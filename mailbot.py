import smtplib
import time
import imaplib
import email
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.header import decode_header
import google.generativeai as genai

# --- AYARLAR ---
EMAIL_USER = "ikutuk2007@gmail.com"
EMAIL_PASS = "ttiz unxi hceq yxum"
# Senin API Key'in
GOOGLE_API_KEY = "AIzaSyCyWw6oiidpu46-Mf7GsTH6W4MZCOw3jEk"

# --- GOOGLE SHEETS BAĞLANTISI ---
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google-key.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing").sheet1
    print("✅ Google Sheets'e başarıyla bağlandım!")
except Exception as e:
    print(f"❌ Sheets Bağlantı Hatası: {e}")

genai.configure(api_key=GOOGLE_API_KEY)

def get_ai_response(user_message):
    # İŞLETME KURALLARI (14 Gün Kuralı)
    isletme_kurallari = f"""
    Bugünün Tarihi: {time.strftime("%Y-%m-%d")}
    KURAL 1: İade süresi satın alımdan itibaren 14 GÜNDÜR. 
    KURAL 2: Eğer müşteri '20 gün oldu' gibi 14 günü aşan bir süre belirtiyorsa, iadeyi KESİNLİKLE REDDET ve sürenin dolduğunu nazikçe açıkla.
    KURAL 3: Ambalajı açılmış ürünler iade alınmaz.
    KURAL 4: 500 TL altı kargo 50 TL'dir.
    """
    
    try:
        # 🚀 HEDEFİ 12'DEN VURAN SATIR:
        # Senin listende 'gemini-flash-latest' var, onu kullanıyoruz.
        model = genai.GenerativeModel('models/gemini-flash-latest')
        
        prompt = f"""
        Sen İremStore profesyonel asistanısın. Kurallarımız:
        {isletme_kurallari}

        Müşteri Mesajı: "{user_message}"
        
        GÖREV:
        1. Kurallara göre (özellikle 14 gün sınırı) profesyonel bir cevap yaz.
        2. Kategoriyi seç: IADE, KARGO, SORU, SIKAYET.
        
        Format (Sadece bu formatta cevap ver):
        KATEGORI: [Kategori]
        CEVAP: [Cevabın]
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ AI Hatası: {e}") 
        return "KATEGORI: GENEL\nCEVAP: Üzgünüz, şu an sistemde teknik bir sorun var."

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
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("is") 

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()
        
        print(f"🔎 {len(mail_ids)} adet işlenecek mail var.")

        for mail_id in mail_ids:
            status, data = mail.fetch(mail_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            from_ = msg.get("From")
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes): subject = subject.decode()

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
            else:
                body = msg.get_payload(decode=True).decode()

            print(f"🚀 İşleniyor: {subject}")
            ai_output = get_ai_response(body)
            
            # Terminalde AI'nın cevabını görelim
            print(f"🤖 AI Ne Dedi:\n{ai_output}") 

            # Parçalama (split) mantığı
            try:
                if "CEVAP:" in ai_output.upper():
                    kategori = ai_output.upper().split("KATEGORI:")[1].split("CEVAP:")[0].strip().replace("*", "")
                    ai_reply = ai_output.split("CEVAP:")[1].strip()
                else:
                    kategori = "GENEL"
                    ai_reply = ai_output
            except:
                kategori = "GENEL"
                ai_reply = ai_output

            # Sheets Kayıt
            sheet.append_row([time.strftime("%Y-%m-%d %H:%M"), str(from_), str(subject), str(body[:1000]), str(kategori), str(ai_reply)])
            print(f"💾 '{kategori}' olarak kaydedildi.")
            
            send_mail(from_, f"YNT: {subject}", ai_reply)

        mail.logout()
    except Exception as e:
        print(f"⚠️ Hata: {e}")

# Sonsuz Döngü
print("\n🤖 Bot AKTİF. 'gemini-flash-latest' modeli devrede...")
while True:
    check_mails()
    time.sleep(10)