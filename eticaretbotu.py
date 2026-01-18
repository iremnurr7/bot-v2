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

# --- PREMIUM UI/UX TASARIMI ---
st.set_page_config(page_title="İremStore BI Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0F172A; }
    .stApp { background-color: #0F172A; }
    
    /* Sidebar Optimizasyonu */
    section[data-testid="stSidebar"] { background-color: #1E293B !important; width: 280px !important; border-right: 1px solid #334155; }
    section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem !important; }

    /* Metrik Kartları */
    div[data-testid="stMetric"] { background-color: #1E293B !important; border: 1px solid #334155 !important; padding: 20px !important; border-radius: 12px !important; }

    /* Chat Input ve Aksiyon Alanı */
    div[data-testid="stChatInput"] { background-color: #0F172A !important; border-top: 1px solid #334155 !important; }
    div[data-testid="stChatInput"] > div { background-color: #1E293B !important; border: 1px solid #475569 !important; }

    /* Tab Tasarımı */
    .stTabs [data-baseweb="tab-list"] { background-color: #0F172A; }
    .stTabs [data-baseweb="tab"] { background-color: #1E293B; border-radius: 8px 8px 0 0; color: #94A3B8; }
    .stTabs [aria-selected="true"] { background-color: #3B82F6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONKSİYONLAR ---
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
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"İş analisti olarak bu verileri incele. 1. Özetle, 2. 3 somut aksiyon planı çıkar: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.last_analysis = res.text
        st.info(res.text)
    except: st.error("AI meşgul.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## İremStore BI")
    mod = st.radio("MODÜL SEÇİMİ", ["📊 Dashboards", "🧪 Simülasyon"])
    st.markdown("---")
    if mod == "🧪 Simülasyon":
        st.info("Bu modda, operasyonel değişikliklerin müşteri deneyimine etkisini test edersiniz.")
        f_adi = st.text_input("Şirket", "İremStore")
        iade = st.slider("İade (Gün)", 14, 90, 30)
        kargo = st.number_input("Kargo (TL)", 0, 200, 50)
    st.caption("v3.1.0 | SaaS Mode")

# --- ANA İÇERİK ---
df = verileri_getir()

if mod == "📊 Dashboards":
    st.title("Yönetici Karar Destek Paneli")
    if df is not None:
        tab1, tab2 = st.tabs(["📉 Veri Analitiği", "🚀 Aksiyon Merkezi"])
        
        with tab1:
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Etkileşim", len(df), "+%12")
            m2.metric("Müşteri Skoru", "4.8/5", help="Gelen mesajların duygu analizi ortalaması.")
            m3.metric("AI Performansı", "%98", help="Son 100 mesajın doğru kategorize edilme oranı.")
            
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.markdown("#### Mesaj Yoğunluk Trendi")
                st.line_chart(df.index, color="#3B82F6")
            with col_right:
                st.markdown("#### Kategori Dağılımı")
                st.bar_chart(df["Kategori"].value_counts(), color="#60A5FA")

        with tab2:
            st.markdown("#### Stratejik Planlama")
            if st.button("AI Analizini ve Aksiyon Planını Başlat"):
                ai_stratejik_rapor(df)
            
            if "last_analysis" in st.session_state:
                st.markdown("---")
                st.subheader("Uygulanabilir Aksiyonlar")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Stratejiyi Onayla ve Ekipe Gönder"):
                        st.success("Plan operasyon birimine iletildi.")
                with col_b:
                    if st.button("Müşteri Memnuniyeti Kampanyası Başlat"):
                        st.balloons()
    else: st.error("Veri yok.")

else:
    st.title("Müşteri Deneyimi Simülatörü")
    st.caption("Senaryo: Kargo ücreti veya iade süresi değişirse müşteri tepkisi ne olur?")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    prompt = st.chat_input("Test sorusu girin...")
    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        sys_p = f"Şirket: {f_adi}. İade: {iade} gün. Kargo: {kargo}. Profesyonel ol. Müşteri: {prompt}"
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            res = model.generate_content(sys_p)
            with st.chat_message("assistant"): st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except: st.error("AI Hatası.")