import json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- KRİTİK YAPILANDIRMA ---
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Doğrulama Hatası: API erişimi sağlanamadı.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- PREMIUM UI/UX TASARIMI ---
st.set_page_config(page_title="İremStore BI Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #F9FAFB;
    }
    /* Metrik Kartları Gelişmiş */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #F3F4F6;
        padding: 20px !important;
        border-radius: 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    /* Sidebar Modernizasyon */
    .css-1d391kg {
        background-color: #111827;
    }
    .sidebar-text {
        color: #9CA3AF;
        font-size: 0.9rem;
    }
    /* Butonlar */
    .stButton > button {
        border-radius: 10px !important;
        background-color: #3B82F6 !important;
        border: none !important;
        padding: 10px 24px !important;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #2563EB !important;
        transform: scale(1.02);
    }
    </style>
    """, unsafe_allow_html=True)

# --- ANALİZ VE VERİ SİSTEMİ ---
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

def ai_stratejik_ozet(df):
    st.markdown("#### ⚡ Yapay Zeka Strateji Raporu")
    metin = " ".join(df["Mesaj"].astype(str).tail(12))
    prompt = f"Analist olarak bu verileri yorumla ve patrona 3 somut tavsiye ver: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.info(res.text)
    except: st.warning("Analiz şu an gerçekleştirilemiyor.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### İremStore BI")
    st.markdown("<p class='sidebar-text'>Veri Odaklı Yönetim Paneli</p>", unsafe_allow_html=True)
    st.markdown("---")
    mod = st.radio("ANA MENÜ", ["📈 Dashboards", "🛠️ Sistem Testleri"])
    st.markdown("---")
    st.caption("Versiyon 2.5.0 Premium")

# --- ANA İÇERİK ---
df = verileri_getir()

if mod == "📈 Dashboards":
    st.title("Müşteri Deneyimi Analitik Paneli")
    st.write("Veriler üzerinden işletme performansınızı anlık olarak takip edin.")
    
    if df is not None:
        # Metrikler
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Kayıt", len(df))
        c2.metric("Müşteri Memnuniyeti", "%94", "+2.1")
        c3.metric("AI Yanıt Hızı", "1.2sn")
        c4.metric("Sistem Durumu", "Stabil")
        
        st.markdown("###")

        # Grafik ve Araçlar
        col_main, col_side = st.columns([2, 1])
        
        with col_main:
            if "Kategori" in df.columns:
                st.markdown("#### Mesaj Konularına Göre Dağılım")
                st.bar_chart(df["Kategori"].value_counts(), color="#3B82F6")
            
            st.markdown("#### Detaylı İşlem Geçmişi")
            st.dataframe(df, use_container_width=True)

        with col_side:
            st.markdown("#### Aksiyon Merkezi")
            if st.button("🚀 AI Analizini Çalıştır"):
                with st.spinner("Veriler işleniyor..."):
                    ai_stratejik_ozet(df)
            
            if st.button("🔄 Veri Akışını Yenile"):
                st.cache_data.clear()
                st.rerun()
            
            st.markdown("---")
            st.markdown("**Not:** Analizler son 12 etkileşimi kapsar.")
    else:
        st.error("Veri tabanına ulaşılamadı. Lütfen bağlantı ayarlarını kontrol edin.")

else:
    st.title("Sistem Simülasyonu")
    st.write("Müşteri temsilcisi botunu gerçek senaryolarla test edin.")
    # Chatbot kısmı buraya gelecek