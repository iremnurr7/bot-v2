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

# --- 1. AYARLARI AL ---
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    EMAIL_USER = st.secrets["email_user"]
    EMAIL_PASS = st.secrets["email_pass"]
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    SHEET_URL = st.secrets["sheet_url"]
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
except Exception as e:
    st.error(f"⚠️ Ayar Hatası: Secrets dosyanızı kontrol edin. Hata: {e}")
    st.stop()

# --- 2. HATA AYIKLAYICI AI FONKSİYONU ---
def get_ai_response(user_message):
    isletme_kurallari = f"""
    Bugünün Tarihi: {datetime.datetime.now().strftime("%Y-%m-%d")}
    KURAL 1: İade süresi satın alımdan itibaren 14 GÜNDÜR. 
    KURAL 2: Eğer müşteri 14 günü aşan bir süre belirtiyorsa, iadeyi KESİNLİKLE REDDET.
    KURAL 3: Ambalajı açılmış ürünler iade alınmaz.
    KURAL 4: 500 TL altı kargo 50 TL'dir.
    """
    
    # Mevcut Modelleri Kontrol Et (Diagnostic)
    try:
        # En garanti model ismi budur
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        prompt = f"""
        Sen İremStore profesyonel asistanısın. Kurallarımız:
        {isletme_kurallari}
        Müşteri Mesajı: "{user_message}"
        GÖREV: Kurallara göre cevap yaz. KATEGORI (IADE, KARGO, SORU, SIKAYET) ve CEVAP formatında dön.
        Format:
        KATEGORI: [Kategori]
        CEVAP: [Cevabın]
        """
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        # Hata Detayı Yazdır
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return "KATEGORI: SISTEM_HATASI\nCEVAP: Model Bulunamadı. Lütfen 'requirements.txt' dosyasında 'google-generativeai>=0.5.0' yazdığından emin olun."
        else:
            return f"KATEGORI: SISTEM_HATASI\nCEVAP: Beklenmedik Hata: {error_msg}"

# --- 3. MAİL GÖNDERME ---
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

# --- 4. ANA İŞLEM ---
def process_emails():
    status_box = st.status("Mail Botu Çalışıyor...", expanded=True)
    
    try:
        status_box.write("🔌 Gmail'e bağlanılıyor...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        try:
            mail.select("is")
            status_box.write("✅ 'is' klasörü bulundu.")
        except:
            status_box.error("❌ 'is' etiketi bulunamadı!")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            status_box.warning("📭 Yeni (okunmamış) mail yok.")
            status_box.update(label="İşlem Bitti", state="complete")
            return

        status_box.write(f"📢 {len(mail_ids)} adet yeni mail işleniyor...")
        
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet = client.open_by_url(SHEET_URL).sheet1

        count = 0
        for i in mail_ids:
            res, msg_data = mail.fetch(i, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    sender = msg.get("From")
                    sender_email = email.utils.parseaddr(sender)[1]
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    status_box.write(f"📩 İşleniyor: {subject}")

                    # AI ZEKASI
                    ai_full_response = get_ai_response(body)
                    
                    # HATA KONTROLÜ
                    if "SISTEM_HATASI" in ai_full_response:
                        status_box.error(ai_full_response)
                        # Hata varsa işlemi durdurma, kaydet ama mail atma
                        kategori = "HATA"
                        cevap = ai_full_response
                    else:
                        kategori = "GENEL"
                        cevap = ai_full_response
                        if "KATEGORI:" in ai_full_response and "CEVAP:" in ai_full_response:
                            try:
                                parts = ai_full_response.split("CEVAP:")
                                kategori = parts[0].split("KATEGORI:")[1].strip()
                                cevap = parts[1].strip()
                            except: pass
                        
                        # Mail Gönder (Sadece hata yoksa)
                        if send_mail_reply(sender_email, f"Re: {subject}", cevap):
                            status_box.write(f"✅ Yanıtlandı: {kategori}")
                    
                    # Kaydet
                    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet.append_row([date_now, sender, subject, body, kategori, cevap])
                    count += 1

        mail.close()
        mail.logout()
        
        if count > 0:
            status_box.update(label=f"🚀 {count} işlem tamamlandı!", state="complete")
            st.success(f"{count} adet mail işlendi.")
            st.cache_data.clear()
            time.sleep(2)
            st.rerun()

    except Exception as e:
        status_box.error(f"Genel Hata: {e}")

# --- ARAYÜZ ---
st.title("🌐 NEXUS Admin Paneli")
st.caption("AI Email Bot v2.1 (Diagnostic Mode)")
st.markdown("---")

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("🤖 Bot Kontrol")
    if st.button("📥 Mailleri Kontrol Et ve Yanıtla", type="primary"):
        process_emails()
    
    # MODEL KONTROL BUTONU (YENİ)
    st.markdown("---")
    if st.button("🛠️ Sistem Modellerini Kontrol Et"):
        st.write("Sunucuda yüklü modeller aranıyor...")
        try:
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            if available_models:
                st.success("✅ Yüklü Modeller:")
                st.write(available_models)
                if "models/gemini-1.5-flash" in available_models or "models/gemini-pro" in available_models:
                    st.success("Sistem UYUMLU! Kod çalışmalı.")
                else:
                    st.error("❌ Hiçbir Gemini modeli bulunamadı. 'requirements.txt' dosyasını kontrol et!")
            else:
                st.error("❌ Hiç model bulunamadı. Kütüphane çok eski.")
        except Exception as e:
            st.error(f"Kontrol Hatası: {e}. Muhtemelen API Anahtarı hatalı veya Kütüphane çok eski.")

with col2:
    st.subheader("📊 Mesaj Geçmişi")
    try:
        try:
            sheet_read = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet_read = client.open_by_url(SHEET_URL).sheet1   
        data = sheet_read.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=["Tarih", "Kimden", "Konu", "Mesaj", "Kategori", "AI Cevabı"])
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")