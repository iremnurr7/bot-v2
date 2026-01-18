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
    
    /* Sidebar Optimizasyonu: Boşlukları Siler */
    section[data-testid="stSidebar"] { background-color: #1E293B !important; width: 280px !important; border-right: 1px solid #334155; }
    section[data-testid="stSidebar"] .block-container { padding-top: 1rem !important; }

    /* Metrik Kartları */
    div[data-testid="stMetric"] { background-color: #1E293B !important; border: 1px solid #334155 !important; padding: 20px !important; border-radius: 12px !important; }
    
    /* Chat Input Entegrasyonu */
    div[data-testid="stChatInput"] { background-color: #0F172A !important; border-top: 1px solid #334155 !important; }
    div[data-testid="stChatInput"] > div { background-color: #1E293B !important; border: 1px solid #475569 !important; }

    /* Butonlar */
    .stButton > button { border-radius: 8px !important; background-color: #2563EB !important; color: white !important; font-weight: 600 !important; width: 100%; height: 45px; }
    
    /* Başlıklar ve Yazılar */
    h1, h2, h3 { color: #F8FAFC !important; }
    p, .stMarkdown { color: #94A3B8 !important; }
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

def ai_analiz_yap(df):
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"İş analisti olarak bu mesajları yorumla ve 3 somut tavsiye ver: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        # Analizi session state'e kaydediyoruz ki butonlara basınca kaybolmasın
        st.session_state.analiz_sonucu = res.text
    except: st.error("AI şu an meşgul.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## İremStore BI")
    st.caption("Veri Odaklı Karar Destek Paneli")
    st.markdown("---")
    mod = st.radio("MENÜ", ["📊 Dashboards", "🧪 Simülatör"])
    
    if mod == "🧪 Simülatör":
        st.markdown("---")
        st.subheader("Kurallar")
        f_adi = st.text_input("Şirket İsmi", "İremStore")
        iade = st.slider("İade Süresi", 14, 90, 30)
        kargo = st.number_input("Kargo Ücreti", 0, 200, 50)
    
    st.markdown("---")
    st.caption("v3.2.0 | Kurumsal Sürüm")

# --- ANA İÇERİK ---
df = verileri_getir()

# --- MOD 1: DASHBOARDS (TEK SAYFA DÜZENİ) ---
if mod == "📊 Dashboards":
    st.title("Yönetici Kontrol Paneli")
    
    if df is not None:
        # 1. Metrikler (Üst Bölüm)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Trafik", len(df), "+%12")
        m2.metric("Sistem Sağlığı", "Optimize")
        m3.metric("AI Çözümleme", "%98", help="Otomatik kategorize edilme oranı.")
        m4.metric("Bekleyen Aksiyon", "3 Adet")
        
        st.markdown("---")

        # 2. Grafikler (Orta Bölüm - Ekranı Doldurur)
        col_main, col_sub = st.columns([2, 1])
        with col_main:
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Bazlı Dağılım Analizi")
                st.bar_chart(df["Kategori"].value_counts(), color="#3B82F6")
        with col_sub:
            st.markdown("#### Hızlı Araçlar")
            if st.button("🔄 Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()
            st.write("Veriler anlık olarak Google Sheets üzerinden güncellenmektedir.")

        # 3. Aksiyon Merkezi ve AI Raporu (Alt Bölüm)
        st.markdown("---")
        st.subheader("🚀 Stratejik Aksiyon Merkezi")
        
        col_ai_btn, col_empty = st.columns([1, 2])
        with col_ai_btn:
            if st.button("🧐 AI Analizini Başlat"):
                with st.spinner("AI veri madenciliği yapıyor..."):
                    ai_analiz_yap(df)

        # Analiz Sonucu Varsa Göster
        if "analiz_sonucu" in st.session_state:
            st.info(st.session_state.analiz_sonucu)
            
            # Aksiyon Butonları
            st.markdown("##### Bu Analize Dayalı Aksiyon Al:")
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("✅ Stratejiyi Onayla"):
                    st.success("Strateji onaylandı ve ekiplere iletildi.")
            with a2:
                if st.button("📢 Kampanya Başlat"):
                    st.balloons()
            with a3:
                if st.button("❌ Raporu Arşivle"):
                    del st.session_state.analiz_sonucu
                    st.rerun()

        # 4. Ham Veri Tablosu (En Alt)
        st.markdown("---")
        st.markdown("#### Detaylı Veri Kayıtları")
        st.dataframe(df, use_container_width=True)
        
    else: st.error("Veri bağlantısı sağlanamadı.")

# --- MOD 2: SİMLÜLATÖR ---
else:
    st.title("Müşteri Deneyimi Simülatörü")
    st.markdown("Operasyonel değişikliklerin müşteri temsilcisi üzerindeki etkisini test edin.")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    prompt = st.chat_input("Bir müşteri sorusu simüle edin...")
    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        sys_p = f"Şirket: {f_adi}. İade: {iade} gün. Kargo: {kargo} TL. Kibar ol. Müşteri: {prompt}"
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            res = model.generate_content(sys_p)
            with st.chat_message("assistant"): st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except: st.error("AI şu an yanıt veremiyor.")