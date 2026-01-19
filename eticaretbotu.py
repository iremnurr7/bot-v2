import streamlit as st
import pandas as pd
import gspread
import smtplib
import imaplib
import email
import datetime
import time
from email.header import decode_header
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Nexus Admin", layout="wide", page_icon="🌐")

# --- 1. AYARLARI AL (SECRETS KULLANARAK) ---
try:
    # API ve Mail Şifreleri
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    EMAIL_USER = st.secrets["email_user"]
    EMAIL_PASS = st.secrets["email_pass"]
    
    # Google Sheets Bağlantısı
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    SHEET_URL = st.secrets["sheet_url"]
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
except Exception as e:
    st.error(f"⚠️ Ayar Hatası: Secrets dosyanızı kontrol edin. Hata: {e}")
    st.stop()

# --- 2. SENİN ZEKİ AI FONKSİYONUN (AYNEN KORUNDU) ---
def get_ai_response(user_message):
    isletme_kurallari = f"""
    Bugünün Tarihi: {datetime.datetime.now().strftime("%Y-%m-%d")}
    KURAL 1: İade süresi satın alımdan itibaren 14 GÜNDÜR. 
    KURAL 2: Eğer müşteri 14 günü aşan bir süre belirtiyorsa, iadeyi KESİNLİKLE REDDET.
    KURAL 3: Ambalajı açılmış ürünler iade alınmaz.
    KURAL 4: 500 TL altı kargo 50 TL'dir.
    """
    
    try:
        # Senin kullandığın ve çalışan model
        model = genai.GenerativeModel('models/gemini-1.5-flash') 
        
        prompt = f"""
        Sen İremStore profesyonel asistanısın. Kurallarımız:
        {isletme_kurallari}

        Müşteri Mesajı: "{user_message}"
        
        GÖREV:
        1. Kurallara göre profesyonel cevap yaz.
        2. Kategoriyi seç: IADE, KARGO, SORU, SIKAYET.
        
        Format (Sadece bu formatta cevap ver):
        KATEGORI: [Kategori]
        CEVAP: [Cevabın]
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"KATEGORI: GENEL\nCEVAP: Sistemsel hata oluştu: {e}"

# --- 3. MAİL GÖNDERME FONKSİYONU ---
def send_mail_reply(to_email, subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail Gönderme Hatası: {e}")
        return False

# --- 4. ANA İŞLEM FONKSİYONU (DÖNGÜSÜZ) ---
def process_emails():
    status_box = st.status("Mail Botu Çalışıyor...", expanded=True)
    
    try:
        # Gmail'e Bağlan
        status_box.write("🔌 Gmail'e bağlanılıyor...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        # 'is' Etiketini Seç
        try:
            mail.select("is")
            status_box.write("✅ 'is' klasörü bulundu.")
        except:
            status_box.error("❌ 'is' etiketi bulunamadı!")
            return

        # Okunmamışları Bul
        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            status_box.warning("📭 Yeni (okunmamış) mail yok.")
            status_box.update(label="İşlem Bitti", state="complete")
            return

        status_box.write(f"📢 {len(mail_ids)} adet yeni mail işleniyor...")
        
        # Google Sheets'i Aç
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet = client.open_by_url(SHEET_URL).sheet1

        count = 0
        for i in mail_ids:
            # Maili Oku
            res, msg_data = mail.fetch(i, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Konu ve Gönderen
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    sender = msg.get("From")
                    sender_email = email.utils.parseaddr(sender)[1]
                    
                    # İçerik
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    status_box.write(f"📩 İşleniyor: {subject}")

                    # --- AI ZEKASI BURADA ÇALIŞIYOR ---
                    ai_full_response = get_ai_response(body)
                    
                    # Cevabı Parçala (Kategori ve Cevap ayır)
                    kategori = "GENEL"
                    cevap = ai_full_response
                    
                    if "KATEGORI:" in ai_full_response and "CEVAP:" in ai_full_response:
                        parts = ai_full_response.split("CEVAP:")
                        kategori_part = parts[0].split("KATEGORI:")[1].strip()
                        cevap_part = parts[1].strip()
                        kategori = kategori_part
                        cevap = cevap_part

                    # 1. Sheets'e Kaydet
                    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet.append_row([date_now, sender, subject, body, kategori, cevap])
                    
                    # 2. Mail Gönder
                    if send_mail_reply(sender_email, f"Re: {subject}", cevap):
                        status_box.write(f"✅ Yanıtlandı: {kategori}")
                        count += 1

        mail.close()
        mail.logout()
        
        if count > 0:
            status_box.update(label=f"🚀 {count} mail başarıyla yanıtlandı!", state="complete")
            st.success(f"{count} adet mail işlendi ve veritabanına kaydedildi.")
            st.cache_data.clear() # Tabloyu yenilemek için
            time.sleep(2)
            st.rerun()

    except Exception as e:
        status_box.error(f"Hata oluştu: {e}")

# --- ARAYÜZ (GÖRÜNÜM) ---
st.title("🌐 NEXUS Admin Paneli")
st.markdown("---")

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("🤖 Bot Kontrol")
    st.info("Bot, 'is' etiketli okunmamış mailleri kontrol eder, kurallara göre cevaplar ve veritabanına işler.")
    
    # İŞTE O BUTON! (While True yerine buna basacaksın)
    if st.button("📥 Mailleri Kontrol Et ve Yanıtla", type="primary"):
        process_emails()

with col2:
    st.subheader("📊 Mesaj Geçmişi")
    # Verileri Göster
    try:
        try:
            sheet_read = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet_read = client.open_by_url(SHEET_URL).sheet1
            
        data = sheet_read.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=["Tarih", "Kimden", "Konu", "Mesaj", "Kategori", "AI Cevabı"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Henüz hiç mesaj yok.")
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")