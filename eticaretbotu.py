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

# --- ÖZEL CSS (TASARIM) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        background-color: #0F172A;
        color: #F8FAFC;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #1E293B;
        border-right: 1px solid #334155;
    }
    
    div[data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        color: #94A3B8;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 700;
        color: #3B82F6;
    }

    div[data-testid="stDataFrame"] {
        background-color: #1E293B;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
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
    prompt = f"Sen kıdemli bir iş analistisin. Mesajlar: '{metin}'. Şirket sahibi için 3 kısa stratejik öneri yaz."
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.analiz_sonucu = res.text
    except:
        st.error("AI bağlantısında gecikme var.")

# --- SIDEBAR (MENÜ) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9187/9187604.png", width=70)
    st.markdown("### İremStore Panel")
    st.markdown("---")
    
    # MENÜ SEÇİMİNİ BİR DEĞİŞKENE ATIYORUZ
    menu_secimi = st.radio("MENÜ", ["🏠 Ana Sayfa", "📊 Detaylı Raporlar", "⚙️ Ayarlar"])
    
    st.markdown("---")
    st.caption("v2.5.0 Aktif")
    if st.button("🔄 Verileri Yenile", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- ANA EKRAN YÖNLENDİRMESİ ---
# Burası çok önemli! Seçilen menüye göre ekranı değiştiriyoruz.

df = verileri_getir()

# 1. SENARYO: ANA SAYFA SEÇİLİYSE
if menu_secimi == "🏠 Ana Sayfa":
    st.title("Genel Bakış")
    st.markdown(f"*{datetime.date.today().strftime('%d %B %Y')} durumu.*")
    st.markdown("---")

    if df is not None and not df.empty:
        # KPI KARTLARI
        col1, col2, col3, col4 = st.columns(4)
        toplam = len(df)
        iade = len(df[df["Kategori"] == "IADE"])
        red = len(df[df["AI_Cevap"].str.contains("dolmuştur|red|geçmiş", case=False, na=False)])
        soru = len(df[df["Kategori"] == "SORU"])
        
        col1.metric("Toplam Mesaj", toplam, "Aktif")
        col2.metric("İade Talebi", iade, f"%{(iade/toplam)*100:.0f}")
        col3.metric("Otomatik Red", red, "Bot")
        col4.metric("Sorular", soru, "Satış")

        st.markdown("###")
        
        # GRAFİKLER
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📁 Kategori Dağılımı")
            df_pie = df["Kategori"].value_counts().reset_index()
            df_pie.columns = ["Kategori", "Adet"]
            fig1 = px.pie(df_pie, values='Adet', names='Kategori', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            st.markdown("### 📅 Günlük Trafik")
            df["Gun"] = pd.to_datetime(df["Tarih"]).dt.date
            gunluk = df["Gun"].value_counts().sort_index()
            st.bar_chart(gunluk, color="#3B82F6")
    else:
        st.info("Veri bekleniyor...")

# 2. SENARYO: DETAYLI RAPORLAR SEÇİLİYSE
elif menu_secimi == "📊 Detaylı Raporlar":
    st.title("Veri Merkezi & AI Analiz")
    st.markdown("---")
    
    if df is not None and not df.empty:
        tab1, tab2 = st.tabs(["📋 Tüm Kayıtlar", "🧠 Yapay Zeka Raporu"])
        
        with tab1:
            st.markdown("### 🔍 Veri Filtreleme")
            kategoriler = st.multiselect("Kategori Seç:", df["Kategori"].unique(), default=df["Kategori"].unique())
            st.dataframe(df[df["Kategori"].isin(kategoriler)], use_container_width=True, height=600)
            
        with tab2:
            st.info("AI, son mesajları okuyup yönetici özeti çıkarır.")
            if st.button("✨ Raporu Oluştur"):
                with st.spinner("Analiz yapılıyor..."):
                    ai_analiz_yap(df)
            
            if "analiz_sonucu" in st.session_state:
                st.success("Analiz Tamamlandı")
                st.markdown(st.session_state.analiz_sonucu)

# 3. SENARYO: AYARLAR SEÇİLİYSE
elif menu_secimi == "⚙️ Ayarlar":
    st.title("Sistem Ayarları")
    st.markdown("---")
    
    st.warning("⚠️ Bu alan sadece yönetici erişimine açıktır.")
    
    st.text_input("Bot Adı", "İremStore Asistanı", disabled=True)
    st.slider("İade Kabul Süresi (Gün)", 0, 30, 14, disabled=True)
    st.toggle("Bakım Modu", False)
    
    st.caption("Not: Bu ayarlar demo amaçlıdır, şu an veritabanını etkilemez.")

else:
    st.error("Bir seçim yapılmadı.")