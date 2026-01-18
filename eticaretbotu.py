import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px # YENİ: Grafikler için gerekli
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
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0F172A;
    }
    .stApp { background-color: #0F172A; }
    
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        width: 260px !important;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] .block-container { padding: 1rem !important; }

    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        border-radius: 12px !important;
    }

    div[data-testid="stChatInput"] {
        background-color: #0F172A !important;
        border-top: 1px solid #334155 !important;
    }
    div[data-testid="stChatInput"] > div {
        background-color: #1E293B !important;
        border: 1px solid #475569 !important;
    }

    .stTabs [data-baseweb="tab-list"] { background-color: #0F172A; gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #1E293B;
        border-radius: 8px 8px 0 0;
        color: #94A3B8;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #3B82F6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- VERİ FONKSİYONLARI ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        # YENİ: Sütun isimlerini standartlaştırıyoruz ki grafikler hata vermesin
        if not df.empty and len(df.columns) >= 6:
            df.columns = ["Tarih", "Kimden", "Konu", "Mesaj", "Kategori", "AI_Cevap"]
        return df
    except: return None

def ai_analiz_yap(df):
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"İş analisti olarak son 15 mesajı özetle ve patrona 3 somut aksiyon öner: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.analiz_sonucu = res.text
    except:
        st.error("AI şu an meşgul.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## İremStore BI")
    mod = st.radio("SİSTEM MODÜLÜ", ["📊 Dashboards", "🧪 Simülatör"])
    st.markdown("---")
    if mod == "🧪 Simülatör":
        st.subheader("Kurallar")
        f_adi = st.text_input("Şirket", "İremStore")
        iade = st.slider("İade", 14, 90, 30)
        kargo = st.number_input("Kargo", 0, 200, 50)
    st.caption("v3.2.0 Pro Analytics")

# --- ANA İÇERİK ---
df = verileri_getir()

if mod == "📊 Dashboards":
    st.title("🚀 Stratejik Karar Destek Merkezi")
    
    if df is not None and not df.empty:
        # --- ÜST KPI KARTLARI (YENİ) ---
        kp1, kp2, kp3 = st.columns(3)
        
        toplam_mail = len(df)
        # Sadece IADE kategorisindekileri say
        iade_sayisi = len(df[df["Kategori"] == "IADE"])
        # AI cevabında 'dolmuştur' veya 'red' geçenleri say (Otomatik engellenenler)
        reddedilenler = len(df[df["AI_Cevap"].str.contains("dolmuştur|red|geçmiş", case=False, na=False)])
        
        kp1.metric("Toplam Gelen Mail", toplam_mail, border=True)
        kp2.metric("İade Talepleri", iade_sayisi, f"Genelin %{(iade_sayisi/toplam_mail)*100:.1f}'i", border=True)
        kp3.metric("⛔ Botun Reddettiği", reddedilenler, "Otomatik Koruma", border=True)

        st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["📉 Görsel Analiz", "🧠 AI Strateji", "📋 Detaylı Veri"])
        
        with tab1:
            col_grafik1, col_grafik2 = st.columns(2)
            
            with col_grafik1:
                st.subheader("📁 Müşteri Ne İstiyor?")
                # Pasta Grafiği
                kategori_ozet = df["Kategori"].value_counts().reset_index()
                kategori_ozet.columns = ["Kategori", "Adet"]
                fig_pie = px.pie(kategori_ozet, values='Adet', names='Kategori', 
                                 title='Kategori Dağılımı', 
                                 color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_grafik2:
                st.subheader("📅 Günlük Mesaj Trafiği")
                # Tarih verisini sadeleştirme (sadece gün)
                df["Gun"] = pd.to_datetime(df["Tarih"]).dt.date
                gunluk_mail = df["Gun"].value_counts().sort_index()
                st.bar_chart(gunluk_mail, color="#3B82F6")
                
        with tab2:
            st.markdown("#### AI Destekli İşletme Raporu")
            if st.button("Kapsamlı Analizi Başlat"):
                with st.spinner("AI veri madenciliği yapıyor..."):
                    ai_analiz_yap(df)
            
            if "analiz_sonucu" in st.session_state:
                st.info(st.session_state.analiz_sonucu)
        
        with tab3:
            st.subheader("🔍 Akıllı Veri Filtreleme")
            
            # YENİ: Filtreleme Seçeneği
            secilenler = st.multiselect(
                "Görmek istediğiniz kategorileri seçin:",
                options=df["Kategori"].unique(),
                default=df["Kategori"].unique()
            )
            
            df_filtreli = df[df["Kategori"].isin(secilenler)]
            st.dataframe(df_filtreli, use_container_width=True, height=400)
            
            if st.button("Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("Henüz yeterli veri yok veya bağlantı kurulamadı.")

else:
    # --- BURASI SENİN ESKİ SİMÜLATÖRÜN (DOKUNULMADI) ---
    st.title("Müşteri Deneyimi Simülatörü")
    st.caption("Senaryo: Kargo ücreti veya iade süresi değişirse bot markayı nasıl korur?")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    prompt = st.chat_input("Bir müşteri sorusu simüle edin...")
    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        sys_p = f"Şirket: {f_adi}. İade: {iade} gün. Kargo: {kargo} TL. Profesyonel ol. Müşteri: {prompt}"
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            res = model.generate_content(sys_p)
            with st.chat_message("assistant"): st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except Exception as e: st.error(f"AI Hatası: {e}")