import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime
import imaplib
import smtplib 
import email
from email.header import decode_header
from email.mime.text import MIMEText

# --- AYARLAR ---
try:
    # 1. GEMINI AI
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 2. GOOGLE SHEETS
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    SHEET_URL = st.secrets["sheet_url"] 
    
    # 3. GMAIL
    EMAIL_USER = st.secrets["email_user"]
    EMAIL_PASS = st.secrets["email_pass"]
    
except Exception as e:
    st.error(f"Sistem Hatası: Ayarlar eksik. Secrets kısmını kontrol et. Hata: {e}")
    st.stop()

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Nexus Admin", layout="wide", page_icon="🌐")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0F172A; color: #F8FAFC; }
    section[data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; padding: 20px; border-radius: 15px; text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; color: #3B82F6; }
    </style>
    """, unsafe_allow_html=True)

# --- YARDIMCI FONKSİYON: GÜVENLİ AI CEVABI ALMA ---
def get_safe_ai_response(prompt_text):
    """
    Bu fonksiyon sırayla tüm modelleri dener. Biri çalışmazsa diğerine geçer.
    """
    models_to_try = ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.0-pro']
    
    # Güvenlik filtrelerini kapat (Hata almamak için)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt_text, safety_settings=safety_settings)
            return response.text
        except Exception:
            continue # Bu model çalışmadıysa sıradakine geç
            
    return "HATA: Hiçbir AI modeli cevap veremedi. API Anahtarınızı veya Kota durumunu kontrol edin."

# --- FONKSİYON 1: VERİLERİ GETİR ---
@st.cache_data(ttl=60)
def get_data():
    try:
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet = client.open_by_url(SHEET_URL).sheet1
            
        data = sheet.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:]) 
            expected_headers = ["Date", "Sender", "Subject", "Message", "Category", "AI_Reply"]
            current_cols = len(df.columns)
            if current_cols >= 6:
                df.columns = expected_headers + list(df.columns[6:])
            else:
                df.columns = expected_headers[:current_cols]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- FONKSİYON 2: MAIL BOTU (AKILLI MODEL SEÇİMLİ) ---
def fetch_and_reply_emails():
    status_box = st.status("Mail Botu Başlatılıyor...", expanded=True) 
    
    try:
        status_box.write("1. Gmail'e bağlanılıyor...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        try:
            mail.select("is") 
            status_box.write("✅ 'is' klasörüne girildi.")
        except:
            status_box.error("❌ HATA: 'is' etiketi bulunamadı.")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            status_box.warning("📭 Yeni (okunmamış) mail yok.")
            status_box.update(label="İşlem Tamamlandı", state="complete")
            return

        status_box.write(f"📢 {len(mail_ids)} yeni mail bulundu.")
        sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        count = 0

        for i in mail_ids: 
            res, msg = mail.fetch(i, "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    msg_content = email.message_from_bytes(response[1])
                    subject, encoding = decode_header(msg_content["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    sender = msg_content.get("From")
                    sender_email = email.utils.parseaddr(sender)[1] 
                    
                    body = ""
                    if msg_content.is_multipart():
                        for part in msg_content.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg_content.get_payload(decode=True).decode()

                    # --- YENİ AI SİSTEMİ ---
                    status_box.write(f"🤖 AI Cevaplıyor: {subject}")
                    bugun = datetime.datetime.now().strftime("%Y-%m-%d")
                    prompt = f"""
                    Sen İremStore asistanısın. Müşteri mesajı: "{body}"
                    KURALLAR: Tarih {bugun}. İade süresi 14 gün. Açılmış paket iade alınmaz. 500TL altı kargo 50TL.
                    GÖREV: Kurallara göre kısa, nazik bir cevap yaz.
                    """
                    
                    # Burada hata vermeyen özel fonksiyonumuzu kullanıyoruz
                    ai_reply = get_safe_ai_response(prompt)

                    # Mail Gönder
                    try:
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(EMAIL_USER, EMAIL_PASS)
                        msg = MIMEText(ai_reply, 'plain', 'utf-8')
                        msg['Subject'] = f"Re: {subject}"
                        msg['From'] = EMAIL_USER
                        msg['To'] = sender_email
                        server.sendmail(EMAIL_USER, sender_email, msg.as_string())
                        server.quit()
                    except Exception as e:
                        status_box.error(f"Mail hatası: {e}")

                    # Kaydet
                    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    kategori = "IADE" if "İADE" in ai_reply.upper() or "IADE" in ai_reply.upper() else "GENEL"
                    sheet.append_row([date_now, sender, subject, body, kategori, ai_reply])
                    count += 1
        
        mail.close()
        mail.logout()
        
        if count > 0:
            status_box.update(label=f"🚀 {count} işlem tamamlandı!", state="complete")
            st.success(f"🚀 {count} mail yanıtlandı!")
            st.cache_data.clear()
            st.rerun()
            
    except Exception as e:
        status_box.error(f"GENEL HATA: {e}")

# --- FONKSİYON 3: AI ANALİZ (DÜZELTİLDİ) ---
def ai_analyze(df):
    if "Message" not in df.columns or df.empty:
        st.error("Analiz edilecek mesaj bulunamadı.")
        return

    # Boş mesajları temizle
    text_data = " ".join(df["Message"].astype(str).tail(15))
    
    if len(text_data) < 5:
        st.warning("Yeterli veri yok.")
        return

    prompt = f"Sen iş analistisin. Mesajlar: '{text_data}'. 3 kısa stratejik öneri yaz."
    
    # Burada da güvenli fonksiyonu kullanıyoruz
    try:
        res_text = get_safe_ai_response(prompt)
        st.session_state.analysis_result = res_text
    except Exception as e: 
        st.error(f"AI Hatası: {e}")

# --- MENÜ ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.caption("Auto-Reply System v2")
    st.markdown("---")
    
    if st.button("📥 Mailleri Çek & Yanıtla", type="primary"):
        fetch_and_reply_emails()
    
    st.markdown("---")
    menu_selection = st.radio("MENU", ["🏠 Dashboard", "💰 Sales Analytics", "📦 Inventory Manager", "📊 Customer Insights", "⚙️ Settings"])
    if st.button("🔄 Yenile"): st.cache_data.clear(); st.rerun()

# --- EKRANLAR ---
df = get_data()

if menu_selection == "🏠 Dashboard":
    st.title("Executive Dashboard")
    st.markdown(f"*{datetime.date.today().strftime('%B %d, %Y')}*")
    if df is not None and not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Mesaj", len(df))
        c2.metric("İadeler", len(df[df["Category"] == "IADE"]) if "Category" in df.columns else 0)
        c3.metric("Ciro", "$1,250", "+12%")
        c4.metric("Aktif Üye", "842")
        
elif menu_selection == "💰 Sales Analytics":
    st.title("💸 Sales Performance")
    st.line_chart(pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=30), "Rev": np.random.randint(200,1000,30)}).set_index("Date"))

elif menu_selection == "📦 Inventory Manager":
    st.title("📦 Inventory")
    try:
        product_sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        st.dataframe(pd.DataFrame(product_sheet.get_all_records()), use_container_width=True)
        with st.form("new"):
            c1, c2 = st.columns(2)
            isim = c1.text_input("Ürün"); fiyat = c1.number_input("Fiyat")
            stok = c2.number_input("Stok"); aciklama = c2.text_input("Açıklama")
            if st.form_submit_button("Kaydet"):
                product_sheet.append_row([isim, stok, fiyat, aciklama])
                st.success("Kaydedildi"); st.rerun()
    except: st.error("'Urunler' sayfası bulunamadı.")

elif menu_selection == "📊 Customer Insights":
    st.title("Customer Intelligence")
    if df is not None:
        st.dataframe(df, use_container_width=True)
        st.markdown("### AI Report")
        if st.button("✨ Rapor Oluştur"): 
            with st.spinner("AI Düşünüyor..."):
                ai_analyze(df)
        if "analysis_result" in st.session_state: 
            st.info(st.session_state.analysis_result)

elif menu_selection == "⚙️ Settings":
    st.title("Ayarlar"); st.warning("Admin Only")