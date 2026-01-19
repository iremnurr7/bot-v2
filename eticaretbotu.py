import streamlit as st
import subprocess
import sys
import time

# --- 1. ZORLA GÜNCELLEME MODÜLÜ (EN BAŞTA ÇALIŞIR) ---
# Bu blok, sunucudaki eski kütüphaneyi ezer ve yenisini kurar.
try:
    import google.generativeai as genai
    # Sürüm kontrolü: Eğer sürüm eskiyse güncellemeye zorla
    import importlib.metadata
    version = importlib.metadata.version("google-generativeai")
    if version < "0.5.0":
        raise ImportError # Bilerek hata verdirip güncellemeye zorluyoruz
except:
    print("Kütüphane güncelleniyor... Lütfen bekleyin...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai"])
    # Güncelleme sonrası modülü tekrar yükle
    import google.generativeai as genai

# Diğer kütüphaneler
import pandas as pd
import gspread
import smtplib
import imaplib
import email
import json
from email.header import decode_header
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Nexus Admin", layout="wide", page_icon="🌐")

# --- 2. AYARLARI AL ---
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
    st.error(f"⚠️ Ayar Hatası: Secrets kısmını kontrol et. Hata: {e}")
    st.stop()

# --- 3. AKILLI AI CEVAPLAYICI (MODELİ KENDİ SEÇER) ---
def get_ai_response(user_message):
    isletme_kurallari = f"""
    Bugün: {time.strftime("%Y-%m-%d")}
    KURAL 1: İade süresi 14 GÜNDÜR. (Geçtiyse reddet).
    KURAL 2: Ambalajı açılmış ürün iade alınmaz.
    KURAL 3: 500 TL altı kargo 50 TL'dir.
    """
    
    prompt = f"""
    Sen İremStore asistanısın. Kurallar: {isletme_kurallari}
    Müşteri Mesajı: "{user_message}"
    GÖREV: Kurallara göre cevap yaz.
    FORMAT: 
    KATEGORI: [IADE/KARGO/SORU]
    CEVAP: [Kısa Cevap]
    """
    
    try:
        # BURASI DEĞİŞTİ: Model ismini ezbere yazmıyoruz.
        # Google'a soruyoruz: "Elinizde çalışan hangi model var?"
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Listeden içinde 'gemini' geçen ilk modeli al, yoksa listenin ilkini al
        model_name = next((m for m in available_models if 'gemini' in m), available_models[0])
        
        # Seçilen modeli kullan
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text, model_name # Hangi modeli kullandığını da döndür
        
    except Exception as e:
        return f"KATEGORI: HATA\nCEVAP: Teknik Hata: {str(e)}", "Yok"

# --- 4. MAİL GÖNDERME ---
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
    except: return False

# --- 5. ANA İŞLEM ---
def process_emails():
    # Ekrana genişletilebilir kutu koyuyoruz
    with st.status("Bot Çalışıyor...", expanded=True) as status:
        
        # Kütüphane sürümünü ekrana yazalım ki güncellenmiş mi görelim
        try:
            import importlib.metadata
            ver = importlib.metadata.version("google-generativeai")
            st.write(f"ℹ️ AI Kütüphane Sürümü: {ver} (0.5.0 üstü olmalı)")
        except: st.write("ℹ️ Sürüm okunamadı.")

        st.write("🔌 Gmail'e bağlanılıyor...")
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("is") # 'is' etiketi
        except Exception as e:
            status.update(label="Bağlantı Hatası!", state="error")
            st.error(f"Gmail Bağlantı Hatası: {e}. 'is' klasörü var mı?")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            status.update(label="Yeni mesaj yok", state="complete")
            st.toast("📭 Yeni mail yok.")
            return

        st.write(f"📢 {len(mail_ids)} adet yeni mail bulundu.")
        
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet = client.open_by_url(SHEET_URL).sheet1

        count = 0
        for i in mail_ids:
            try:
                res, msg_data = mail.fetch(i, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes): subject = subject.decode(encoding or "utf-8")
                        sender = email.utils.parseaddr(msg.get("From"))[1]
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else: body = msg.get_payload(decode=True).decode()

                        st.write(f"📩 İşleniyor: {subject}")

                        # AI ZEKASI
                        ai_full_response, used_model = get_ai_response(body)
                        st.caption(f"Kullanılan Model: {used_model}") # Hangi modeli kullandığını yazar

                        kategori = "GENEL"
                        cevap = ai_full_response
                        if "KATEGORI:" in ai_full_response:
                            parts = ai_full_response.split("CEVAP:")
                            if len(parts) > 1:
                                kategori = parts[0].split("KATEGORI:")[1].strip()
                                cevap = parts[1].strip()

                        # Kaydet
                        sheet.append_row([time.strftime("%Y-%m-%d %H:%M"), sender, subject, body, kategori, cevap])
                        
                        # Gönder
                        if send_mail_reply(sender, f"Re: {subject}", cevap):
                            st.write(f"✅ Yanıtlandı: {kategori}")
                            count += 1
            except Exception as loop_e:
                st.error(f"Mail işleme hatası: {loop_e}")

        mail.close()
        mail.logout()
        
        if count > 0:
            status.update(label="İşlem Tamamlandı!", state="complete")
            st.success(f"🚀 {count} mail başarıyla yanıtlandı!")
            time.sleep(2)
            st.rerun()

# --- ARAYÜZ ---
st.title("🌐 NEXUS Admin")

col1, col2 = st.columns([1,3])
with col1:
    st.info("Bot, 'is' klasörünü kontrol eder.")
    if st.button("📥 Mailleri Çek & Yanıtla", type="primary"):
        process_emails()

with col2:
    st.subheader("Mesajlar")
    try:
        try: sheet_read = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except: sheet_read = client.open_by_url(SHEET_URL).sheet1
        data = sheet_read.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=["Tarih","Kimden","Konu","Mesaj","Kategori","AI Cevabı"])
            st.dataframe(df, use_container_width=True)
    except: st.write("Veri yok.")