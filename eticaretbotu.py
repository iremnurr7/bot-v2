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

# --- AYARLAR (SECRETS'TAN ÇEKİLİYOR) ---
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
    div[data-baseweb="input"] { background-color: #334155 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONKSİYON 1: VERİLERİ TABLOYA ÇEK ---
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
            
            # Sütun eşitleme
            current_cols = len(df.columns)
            if current_cols >= 6:
                df.columns = expected_headers + list(df.columns[6:])
            else:
                df.columns = expected_headers[:current_cols]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- FONKSİYON 2: SENİN ÖZEL BOT MOTORUN (MAİL ÇEK & CEVAPLA) ---
def fetch_and_reply_emails():
    # Ekrana işlem kutusu açıyoruz (Print yerine buraya yazacak)
    status_box = st.status("Mail Botu Devrede...", expanded=True) 
    
    try:
        # 1. Gelen Kutusuna Bağlan
        status_box.write("1. Gmail'e bağlanılıyor...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        # --- BURASI SENİN İSTEDİĞİN 'is' ETİKETİ AYARI ---
        try:
            mail.select("is") 
            status_box.write("✅ 'is' etiketli klasöre giriş yapıldı.")
        except:
            status_box.error("❌ HATA: Gmail'de 'is' adında bir etiket bulunamadı! Lütfen etiketi kontrol edin.")
            return
        # ------------------------------------------------

        # Sadece OKUNMAMIŞ (UNSEEN) mailleri ara
        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            status_box.warning("📭 'is' klasöründe okunmamış yeni mail yok.")
            status_box.update(label="İşlem Tamamlandı (Yeni Mail Yok)", state="complete")
            return

        status_box.write(f"📢 {len(mail_ids)} adet yeni iş maili bulundu! Kurallar uygulanıyor...")

        sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        # Model olarak gemini-pro kullanıyoruz (flash bazen hata veriyor diye)
        model = genai.GenerativeModel('gemini-pro')
        count = 0

        # Mailleri İşle
        for i in mail_ids: 
            res, msg = mail.fetch(i, "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    msg_content = email.message_from_bytes(response[1])
                    
                    # Konu ve Gönderen
                    subject, encoding = decode_header(msg_content["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    sender = msg_content.get("From")
                    sender_email = email.utils.parseaddr(sender)[1] 
                    status_box.write(f"📩 İşlenen: {subject} ({sender_email})")
                    
                    # İçerik
                    body = ""
                    if msg_content.is_multipart():
                        for part in msg_content.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg_content.get_payload(decode=True).decode()

                    # --- SENİN BELİRLEDİĞİN İŞLETME KURALLARI ---
                    status_box.write("🤖 AI Kurallara Göre Cevaplıyor...")
                    
                    bugun = datetime.datetime.now().strftime("%Y-%m-%d")
                    prompt = f"""
                    Sen İremStore profesyonel asistanısın. Müşteri mesajı: "{body}"
                    
                    KURALLARIMIZ (Buna kesinlikle uy):
                    - Bugünün Tarihi: {bugun}
                    1. İade süresi satın alımdan itibaren 14 GÜNDÜR. 
                    2. Eğer müşteri 14 günü aşan bir süre belirtiyorsa (örn: 20 gün), iadeyi KESİNLİKLE REDDET ve sürenin dolduğunu nazikçe açıkla.
                    3. Ambalajı açılmış ürünler iade alınmaz.
                    4. 500 TL altı kargo 50 TL'dir.
                    
                    GÖREV:
                    Bu kurallara göre müşteriye çok kısa, profesyonel ve net bir cevap yaz.
                    """
                    
                    try:
                        ai_reply = model.generate_content(prompt).text
                    except Exception as ai_err:
                        status_box.error(f"AI Hatası: {ai_err}")
                        ai_reply = "Sistem yoğunluğu nedeniyle şu an otomatik cevap verilemedi."

                    # --- CEVABI MAİL OLARAK GÖNDER (SMTP) ---
                    status_box.write("📤 Cevap müşteriye gönderiliyor...")
                    try:
                        server = smtplib.SMTP('smtp.gmail.com', 587) # Senin kodundaki port 587
                        server.starttls()
                        server.login(EMAIL_USER, EMAIL_PASS)
                        
                        # Türkçe karakter sorunu olmasın diye utf-8 kodluyoruz
                        msg = MIMEText(ai_reply, 'plain', 'utf-8')
                        msg['Subject'] = f"Re: {subject}"
                        msg['From'] = EMAIL_USER
                        msg['To'] = sender_email
                        
                        server.sendmail(EMAIL_USER, sender_email, msg.as_string())
                        server.quit()
                        status_box.write("✅ Mail başarıyla iletildi!")
                    except Exception as e:
                        status_box.error(f"❌ Mail Gönderme Hatası: {e}")

                    # --- VERİTABANINA KAYDET ---
                    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    # Kategori belirleme basitçe
                    kategori = "GENEL"
                    if "İADE" in ai_reply.upper() or "IADE" in ai_reply.upper(): kategori = "IADE"
                    
                    sheet.append_row([date_now, sender, subject, body, kategori, ai_reply])
                    count += 1
        
        mail.close()
        mail.logout()
        
        if count > 0:
            status_box.update(label=f"🚀 {count} işlem başarıyla tamamlandı!", state="complete")
            st.success(f"🚀 {count} mail kurallara göre yanıtlandı!")
            st.cache_data.clear()
            st.rerun()
            
    except Exception as e:
        status_box.error(f"KRİTİK HATA: {e}")

# --- FONKSİYON 3: RAPORLAMA İÇİN AI ANALİZ ---
def ai_analyze(df):
    if "Message" not in df.columns or df.empty:
        st.error("Analiz edilecek mesaj bulunamadı.")
        return

    text_data = " ".join(df["Message"].astype(str).tail(10))
    prompt = f"Sen uzman bir iş analistisin. Mesajlar: '{text_data}'. 3 kısa stratejik öneri yaz."
    try:
        model = genai.GenerativeModel('gemini-pro')
        res = model.generate_content(prompt)
        st.session_state.analysis_result = res.text
    except Exception as e: 
        st.error(f"AI Hatası: {e}")

# --- SIDEBAR MENÜSÜ ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.caption("AI Auto-Reply System")
    st.markdown("---")
    
    # SENİN İSTEDİĞİN BUTON BURADA
    if st.button("📥 Mailleri Çek & Yanıtla", type="primary"):
        fetch_and_reply_emails()
    
    st.markdown("---")
    
    menu_selection = st.radio("MENU", [
        "🏠 Dashboard", 
        "💰 Sales Analytics", 
        "📦 Inventory Manager", 
        "📊 Customer Insights", 
        "⚙️ Settings"
    ])
    
    if st.button("🔄 Refresh Data"): 
        st.cache_data.clear()
        st.rerun()

# --- SAYFALAR ---
df = get_data()

# 1. DASHBOARD
if menu_selection == "🏠 Dashboard":
    st.title("Executive Dashboard")
    st.markdown(f"*{datetime.date.today().strftime('%B %d, %Y')} - Live Overview*")
    
    if df is not None and not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        total_msg = len(df)
        returns = len(df[df["Category"] == "IADE"]) if "Category" in df.columns else 0
            
        c1.metric("Total Messages", total_msg)
        c2.metric("Return Requests", returns)
        c3.metric("Est. Revenue", "$1,250", "+12%")
        c4.metric("Active Users", "842", "+5")
        
        st.markdown("###")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ticket Categories")
            if "Category" in df.columns:
                df_pie = df["Category"].value_counts().reset_index()
                df_pie.columns = ["Category", "Count"]
                fig = px.pie(df_pie, values='Count', names='Category', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        with col2: 
            st.info("💡 **Insight:** İade talepleri bu hafta düşüşte.")

# 2. SALES ANALYTICS
elif menu_selection == "💰 Sales Analytics":
    st.title("💸 Sales Performance")
    sales = pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=30), 
        "Revenue": np.random.randint(200, 1000, 30) 
    })
    st.line_chart(sales.set_index("Date")["Revenue"], color="#34D399")

# 3. INVENTORY MANAGER
elif menu_selection == "📦 Inventory Manager":
    st.title("📦 Inventory & Product Management")
    try:
        product_sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        st.dataframe(pd.DataFrame(product_sheet.get_all_records()), use_container_width=True)
        
        with st.form("new_product_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Product Name")
            p_price = c1.number_input("Price ($)", min_value=0.0)
            p_stock = c2.number_input("Stock", min_value=0, step=1)
            p_desc = c2.text_input("Desc")
            if st.form_submit_button("Save"):
                product_sheet.append_row([p_name, p_stock, p_price, p_desc])
                st.success("Saved!"); st.rerun()
    except: st.error("Lütfen 'Urunler' sayfasını oluşturun.")

# 4. CUSTOMER INSIGHTS
elif menu_selection == "📊 Customer Insights":
    st.title("Customer Intelligence")
    if df is not None:
        st.dataframe(df, use_container_width=True)
        st.markdown("### AI Strategic Advisor")
        if st.button("✨ Generate AI Report"): 
            with st.spinner("Analyzing..."):
                ai_analyze(df)
        if "analysis_result" in st.session_state: 
            st.success("Analysis Complete")
            st.info(st.session_state.analysis_result)

# 5. SETTINGS
elif menu_selection == "⚙️ Settings":
    st.title("System Settings")
    st.warning("⚠️ Admin Access Only")