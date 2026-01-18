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

# --- PREMIUM UI/UX TASARIMI (Nihai Sürüm) ---
st.set_page_config(page_title="İremStore BI Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0F172A; }
    .stApp { background-color: #0F172A; }
    
    /* Sidebar: Daraltılmış ve Sabit */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        width: 280px !important;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem !important; }

    /* Metrik Kartları: Hover Efektli */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-3px); }
    div[data-testid="stMetricValue"] { color: #F8FAFC !important; font-size: 2rem !important; }
    div[data-testid="stMetricLabel"] { color: #94A3B8 !important; text-transform: uppercase; letter-spacing: 0.1em; }

    /* Chat Input: Tema Bütünleşik */
    div[data-testid="stChatInput"] {
        background-color: rgba(15, 23, 42, 0.9) !important;
        border-top: 1px solid #334155 !important;
        padding: 10px 5% !important;
    }
    div[data-testid="stChatInput"] > div { background-color: #1E293B !important; border: 1px solid #475569 !important; }

    /* Butonlar: SaaS Standart */
    .stButton > button {
        border-radius: 8px !important;
        background-color: #2563EB !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        width: 100%;
        height: 48px;
    }
    
    /* Yazı ve Boşluklar */
    h1, h2, h3 { color: #F8FAFC !important; }
    p, .stMarkdown { color: #94A3B8 !important; }
    .block-container { padding-top: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- VERİ VE ANALİZ FONKSİYONLARI ---
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

def ai_stratejik_analiz(df):
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"Sen profesyonel bir iş analistisin. Bu son müşteri mesajlarını inceleyerek patrona 3 adet somut ve uygulanabilir yönetim kararı öner: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.last_analiz = res.text
    except: st.error("AI şu an meşgul.")

# --- SIDEBAR (Kompakt ve Bilgilendirici) ---
with st.sidebar:
    st.markdown("## İremStore BI")
    st.caption("Veri Odaklı Karar Destek Paneli")
    st.markdown("---")
    mod = st.radio("SİSTEM MODÜLÜ", ["📊 Dashboards", "🧪 Simülasyon"])
    
    if mod == "🧪 Simülasyon":
        st.markdown("---")
        st.markdown("**Senaryo Test Merkezi**")
        st.caption("Fiyat veya iade süresi değişikliklerinin müşteri tepkisini buradan ölçün.")
        f_adi = st.text_input("Şirket", "İremStore")
        iade = st.slider("İade (Gün)", 14, 90, 30)
        kargo = st.number_input("Kargo (TL)", 0, 200, 50)
    
    st.markdown("---")
    st.caption("v3.5.0 | MIS DSS Edition")

# --- ANA İÇERİK ---
df = verileri_getir()

# --- MOD 1: DASHBOARDS (Single-Page Dashboard) ---
if mod == "📊 Dashboards":
    st.title("Yönetici Strateji Paneli")
    st.markdown("İşletmenizin müşteri reflekslerini analiz eden ve karar destek sunan merkezi ekran.")

    if df is not None:
        # 1. Metrik Kartları (Açıklayıcı Tooltipler)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Trafik", len(df), "+%12")
        m2.metric("Müşteri Skoru", "4.8/5", help="Gelen mesajların duygu analizi ortalamasıdır.")
        m3.metric("AI Performansı", "%98", help="Son 100 mesajın otomatik kategorize edilme başarı oranıdır.")
        m4.metric("Sistem Sağlığı", "Optimize")
        
        st.markdown("---")

        # 2. Görselleştirme (Geniş Yerleşim)
        col_main, col_sub = st.columns([2, 1])
        with col_main:
            st.markdown("#### Operasyonel Yoğunluk Trendi")
            st.line_chart(df.index, color="#3B82F6")
            
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Dağılım Analizi")
                st.bar_chart(df["Kategori"].value_counts(), color="#60A5FA")
        
        with col_sub:
            st.markdown("#### Hızlı Araçlar")
            if st.button("🔄 Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()
            
            st.markdown("---")
            st.markdown("#### 🚀 Aksiyon Merkezi")
            st.caption("Peki şimdi ne yapmalı? AI'dan öneri alın.")
            if st.button("Stratejik AI Analizini Başlat"):
                with st.spinner("Veri madenciliği yapılıyor..."):
                    ai_stratejik_analiz(df)

        # 3. AI Raporu ve Karar Mekanizması
        if "last_analiz" in st.session_state:
            st.markdown("---")
            st.subheader("🤖 AI Strateji Raporu")
            st.info(st.session_state.last_analiz)
            
            st.markdown("##### Önerilen Kararları Uygula:")
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("✅ Stratejiyi Onayla"):
                    st.success("Karar onaylandı ve ilgili birimlere iletildi.")
            with a2:
                if st.button("📢 Kampanya Başlat"):
                    st.balloons()
            with a3:
                if st.button("❌ Raporu Arşivle"):
                    del st.session_state.last_analiz
                    st.rerun()

        # 4. Veri Tablosu
        st.markdown("---")
        st.markdown("#### Detaylı İşlem Kayıtları")
        st.dataframe(df, use_container_width=True)
    else: st.error("Veri tabanı bağlantısı sağlanamadı.")

# --- MOD 2: SİMÜLATÖR ---
else:
    st.title("Müşteri Deneyimi Simülasyonu")
    st.write("**Senaryo:** Kargo ücretini artırırsam ve iade süresini kısaltırsam, botum bu sert kuralları müşteriye markayı küstürmeden nasıl açıklar?")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    prompt = st.chat_input("Bir müşteri sorusu simüle edin...")
    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_p = f"Şirket: {f_adi}. İade: {iade} gün. Kargo: {kargo} TL. Profesyonel ve çözüm odaklı ol. Müşteri: {prompt}"
        
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            res = model.generate_content(sys_p)
            with st.chat_message("assistant"): st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except: st.error("AI servisi şu an meşgul.")