import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime

# --- SECURE CONFIGURATION ---
try:
    # Gemini Key
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Google Sheets Auth
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    
    # Sheet URL from Secrets
    SHEET_URL = st.secrets["sheet_url"] 
    
except Exception as e:
    st.error(f"System Error: Configuration failed. Please check 'Secrets'. Error: {e}")
    st.stop()

# --- PAGE SETTINGS ---
# 'Nexus Admin' olarak değiştirdik.
st.set_page_config(page_title="Nexus Admin", layout="wide", page_icon="🌐")

# --- CUSTOM CSS DESIGN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0F172A; color: #F8FAFC; }
    section[data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; padding: 20px; border-radius: 15px; text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; color: #3B82F6; }
    
    /* Input Fields Design */
    div[data-baseweb="input"] { background-color: #334155 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTIONS ---
@st.cache_data(ttl=60)
def get_data():
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        # Sütun başlıklarını da İngilizce bekliyoruz ama veri Türkçe gelebilir.
        # Kodun çalışması için dataframe sütunlarını standartlaştırıyoruz.
        if not df.empty and len(df.columns) >= 6:
            df.columns = ["Date", "Sender", "Subject", "Message", "Category", "AI_Reply"]
        return df
    except: return None

def ai_analyze(df):
    text_data = " ".join(df["Message"].astype(str).tail(15))
    prompt = f"You are a senior business analyst. Review these customer messages: '{text_data}'. Write 3 short, strategic recommendations for the business owner."
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.analysis_result = res.text
    except: st.error("AI connection timeout.")

# --- SIDEBAR MENU ---
with st.sidebar:
    # Logo yerine emoji veya ikon kullanabilirsin
    st.title("🌐 NEXUS")
    st.caption("E-Commerce OS v1.0")
    st.markdown("---")
    
    menu_selection = st.radio("MENU", [
        "🏠 Dashboard", 
        "💰 Sales Analytics", 
        "📦 Inventory Manager", 
        "📊 Customer Insights", 
        "⚙️ Settings"
    ])
    
    st.markdown("---")
    if st.button("🔄 Refresh Data"): 
        st.cache_data.clear()
        st.rerun()

# --- PAGES ---
df = get_data()

# 1. DASHBOARD
if menu_selection == "🏠 Dashboard":
    st.title("Executive Dashboard")
    st.markdown(f"*{datetime.date.today().strftime('%B %d, %Y')} - Live Overview*")
    
    if df is not None and not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        total_msg = len(df)
        returns = len(df[df["Category"] == "IADE"]) # Veritabanında "IADE" yazıyorsa değiştirmene gerek yok
        
        c1.metric("Total Messages", total_msg)
        c2.metric("Return Requests", returns)
        c3.metric("Est. Revenue", "$1,250", "+12%")
        c4.metric("Active Users", "842", "+5")
        
        st.markdown("###")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ticket Categories")
            df_pie = df["Category"].value_counts().reset_index()
            df_pie.columns = ["Category", "Count"]
            fig = px.pie(df_pie, values='Count', names='Category', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with col2: 
            st.info("💡 **Insight:** Return requests decreased by 5% this week. Customer satisfaction is trending up.")

# 2. SALES ANALYTICS
elif menu_selection == "💰 Sales Analytics":
    st.title("💸 Sales Performance (Demo)")
    # Simülasyon verisi (Random Data)
    sales = pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=30), 
        "Revenue": np.random.randint(200, 1000, 30) # Dolar bazlı
    })
    st.line_chart(sales.set_index("Date")["Revenue"], color="#34D399")
    st.caption("Data is simulated for demonstration purposes.")

# 3. INVENTORY MANAGER
elif menu_selection == "📦 Inventory Manager":
    st.title("📦 Inventory & Product Management")
    try:
        # Google Sheet'teki sayfa adını 'Urunler' olarak bırakabilirsin, kod oraya bakar.
        product_sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        st.dataframe(pd.DataFrame(product_sheet.get_all_records()), use_container_width=True)
        
        st.markdown("---")
        st.subheader("➕ Add New Product")
        with st.form("new_product_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Product Name (e.g. Nike Air Max)")
            p_price = c1.number_input("Price ($)", min_value=0.0)
            p_stock = c2.number_input("Stock Qty", min_value=0, step=1)
            p_desc = c2.text_input("Short Description")
            
            if st.form_submit_button("Save Product") and p_name:
                # Veritabanına kaydederken sırayı bozmuyoruz
                product_sheet.append_row([p_name, p_stock, p_price, p_desc])
                st.success(f"✅ {p_name} added to inventory!")
                st.rerun()
    except: st.error("Database Error: 'Urunler' worksheet not found.")

# 4. CUSTOMER INSIGHTS
elif menu_selection == "📊 Customer Insights":
    st.title("Customer Intelligence")
    if df is not None:
        st.dataframe(df, use_container_width=True)
        
        st.markdown("### AI Strategic Advisor")
        if st.button("✨ Generate AI Report"): 
            ai_analyze(df)
        
        if "analysis_result" in st.session_state: 
            st.success("Analysis Complete")
            st.info(st.session_state.analysis_result)

# 5. SETTINGS
elif menu_selection == "⚙️ Settings":
    st.title("System Settings")
    st.warning("⚠️ Restricted Access: Only Administrators can modify these settings.")
    st.text_input("API Key Status", "Active (Secure)", disabled=True)
    st.toggle("Maintenance Mode", False)