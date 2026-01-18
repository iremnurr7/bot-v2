import smtplib
import time
import imaplib
import email
import gspread  # Google Sheets kütüphanesi
from oauth2client.service_account import ServiceAccountCredentials
from email.header import decode_header
import google.generativeai as genai

# --- AYARLAR ---
EMAIL_USER = "ikutuk2007@gmail.com"  # Senin bot mailin
EMAIL_PASS = "ttiz unxi hceq yxum"    # O 16 haneli şifren (Aynı kalsın)
GOOGLE_API_KEY = "AIzaSyB1C5JDPFbolsCZC4-UBzr0wTgSOc0ykS8" # Gemini şifren (Aynı kalsın)

# --- GOOGLE SHEETS BAĞLANTISI ---
# Robotun pasaportunu tanımlıyoruz
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-key.json', scope)
client = gspread.authorize(creds)

# Tabloyu açıyoruz (Adı 'IremStoreVeri' olmalı!)
# Link ile bağlanıyoruz (Daha garantidir)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing").sheet1

print("✅ Google Sheets'e başarıyla bağlandım!")

# Yapay Zeka Ayarı
genai.configure(api_key=GOOGLE_API_KEY)

def get_ai_response(user_message):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Sen bir e-ticaret asistanısın. Müşteri şöyle dedi: "{user_message}"
        Buna kibar, kısa ve çözüm odaklı bir cevap ver.
        Cevabın sadece mail içeriği olsun.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "Şu an sistemde bakım var, talebinizi aldık."

def send_mail(to_email, subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        msg = f"Subject: {subject}\n\n{body}".encode('utf-8')
        server.sendmail(EMAIL_USER, to_email, msg)
        server.quit()
        print(f"📨 Cevap gönderildi: {to_email}")
    except Exception as e:
        print(f"Hata: {e}")

def check_mails():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    # Sadece okunmamış mailleri al
    status, messages = mail.search(None, 'UNSEEN')
    mail_ids = messages[0].split()

    for mail_id in mail_ids:
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Gönderen ve Konu'yu çöz
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                from_ = msg.get("From")

                # 🛑 KENDİ KENDİNE KONUŞMA ENGELİ 🛑
                if EMAIL_USER in from_:
                    print("🛑 Kendi mailimi okudum, cevap vermiyorum.")
                    continue  # Bu maili atla, sıradakine geç

                # İçeriği al
                
                # İçeriği al
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                print(f"📩 Yeni Mail: {subject} - {from_}")

                # --- FİLTRE KALDIRILDI (Her şeye cevap verecek) ---
                # Yapay Zeka Cevabı Al
                ai_reply = get_ai_response(body)
                
                # Kategoriyi Basitçe Belirle (Örnek)
                kategori = "Genel"
                if "kargo" in body.lower(): kategori = "Kargo"
                elif "iade" in body.lower(): kategori = "İade"

                # 🚀 GOOGLE SHEETS'E KAYDET 🚀
                # Tarih, Kimden, Konu, Mesaj, Kategori, Cevap
                # Mail çok uzunsa keselim (Maksimum 2000 karakter)
                ozet_govde = body[:2000] 
                yeni_satir = [time.strftime("%Y-%m-%d %H:%M"), from_, subject, ozet_govde, kategori, ai_reply]
                sheet.append_row(yeni_satir)
                print(f"💾 Buluta Kaydedildi!")

                # Cevap Gönder
                send_mail(from_, f"YNT: {subject}", ai_reply)

# Sonsuz Döngü
print("🤖 Bot çalışıyor... (Kapatmak için Ctrl+C)")
while True:
    try:
        check_mails()
        time.sleep(5)
    except Exception as e:
        print(f"Bir hata oldu: {e}")
        time.sleep(5)