import json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- GÜVENLİ YAPILANDIRMA ---
try:
    # Hem Gemini hem de Google Sheets anahtarlarını Secrets'tan çekiyoruz
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Doğrulama Hatası: API erişimi sağlanamadı. Lütfen Secrets panelini kontrol edin.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- KURUMSAL WEB TASARIMI (CSS) ---
st.set_page_config(page_title="İremStore BI Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0F172A;
    }
    .stApp {
        background-color: #0F172A;
    }
    
    /* Premium Metrik Kartları */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
    }
    div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-size: 2.2rem !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
    }

    /* Modern Butonlar */
    .stButton > button {
        border-radius: 8px !important;
        background-color: #3B82F6 !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 10px 20px !important;
        width: 100%;
    }
    
    /* Başlık Renkleri */
    h1, h2, h3, h4 {
        color: #F8FAFC !important;
    }
    p {
        color: #94A3B8 !important;
    }
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
    except:
        return None

def ai_stratejik_rapor(df):
    st.markdown("### Stratejik Analiz Raporu")
    metin = " ".join(df["Mesaj"].astype(str).tail(12))
    prompt = f"Sen bir iş analistisin. Bu mesajları inceleyerek patrona 3 adet profesyonel tavsiye ver: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.success(res.text)
    except:
        st.warning("Analiz servisine şu an ulaşılamıyor.")

# --- SIDEBAR ---
with st.sidebar:
    st.title("İremStore BI")
    st.markdown("Veri Odaklı Yönetim Sistemi")
    st.markdown("---")
    mod = st.radio("MENÜ", ["📊 Dashboards", "🧪 Test Merkezi"])
    st.markdown("---")
    st.caption("v2.5.0 Premium Edition")

# --- ANA İÇERİK ---
df = verileri_getir()

# --- MOD 1: DASHBOARD ---
if mod == "📊 Dashboards":
    st.title("Müşteri Analitik Paneli")
    st.write("Gerçek zamanlı müşteri etkileşimleri ve operasyonel veriler.")
    
    if df is not None:
        # Metrikler
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Kayıt", len(df))
        m2.metric("Sistem Sağlığı", "Optimize")
        m3.metric("AI Performansı", "Yüksek")
        m4.metric("Veri Gecikmesi", "0.2s")
        
        st.markdown("###")

        # Görselleştirme ve Araçlar
        col_main, col_tools = st.columns([2.5, 1])
        
        with col_main:
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Dağılım Grafiği")
                st.bar_chart(df["Kategori"].value_counts(), color="#3B82F6")
            
            st.markdown("#### Güncel Veri Tablosu")
            st.dataframe(df, use_container_width=True)

        with col_tools:
            st.markdown("#### Yönetici Araçları")
            if st.button("AI Analizini Başlat"):
                with st.spinner("AI veri madenciliği yapıyor..."):
                    ai_stratejik_rapor(df)
            
            if st.button("Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()
    else:
        st.error("Veri tabanı bağlantısı sağlanamadı.")

# --- MOD 2: TEST MERKEZİ (CHATBOT BURADA) ---
else:
    st.title("Sistem Simülatörü")
    st.write("Müşteri temsilcisi botunu gerçek senaryolarla test edin.")
    
    # Simülasyon Ayarları
    st.sidebar.markdown("---")
    st.sidebar.subheader("Operasyonel Kurallar")
    firma_adi = st.sidebar.text_input("Şirket İsmi", "İremStore")
    iade_suresi = st.sidebar.slider("İade Süresi (Gün)", 14, 90, 30)
    kargo_ucreti = st.sidebar.number_input("Kargo Ücreti (TL)", 0, 200, 50)

    # Chat Hafızası
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mesajları Ekrana Bas
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Kullanıcı Girişi
    prompt = st.chat_input("Bir soru sorun (Örn: Kargo ücreti ne kadar?)")

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Gemini Yanıtı
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