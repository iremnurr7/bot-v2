import streamlit as st
import subprocess
import sys
import time
import json
import pandas as pd
import gspread
import smtplib
import imaplib
import email
import datetime
from email.header import decode_header
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# --- 1. FORCE UPDATE (Kütüphaneleri Güncelle) ---
try:
    import google.generativeai as genai
    import importlib.metadata
    version = importlib.metadata.version("google-generativeai")
    if version < "0.5.0":
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai"])
        st.rerun()
except:
    pass

# --- PAGE CONFIG ---
st.set_page_config(page_title="Solace Admin", layout="wide", page_icon="🌑")

# --- CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0F172A; color: #F8FAFC; }
    section[data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; padding: 20px; border-radius: 15px; text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; color: #3B82F6; }
    div[data-baseweb="textarea"] { background-color: #334155 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOAD SECRETS ---
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
    st.error(f"⚠️ Configuration Error: Check your secrets. Error: {e}")
    st.stop()

# --- 3. GARANTİ MODEL BULUCU (Dynamic Discovery) ---
def get_working_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return m.name
        return "models/gemini-pro"
    except:
        return "models/gemini-pro"

# --- 4. DYNAMIC RULES ---
if "bot_rules" not in st.session_state:
    st.session_state.bot_rules = """1. Return period is 14 days.
2. Opened products cannot be returned.
3. Shipping is 50 TL for orders under 500 TL.
4. If the product is not in the Product List, say you don't have stock info."""

# --- 5. DATA FETCHING ---
@st.cache_data(ttl=60)
def get_data():
    try:
        try: sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except: sheet = client.open_by_url(SHEET_URL).sheet1
        data = sheet.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:])
            expected_headers = ["Date", "Sender", "Subject", "Message", "Category", "AI_Reply"]
            if len(df.columns) >= 6:
                df.columns = expected_headers + list(df.columns[6:])
            else:
                df.columns = expected_headers[:len(df.columns)]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_products():
    try:
        # Hata önleyici: Müşteri sayfa adını yanlış yazarsa veya Urunler sayfası yoksa patlamasın
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        except:
            # Eğer Urunler sayfası yoksa boş dataframe dön
            return pd.DataFrame(), 0, ""

        data = sheet.get_all_values()
        if len(data) > 1:
            # Sütun isimlerini standartlaştırıyoruz (ilk satır başlık kabul edilir)
            headers = data[0]
            df = pd.DataFrame(data[1:], columns=headers)
            
            # AI için metin formatına çevir (Ürün bilgisi: Adı X, Fiyatı Y...)
            product_text_list = []
            for index, row in df.iterrows():
                row_str = ", ".join([f"{col}: {val}" for col, val in row.items() if val])
                product_text_list.append(f"- {row_str}")
            product_context = "\n".join(product_text_list)

            # Dashboard hesaplamaları için basit temizlik (Hata verirse 0 kabul et)
            total_value = 0
            if "Price" in df.columns and "Stock" in df.columns:
                try:
                    price_clean = pd.to_numeric(df["Price"].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                    stock_clean = pd.to_numeric(df["Stock"], errors='coerce').fillna(0)
                    total_value = (price_clean * stock_clean).sum()
                except: pass
            
            return df, total_value, product_context
        return pd.DataFrame(), 0, ""
    except: return pd.DataFrame(), 0, ""

# --- 6. STRATEGIC REPORT ---
def generate_strategic_report(df):
    if df.empty: return "No data available."
    messages_text = "\n".join(df["Message"].tail(30).astype(str).tolist())
    
    prompt = f"""
    You are an expert E-Commerce Consultant. Data: {messages_text}
    Analyze this data and write a strategic report.
    OUTPUT FORMAT:
    📊 **Trend Analysis:** [Insights]
    🚨 **Critical Issue:** [Main problem]
    💡 **Action Plan:** [Recommendations]
    """
    try:
        model_name = get_working_model()
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Report Error using {model_name}: {str(e)}"

# --- 7. AI RESPONSE (GELİŞMİŞ) ---
def get_ai_response(user_message, custom_rules, product_info):
    prompt = f"""
    You are 'Solace', a professional e-commerce assistant.
    
    --- CONTEXT ---
    DATE: {datetime.date.today().strftime("%Y-%m-%d")}
    
    --- BUSINESS RULES ---
    {custom_rules}
    
    --- PRODUCT LIST / INVENTORY ---
    {product_info}
    (If the customer asks about a product NOT in this list, state that you cannot find information about it.)
    
    --- CUSTOMER MESSAGE ---
    "{user_message}"
    
    --- INSTRUCTIONS ---
    1. LANGUAGE: You MUST reply in ENGLISH only. Even if the input is Turkish, reply in English.
    2. ACCURACY: Use the Product List above to answer price/stock questions. Do not invent prices.
    3. SAFETY: If the answer is not in the Rules or Product List, reply: "I don't have the details for this specific query right now. Our support team has been notified and will contact you shortly." and mark category as OTHER.
    4. CATEGORY: Use exactly: RETURN, SHIPPING, QUESTION, or OTHER.
    
    FORMAT: 
    CATEGORY: [RETURN/SHIPPING/QUESTION/OTHER] 
    ANSWER: [Your polite reply text in English]
    """
    try:
        model_name = get_working_model()
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: 
        return f"CATEGORY: ERROR\nANSWER: AI Error: {str(e)}"

# --- 8. SEND EMAIL ---
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

# --- 9. PROCESS EMAILS (ESNEK KLASÖR SEÇİMİ) ---
def process_emails():
    # Ürün bilgisini çekiyoruz ki cevaba ekleyelim
    _, _, product_context = get_products()
    
    with st.spinner("Solace is checking emails..."):
        st.write("🔌 Connecting to Gmail...")
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_USER, EMAIL_PASS)
            
            # --- DİNAMİK KLASÖR SEÇİMİ ---
            # Secrets'tan 'mail_klasoru' bilgisini al. Yoksa varsayılan 'INBOX' olsun.
            # Müşteri secrets'a mail_klasoru = "is" yazarsa "is" klasörüne bakar.
            # Hiçbir şey yazmazsa INBOX'a bakar.
            target_folder = st.secrets.get("mail_klasoru", "INBOX")
            
            # Klasörü seçmeyi dene
            status, messages = mail.select(target_folder)
            
            if status != 'OK':
                st.error(f"❌ Error: The folder '{target_folder}' was not found in this Gmail account. Please check 'secrets' configuration.")
                return
            else:
                st.info(f"📂 Scanning folder: {target_folder}")

        except Exception as e:
            st.error(f"Gmail Connection Error: {e}")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            st.toast(f"📭 No new emails found in {target_folder}.")
            return

        st.info(f"📢 {len(mail_ids)} new emails found.")
        try: sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except: sheet = client.open_by_url(SHEET_URL).sheet1
        
        count = 0
        current_rules = st.session_state.bot_rules 

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

                        st.write(f"📩 Processing: {subject}")
                        
                        # AI Fonksiyonuna ürün bilgisini de gönderiyoruz
                        ai_full_response = get_ai_response(body, current_rules, product_context)

                        kategori = "GENERAL"
                        cevap = ai_full_response
                        if "CATEGORY:" in ai_full_response:
                            parts = ai_full_response.split("ANSWER:")
                            if len(parts) > 1:
                                kategori = parts[0].split("CATEGORY:")[1].strip()
                                cevap = parts[1].strip()

                        sheet.append_row([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), sender, subject, body, kategori, cevap])
                        if send_mail_reply(sender, f"Re: {subject}", cevap):
                            st.write(f"✅ Replied: {kategori}")
                            count += 1
            except Exception as loop_e:
                st.error(f"Error: {loop_e}")

        mail.close()
        mail.logout()
        
        if count > 0:
            st.success(f"🚀 {count} emails replied successfully!")
            time.sleep(2)
            st.rerun()

# --- SIDEBAR MENU ---
with st.sidebar:
    st.title("🌑 SOLACE") 
    st.caption("AI-Powered Commerce")
    
    if st.button("📥 Fetch & Reply Emails", type="primary"):
        process_emails()
    st.markdown("---")
    menu_selection = st.radio("MENU", ["🏠 Dashboard", "📦 Inventory", "📊 Analysis", "⚙️ Settings"])
    st.markdown("---")
    if st.button("🔄 Refresh"): 
        st.cache_data.clear()
        st.rerun()

# --- DATA PREP ---
df_msgs = get_data()
df_prods, total_stock_value, _ = get_products()

# --- PAGES ---

if menu_selection == "🏠 Dashboard":
    st.title("Solace Management Panel")
    st.markdown(f"*{datetime.date.today().strftime('%d %B %Y')}*")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Messages", len(df_msgs))
    
    if not df_msgs.empty and "Category" in df_msgs.columns:
        iade_sayisi = len(df_msgs[df_msgs["Category"].astype(str).str.contains("RETURN|IADE", case=False, na=False)])
    else:
        iade_sayisi = 0
        
    c2.metric("Return Requests", iade_sayisi)
    c3.metric("Inventory Value", f"{total_stock_value:,.0f} TL")
    c4.metric("Product Variety", len(df_prods))
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Request Distribution")
        if not df_msgs.empty and "Category" in df_msgs.columns:
            fig = px.pie(df_msgs, names='Category', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.info("💡 **Solace** is active.")

elif menu_selection == "📦 Inventory":
    st.title("📦 Inventory Management")
    if not df_prods.empty:
        st.dataframe(df_prods, use_container_width=True)
    else:
        st.info("No product data found. Please add products to the 'Urunler' sheet.")
        
    with st.expander("➕ Add New Product"):
        with st.form("add_prod"):
            c1, c2 = st.columns(2)
            isim = c1.text_input("Product Name")
            fiyat = c1.number_input("Price (TL)", min_value=0.0)
            stok = c2.number_input("Stock Qty", min_value=0)
            aciklama = c2.text_input("Description")
            if st.form_submit_button("Save to Database"):
                try:
                    sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
                    sheet.append_row([isim, stok, fiyat, aciklama])
                    st.success("Product Added!"); st.rerun()
                except: st.error("Error saving data. Make sure 'Urunler' sheet exists.")

elif menu_selection == "📊 Analysis":
    st.title("Strategic Message Analysis")
    with st.container():
        st.markdown("### 🧠 Solace AI Report")
        st.caption("AI analyzes incoming messages and provides critical alerts.")
        
        try:
             active_model = get_working_model()
             st.caption(f"Active Engine: `{active_model}`")
        except: pass

        if st.button("✨ Generate Strategic Report", type="primary"):
            if not df_msgs.empty:
                with st.spinner("Solace is analyzing data..."):
                    report = generate_strategic_report(df_msgs)
                    st.markdown("---")
                    st.markdown(report)
            else:
                st.warning("Not enough data for analysis.")
    st.markdown("---")
    st.subheader("📨 Message History")
    if not df_msgs.empty:
        st.dataframe(df_msgs, use_container_width=True)
    else:
        st.info("No messages found.")

elif menu_selection == "⚙️ Settings":
    st.title("Solace Settings")
    st.subheader("📜 Business Rules (Prompt)")
    st.caption("Define how the bot should reply.")
    new_rules = st.text_area("Edit Rules:", value=st.session_state.bot_rules, height=200)
    if st.button("Save Rules"):
        st.session_state.bot_rules = new_rules
        st.success("Rules updated successfully!")