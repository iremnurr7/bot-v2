import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime

# --- GÜVENLİ YAPILANDIRMA ---
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Sistem Hatası: Yetkilendirme başarısız.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="İremStore Admin", layout="wide", page_icon="📊")

# --- ÖZEL CSS (TASARIM SİHRİ BURADA) ---
st.markdown("""
    <style>
    /* Genel Yazı Tipi ve Arkaplan */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        background-color: #0F172A; /* Koyu Lacivert Zemin */
        color: #F8FAFC;
    }
    
    /* Sidebar Tasarımı */
    section[data-testid="stSidebar"] {
        background-color: #1E293B;
        border-right: 1px solid #334155;
    }
    
    /* KPI Kartları (Kutular) */
    div[data-testid="stMetric"] {
        background-color: #1E293B; /* Kutu Rengi */
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 15px; /* Yuvarlak Köşeler */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    /* Metrik Yazılarını Büyütme */
    div[data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        color: #94A3B8;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 700;
        color: #3B82F6; /* Mavi Sayılar */
    }

    /* Tablo Tasarımı */
    div[data-testid="stDataFrame"] {
        background-color: #1E293B;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #334155;
    }

    /* Sekme (Tabs) Yazılarını Büyütme */
    .stTabs [data-baseweb="tab"] {
        font-size: 1.2rem !important;
        font-weight: 500;
        padding: 10px 20px;
    }
    
    /* Başlıkları Büyütme */
    h1 { font-size: 3rem !important; font-weight: 800 !important; background: -webkit-linear-gradient(#eee, #999); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.5rem !important; color: #60A5FA !important; }
    
    </style>
    """, unsafe_allow_html=True)

# --- VERİ ÇEKME ---
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

# --- AI ANALİZ ---
def ai_analiz_yap(df):
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"Sen kıdemli bir iş analistisin. Bu müşteri mesajlarını incele: '{metin}'. Şirket sahibi için 3 tane çok kısa, net ve stratejik madde yaz (Örn: İade oranını düşürmek için X yap)."
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.analiz_sonucu = res.text
    except:
        st.error("AI bağlantısında gecikme var.")

# --- SIDEBAR (MENÜ) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9187/9187604.png", width=70) # Örnek Logo
    st.markdown("### İremStore Panel")
    st.markdown("---")
    
    menu = st.radio("MENÜ", ["🏠 Ana Sayfa", "📊 Detaylı Raporlar", "⚙️ Ayarlar (Demo)"])
    
    st.markdown("---")
    st.caption("🟢 Sistem Online")
    st.caption("v2.4.0 Stable")
    
    if st.button("🔄 Verileri Yenile", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- ANA EKRAN ---

# 1. HEADER (Üst Kısım)
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("Yönetim Paneli")
    st.markdown(f"*{datetime.date.today().strftime('%d %B %Y')} itibarıyla işletme durumu.*")
with col_head2:
    # Sağ üstte profil varmış gibi gösterelim
    st.success("👤 Yönetici: İrem K.")

st.markdown("---")

df = verileri_getir()

if df is not None and not df.empty:

    # 2. KPI KARTLARI (BÜYÜK SAYILAR)
    col1, col2, col3, col4 = st.columns(4)
    
    toplam = len(df)
    iade = len(df[df["Kategori"] == "IADE"])
    red = len(df[df["AI_Cevap"].str.contains("dolmuştur|red|geçmiş", case=False, na=False)])
    soru = len(df[df["Kategori"] == "SORU"])
    
    col1.metric("Toplam Mesaj", toplam, "Aktif")
    col2.metric("İade Talebi", iade, f"%{(iade/toplam)*100:.0f} Oran")
    col3.metric("Otomatik Red", red, "Bot Engelledi")
    col4.metric("Genel Sorular", soru, "Potansiyel Satış")

    st.markdown("###") # Biraz boşluk

    # 3. İÇERİK ALANI
    tab1, tab2, tab3 = st.tabs(["📈 GÖRSEL ANALİZ", "🧠 YAPAY ZEKA RAPORU", "📋 VERİ KAYITLARI"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📁 Talep Dağılımı")
            df_pie = df["Kategori"].value_counts().reset_index()
            df_pie.columns = ["Kategori", "Adet"]
            fig1 = px.pie(df_pie, values='Adet', names='Kategori', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig1, use_container_width=True)
            
        with c2:
            st.markdown("### 📅 Günlük Yoğunluk")
            df["Gun"] = pd.to_datetime(df["Tarih"]).dt.date
            gunluk = df["Gun"].value_counts().sort_index()
            st.bar_chart(gunluk, color="#3B82F6")

    with tab2:
        col_ai1, col_ai2 = st.columns([1, 2])
        with col_ai1:
            st.info("Bu modül, son gelen mesajları okuyarak işletme sahibine stratejik öneriler sunar.")
            if st.button("✨ Raporu Oluştur"):
                with st.spinner("Yapay zeka verileri analiz ediyor..."):
                    ai_analiz_yap(df)
        with col_ai2:
            if "analiz_sonucu" in st.session_state:
                st.success("Analiz Tamamlandı")
                st.markdown(f"### 💡 AI Önerileri:\n{st.session_state.analiz_sonucu}")
            else:
                st.markdown("*Analiz sonucu burada görünecek...*")

    with tab3:
        st.markdown("### 🔍 Veri Filtreleme Merkezi")
        filtre = st.multiselect("Kategori Seçiniz:", options=df["Kategori"].unique(), default=df["Kategori"].unique())
        st.dataframe(df[df["Kategori"].isin(filtre)], use_container_width=True, height=500)

else:
    st.warning("Veri tabanına bağlanılıyor veya henüz veri yok...")