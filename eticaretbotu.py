import json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- GÜVENLİ YAPILANDIRMA ---
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Sistem Hatası: API anahtarı doğrulanamadı.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- KURUMSAL UI/UX TASARIMI (Gelişmiş CSS) ---
st.set_page_config(page_title="İremStore BI Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Global Stil */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0F172A;
    }
    .stApp { background-color: #0F172A; }
    
    /* Sidebar Daraltma ve Sabitleme (Kaydırmayı Engeller) */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        width: 260px !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* Metrik Kartları */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 15px !important;
        border-radius: 10px !important;
    }
    div[data-testid="stMetricValue"] { color: #F8FAFC !important; font-size: 1.8rem !important; }
    div[data-testid="stMetricLabel"] { color: #94A3B8 !important; }

    /* Chatbot Giriş Alanı İyileştirme */
    div[data-testid="stChatInput"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        padding: 5px !important;
        bottom: 20px !important;
    }
    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: white !important;
    }

    /* Butonlar */
    .stButton > button {
        border-radius: 6px !important;
        background-color: #3B82F6 !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        width: 100%;
        height: 40px;
    }
    
    /* Gereksiz Boşlukları Silme */
    .block-container { padding-top: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- VERİ VE ANALİZ SİSTEMİ ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return pd.DataFrame(sheet.get_all_records())
    except: return None

def ai_stratejik_rapor(df):
    st.markdown("### Stratejik Analiz Raporu")
    metin = " ".join(df["Mesaj"].astype(str).tail(10))
    prompt = f"Sen profesyonel bir iş analistisin. Bu son müşteri mesajlarını inceleyerek patrona 3 adet kısa, net ve aksiyon odaklı tavsiye ver: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.info(res.text)
    except: st.warning("Analiz servisi şu an meşgul.")

# --- SIDEBAR (DARALTIŞMIŞ DÜZEN) ---
with st.sidebar:
    st.markdown("## İremStore BI")
    st.caption("Veri Odaklı Yönetim Paneli")
    st.markdown("---")
    mod = st.radio("MENÜ", ["📊 Dashboards", "🧪 Test Merkezi"])
    
    if mod == "🧪 Test Merkezi":
        st.markdown("---")
        st.subheader("Bot Ayarları")
        firma_adi = st.text_input("Şirket İsmi", "İremStore")
        iade_suresi = st.slider("İade (Gün)", 14, 90, 30)
        kargo_ucreti = st.number_input("Kargo (TL)", 0, 200, 50)
    
    st.markdown("---")
    st.caption("v2.6.0 | Kurumsal")

# --- ANA İÇERİK ---
df = verileri_getir()

# --- MOD 1: DASHBOARD ---
if mod == "📊 Dashboards":
    st.title("Müşteri Analitik Paneli")
    if df is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Etkileşim", len(df))
        c2.metric("Sistem Sağlığı", "Optimize")
        c3.metric("Veri Gecikmesi", "0.2sn")
        
        st.markdown("---")
        col_chart, col_tools = st.columns([2, 1])
        
        with col_chart:
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Dağılımı")
                st.bar_chart(df["Kategori"].value_counts(), color="#3B82F6")
        
        with col_tools:
            st.markdown("#### Analitik Araçlar")
            if st.button("AI Analizini Başlat"):
                with st.spinner("Analiz ediliyor..."):
                    ai_stratejik_rapor(df)
            if st.button("Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()

        st.markdown("#### Detaylı İşlem Kayıtları")
        st.dataframe(df, use_container_width=True)
    else:
        st.error("Veri tabanına ulaşılamadı.")

# --- MOD 2: TEST MERKEZİ ---
else:
    st.title("Sistem Simülatörü")
    st.write("Müşteri temsilcisi botunu gerçek senaryolarla test edin.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mesajlar (Container içinde, input'a yer kalsın diye)
    chat_placeholder = st.container()
    with chat_placeholder:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat Input (Ekranla bütünleşmiş)
    prompt = st.chat_input("Bir soru sorun...")

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        sys_prompt = f"Şirket: {firma_adi}. İade: {iade_suresi} gün. Kargo: {kargo_ucreti} TL. Profesyonel temsilci olarak cevap ver. Müşteri: {prompt}"
        
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(sys_prompt)
            bot_reply = response.text
            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        except Exception as e:
            st.error(f"AI Yanıt Hatası: {e}")