import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- GÜVENLİ YAPILANDIRMA ---
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Sistem Hatası: Yetkilendirme başarısız.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- TASARIM AYARLARI ---
st.set_page_config(page_title="İremStore Yönetim Paneli", layout="wide")

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
        border-right: 1px solid #334155;
    }
    
    /* Metrik Kartları Tasarımı */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VERİ ÇEKME FONKSİYONU ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        
        if not df.empty and len(df.columns) >= 6:
            df.columns = ["Tarih", "Kimden", "Konu", "Mesaj", "Kategori", "AI_Cevap"]
        return df
    except: return None

# --- AI ANALİZ FONKSİYONU ---
def ai_analiz_yap(df):
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"İş analisti olarak son 15 mesajı özetle ve patrona 3 somut aksiyon öner: {metin}"
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.analiz_sonucu = res.text
    except:
        st.error("AI şu an meşgul.")

# --- SIDEBAR (TEMİZLENDİ) ---
with st.sidebar:
    st.title("İremStore BI")
    st.info("Yönetim Paneli v1.0")
    st.markdown("---")
    st.caption("Geliştirici: İrem")
    st.caption("Powered by Google Gemini")
    
    if st.button("Verileri Yenile"):
        st.cache_data.clear()
        st.rerun()

# --- ANA EKRAN (DASHBOARD) ---
st.title("🚀 Stratejik Karar Destek Merkezi")

df = verileri_getir()

if df is not None and not df.empty:
    # 1. KPI KARTLARI
    kp1, kp2, kp3 = st.columns(3)
    
    toplam_mail = len(df)
    iade_sayisi = len(df[df["Kategori"] == "IADE"])
    # "red" veya "dolmuştur" kelimesi geçenleri say
    reddedilenler = len(df[df["AI_Cevap"].str.contains("dolmuştur|red|geçmiş", case=False, na=False)])
    
    kp1.metric("Toplam Gelen Mail", toplam_mail, border=True)
    kp2.metric("İade Talepleri", iade_sayisi, f"Genelin %{(iade_sayisi/toplam_mail)*100:.1f}'i", border=True)
    kp3.metric("⛔ Botun Reddettiği", reddedilenler, "Otomatik Koruma", border=True)

    st.markdown("---")

    # 2. GRAFİKLER VE RAPORLAR
    tab1, tab2, tab3 = st.tabs(["📉 Görsel Analiz", "🧠 AI Strateji", "📋 Detaylı Veri"])
    
    with tab1:
        col_grafik1, col_grafik2 = st.columns(2)
        
        with col_grafik1:
            st.subheader("📁 Kategori Dağılımı")
            kategori_ozet = df["Kategori"].value_counts().reset_index()
            kategori_ozet.columns = ["Kategori", "Adet"]
            fig_pie = px.pie(kategori_ozet, values='Adet', names='Kategori', 
                             title='Müşteri Talepleri', 
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_grafik2:
            st.subheader("📅 Günlük Trafik")
            df["Gun"] = pd.to_datetime(df["Tarih"]).dt.date
            gunluk_mail = df["Gun"].value_counts().sort_index()
            st.bar_chart(gunluk_mail, color="#3B82F6")
            
    with tab2:
        st.markdown("#### AI Destekli İşletme Raporu")
        st.write("Yapay zeka son gelen mesajları okuyup işletme için öneriler hazırlar.")
        if st.button("Analizi Başlat"):
            with st.spinner("Veriler işleniyor..."):
                ai_analiz_yap(df)
        
        if "analiz_sonucu" in st.session_state:
            st.success("Analiz Tamamlandı")
            st.info(st.session_state.analiz_sonucu)
    
    with tab3:
        st.subheader("🔍 Veri Filtreleme")
        secilenler = st.multiselect(
            "Görmek istediğiniz kategorileri seçin:",
            options=df["Kategori"].unique(),
            default=df["Kategori"].unique()
        )
        
        if secilenler:
            df_filtreli = df[df["Kategori"].isin(secilenler)]
            st.dataframe(df_filtreli, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

else:
    st.warning("Henüz veri yok veya bağlantı bekleniyor.")