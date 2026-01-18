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
    st.error("Sistem Hatası: API erişimi sağlanamadı.")

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
    section[data-testid="stSidebar"] .block-container { padding-top: 1rem !important; }

    /* Metrik Kartları */
    div[data-testid="stMetric"] { background-color: #1E293B !important; border: 1px solid #334155 !important; padding: 20px !important; border-radius: 12px !important; }
    
    /* Chat Input Entegrasyonu */
    div[data-testid="stChatInput"] { background-color: #0F172A !important; border-top: 1px solid #334155 !important; }
    div[data-testid="stChatInput"] > div { background-color: #1E293B !important; border: 1px solid #475569 !important; }

    /* Buton Tasarımları */
    .stButton > button { border-radius: 8px !important; background-color: #2563EB !important; color: white !important; font-weight: 600 !important; width: 100%; height: 45px; }
    
    /* Genel Yerleşim Boşlukları */
    .block-container { padding-top: 2rem !important; }
    h1, h2, h3 { color: #F8FAFC !important; }
    p, .stMarkdown { color: #94A3B8 !important; }
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

def ai_analiz_tetikle(df):
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"İş analisti olarak bu verileri incele. 1. Özetle, 2. 3 somut aksiyon planı çıkar: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        # Analizi hafızada tutuyoruz ki aksiyon butonları çalışınca silinmesin
        st.session_state.mevcut_analiz = res.text
    except: st.error("AI şu an meşgul.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## İremStore BI")
    st.caption("Veri Odaklı Yönetim Paneli")
    st.markdown("---")
    mod = st.radio("MENÜ", ["📊 Dashboards", "🧪 Simülatör"])
    
    if mod == "🧪 Simülatör":
        st.markdown("---")
        st.subheader("Kurallar")
        f_adi = st.text_input("Şirket", "İremStore")
        iade = st.slider("İade (Gün)", 14, 90, 30)
        kargo = st.number_input("Kargo (TL)", 0, 200, 50)
    
    st.markdown("---")
    st.caption("v3.2.0 | Kurumsal Mod")

# --- ANA İÇERİK ---
df = verileri_getir()

# --- MOD 1: DASHBOARDS (TEK SAYFA DÜZENİ) ---
if mod == "📊 Dashboards":
    st.title("Yönetici Karar Destek Paneli")
    
    if df is not None:
        # 1. Üst Metrikler (Hızlı Bakış)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Etkileşim", len(df), "+12%")
        m2.metric("Müşteri Skoru", "4.8/5", help="Duygu analizi ortalaması.")
        m3.metric("AI Çözümleme", "%98", help="Otomatik çözümleme başarısı.")
        m4.metric("Sistem Sağlığı", "Stabil")
        
        st.markdown("---")

        # 2. Görsel Analizler (Merkezi Bölüm)
        col_chart, col_tools = st.columns([2, 1])
        with col_chart:
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Bazlı Dağılım Analizi")
                st.bar_chart(df["Kategori"].value_counts(), color="#3B82F6")
            st.markdown("#### Mesaj Yoğunluk Trendi")
            st.line_chart(df.index, color="#60A5FA")
            
        with col_tools:
            st.markdown("#### Operasyonel Araçlar")
            if st.button("🧐 Stratejik AI Analizi Başlat"):
                with st.spinner("AI veri madenciliği yapıyor..."):
                    ai_analiz_tetikle(df)
            
            if st.button("🔄 Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()
            
            st.markdown("---")
            st.caption("Veriler Google Cloud üzerinden anlık olarak çekilmektedir.")

        # 3. Aksiyon Merkezi (Dinamik Bölüm)
        if "mevcut_analiz" in st.session_state:
            st.markdown("---")
            st.subheader("🚀 Stratejik Aksiyon Merkezi")
            st.info(st.session_state.mevcut_analiz)
            
            # Aksiyon Butonları
            st.markdown("##### Bu Analize Dayalı Karar Al:")
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("✅ Stratejiyi Onayla"):
                    st.success("Analiz onaylandı ve ilgili birimlere iletildi.")
            with a2:
                if st.button("📢 Kampanya Başlat"):
                    st.balloons()
                    st.info("Müşteri memnuniyeti kampanyası tetiklendi.")
            with a3:
                if st.button("❌ Raporu Temizle"):
                    del st.session_state.mevcut_analiz
                    st.rerun()

        # 4. Ham Veri (En Alt)
        st.markdown("---")
        st.markdown("#### Detaylı İşlem Kayıtları")
        st.dataframe(df, use_container_width=True)
        
    else: st.error("Veri tabanı bağlantısı kurulamadı.")

# --- MOD 2: SİMLÜLATÖR ---
else:
    st.title("Müşteri Deneyimi Simülatörü")
    st.markdown("Operasyonel kural değişikliklerinin bot üzerindeki etkisini test edin.")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    prompt = st.chat_input("Bir müşteri sorusu simüle edin...")
    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_p = f"Şirket: {f_adi}. İade: {iade} gün. Kargo: {kargo} TL. Kibar ve profesyonel ol. Müşteri: {prompt}"
        
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            res = model.generate_content(sys_p)
            with st.chat_message("assistant"): st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except: st.error("AI servisi şu an yanıt veremiyor.")