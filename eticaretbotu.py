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
    st.error("Sistem Hatası: Yetkilendirme başarısız.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- PREMIUM UI/UX TASARIMI (Optimize Edilmiş CSS) ---
st.set_page_config(page_title="İremStore BI Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Global Temizlik */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0F172A;
        overflow-x: hidden;
    }
    .stApp { background-color: #0F172A; }
    
    /* Sidebar Optimizasyonu: Boşlukları ve Kaydırmayı Bitirir */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        width: 280px !important;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] .block-container {
        padding: 1.5rem 1rem !important;
    }
    .st-emotion-cache-6qob1r { padding-top: 1rem !important; } /* Üst boşluk daraltma */

    /* Metrik Kartları */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        border-radius: 12px !important;
    }
    div[data-testid="stMetricValue"] { color: #F8FAFC !important; font-size: 2rem !important; }
    div[data-testid="stMetricLabel"] { color: #94A3B8 !important; text-transform: uppercase; letter-spacing: 0.1em; }

    /* Chat Input Entegrasyonu: Siyahlıktan Kurtarma */
    div[data-testid="stChatInput"] {
        background-color: rgba(15, 23, 42, 0.9) !important;
        border-top: 1px solid #334155 !important;
        padding: 15px 5% !important;
    }
    div[data-testid="stChatInput"] > div {
        background-color: #1E293B !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #F8FAFC !important;
    }

    /* Butonlar ve Genel Form */
    .stButton > button {
        border-radius: 8px !important;
        background-color: #2563EB !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton > button:hover { background-color: #1D4ED8 !important; transform: translateY(-1px); }
    
    /* Header ve Yazı Stilleri */
    h1, h2, h3 { color: #F8FAFC !important; margin-bottom: 0.5rem !important; }
    .block-container { padding-top: 2rem !important; }
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
    st.markdown("### Analitik Değerlendirme")
    metin = " ".join(df["Mesaj"].astype(str).tail(12))
    prompt = f"İş analisti olarak bu müşteri verilerini yorumla ve 3 kritik tavsiye ver: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.info(res.text)
    except: st.error("AI servisi şu an meşgul.")

# --- SIDEBAR (Kompakt Düzen) ---
with st.sidebar:
    st.markdown("## İremStore BI")
    st.caption("Veri Odaklı Yönetim Paneli")
    st.markdown("---")
    mod = st.radio("SİSTEM MODÜLÜ", ["Dashboards", "Test Merkezi"])
    
    if mod == "Test Merkezi":
        st.markdown("---")
        st.markdown("**Simülasyon Parametreleri**")
        firma_adi = st.text_input("Şirket", "İremStore")
        iade_suresi = st.slider("İade (Gün)", 14, 90, 30)
        kargo_ucreti = st.number_input("Kargo (TL)", 0, 200, 50)
    
    st.markdown("---")
    st.caption("v2.7.0 Premium")

# --- ANA İÇERİK ---
df = verileri_getir()

# --- MOD 1: DASHBOARD ---
if mod == "Dashboards":
    st.title("İş Zekası Paneli")
    if df is not None:
        # Metrikler
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Etkileşim", len(df))
        c2.metric("Sistem Sağlığı", "Optimize")
        c3.metric("Veri Gecikmesi", "0.1s")
        
        st.markdown("###")
        
        # Analiz ve Grafik
        col_main, col_tools = st.columns([2, 1])
        
        with col_main:
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Dağılımı")
                st.bar_chart(df["Kategori"].value_counts(), color="#3B82F6")
            
            st.markdown("#### Güncel İşlem Kayıtları")
            st.dataframe(df, use_container_width=True)

        with col_tools:
            st.markdown("#### Karar Destek")
            if st.button("AI Stratejik Rapor"):
                with st.spinner("Veri madenciliği yapılıyor..."):
                    ai_stratejik_rapor(df)
            if st.button("Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()
    else:
        st.error("Veri tabanı bağlantısı kurulamadı.")

# --- MOD 2: TEST MERKEZİ ---
else:
    st.title("Müşteri Temsilcisi Simülasyonu")
    st.write("Botun operasyonel kurallarını yan menüden belirleyip etkileşimi test edebilirsiniz.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat Akışı
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Entegre Chat Input
    prompt = st.chat_input("Bir müşteri sorusu simüle edin...")

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        sys_prompt = f"Şirket: {firma_adi}. İade: {iade_suresi} gün. Kargo: {kargo_ucreti} TL. Profesyonel ve kısa cevap ver. Müşteri: {prompt}"
        
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(sys_prompt)
            bot_reply = response.text
            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        except Exception as e:
            st.error(f"Hata: {e}")