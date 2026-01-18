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

# --- MODERN WEB TASARIMI (CSS) ---
st.set_page_config(page_title="İremStore | Business Intelligence", layout="wide")

st.markdown("""
    <style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #F4F7F9;
    }
    /* Kart Yapıları */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #1E3A8A !important;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 25px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #E5E7EB;
    }
    /* Buton Tasarımları */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #2563EB !important;
        color: white !important;
        font-weight: 600;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
    }
    /* Tablo Güzelleştirme */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VERİ VE ANALİZ ---
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

def ai_analiz_raporu(df):
    st.markdown("### 🔍 Stratejik Analiz Sonuçları")
    analiz_verisi = " ".join(df["Mesaj"].astype(str).tail(10))
    prompt = f"Sen profesyonel bir iş analistisin. Şu mesajları analiz et ve 3 maddede patrona özetle: {analiz_verisi}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        st.success(response.text)
    except: st.error("AI Analizi şu an yapılamıyor.")

# --- YAN MENÜ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3222/3222800.png", width=100)
    st.title("Yönetim Paneli")
    st.markdown("---")
    mod = st.radio("MENÜ", ["📊 Veri Analizi", "⚙️ Sistem Testi"])
    st.markdown("---")
    st.caption("İremStore v2.1.0")

# --- ANA EKRAN ---
df = verileri_getir()

if mod == "📊 Veri Analizi":
    st.header("Müşteri İlişkileri Karar Destek Sistemi")
    st.markdown("İşletmenizin performans metriklerini ve müşteri etkileşimlerini buradan takip edebilirsiniz.")
    
    if df is not None:
        # Üst Metrik Kartları
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Toplam Etkileşim", len(df))
        with c2: st.metric("Sistem Sağlığı", "Optimize")
        with c3: st.metric("AI Analiz Durumu", "Hazır")
        
        st.markdown("###") # Boşluk
        
        # Orta Bölüm: Analiz ve Grafik
        col_btn, col_chart = st.columns([1, 2])
        with col_btn:
            st.markdown("#### Operasyonel Araçlar")
            if st.button("Stratejik Analiz Başlat"):
                with st.spinner("Analiz ediliyor..."):
                    ai_analiz_raporu(df)
            if st.button("Verileri Güncelle"):
                st.cache_data.clear()
                st.rerun()
        
        with col_chart:
            if "Kategori" in df.columns:
                st.markdown("#### Mesaj Yoğunluk Dağılımı")
                st.bar_chart(df["Kategori"].value_counts(), color="#2563EB")

        st.markdown("###") # Boşluk
        st.markdown("#### Detaylı Veri Kayıtları")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Veri bağlantısı kurulamadı.")

else:
    st.header("Sistem Simülatörü")
    st.markdown("Botun çalışma parametrelerini test edin.")
    # Chat sistemi buraya gelecek (Eski kodundaki chatbot kısmı)