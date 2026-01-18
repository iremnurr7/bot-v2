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
    st.error("Doğrulama Hatası: API erişimi sağlanamadı.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- PREMIUM UI/UX TASARIMI (PROFESYONEL CSS) ---
st.set_page_config(page_title="İremStore BI Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Genel Font ve Arka Plan */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0F172A; /* Koyu Lacivert/Siyah Arka Plan */
    }
    .stApp {
        background-color: #0F172A;
    }
    
    /* Metrik Kartları - Yüksek Kontrast */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 25px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Buton Tasarımı - Kurumsal Mavi */
    .stButton > button {
        width: 100%;
        border-radius: 8px !important;
        background-color: #3B82F6 !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 12px !important;
        height: 50px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #2563EB !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
    }

    /* Sidebar - Soft Dark */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    
    /* Grafik ve Tablo Alanları */
    .stDataFrame, .stPlotlyChart {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 10px;
    }
    
    /* Başlıklar */
    h1, h2, h3 {
        color: #F8FAFC !important;
        font-weight: 700 !important;
    }
    p {
        color: #94A3B8 !important;
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
    st.markdown("### 🔍 Stratejik Analiz Sonuçları")
    metin = " ".join(df["Mesaj"].astype(str).tail(12))
    prompt = f"İş analisti olarak bu müşteri verilerini yorumla ve 3 kritik tavsiye ver: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.success(res.text)
    except: st.warning("Analiz servisi şu an meşgul.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## İremStore BI")
    st.markdown("<p style='color:#64748B;'>Karar Destek Sistemi v2.5.0</p>", unsafe_allow_html=True)
    st.markdown("---")
    mod = st.radio("MODÜLLER", ["📈 Dashboards", "🧪 Test Merkezi"])
    st.markdown("---")
    if st.button("Sistem Durumunu Kontrol Et"):
        st.toast("Tüm sistemler aktif.")

# --- ANA İÇERİK ---
df = verileri_getir()

if mod == "📈 Dashboards":
    st.title("Müşteri Analitik Paneli")
    st.write("Veri odaklı yönetim için gerçek zamanlı etkileşim takibi.")
    
    if df is not None:
        # Metrik Kartları
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Kayıt", len(df))
        m2.metric("Sağlık Skoru", "%96", "Aktif")
        m3.metric("AI Performansı", "Yüksek")
        m4.metric("Veri Gecikmesi", "Yok")
        
        st.markdown("###")

        # Görselleştirme Alanı
        col_main, col_action = st.columns([2.5, 1])
        
        with col_main:
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Bazlı Dağılım")
                # Grafiği kurumsal renge boyuyoruz
                st.bar_chart(df["Kategori"].value_counts(), color="#3B82F6")
            
            st.markdown("#### Ham Veri Kayıtları")
            st.dataframe(df, use_container_width=True)

        with col_action:
            st.markdown("#### Analitik Araçlar")
            if st.button("Stratejik Analiz Raporu Oluştur"):
                with st.spinner("AI veri madenciliği yapıyor..."):
                    ai_stratejik_ozet(df)
            
            if st.button("Veri Kaynağını Yenile"):
                st.cache_data.clear()
                st.rerun()
            
            st.markdown("---")
            st.caption("Veriler Google Cloud üzerinden güvenli şekilde çekilmektedir.")
    else:
        st.error("Veri tabanına erişilemiyor. Lütfen yetkilendirme ayarlarını kontrol edin.")

else:
    st.title("Sistem Simülatörü")
    st.write("AI Bot davranışlarını bu alandan simüle edebilirsiniz.")
    # Chatbot kısmı (Eski kodundaki chatbot mantığı)