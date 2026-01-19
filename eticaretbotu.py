import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime

# --- GÜVENLİ YAPILANDIRMA ---
try:
    # Gemini Anahtarı
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Google Sheets Yetkilendirme
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    
    # --- KRİTİK DEĞİŞİKLİK: URL ARTIK GİZLİ ---
    # Kodun içinde link yok! Streamlit ayarlarından çekecek.
    SHEET_URL = st.secrets["sheet_url"] 
    
except Exception as e:
    st.error(f"Sistem Hatası: Ayarlar okunamadı. Lütfen 'Secrets' ayarlarını kontrol edin. Hata: {e}")
    st.stop()

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Yönetim Paneli", layout="wide", page_icon="🛍️")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; background-color: #0F172A; color: #F8FAFC; }
    section[data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; padding: 20px; border-radius: 15px; text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; color: #3B82F6; }
    </style>
    """, unsafe_allow_html=True)

# --- FONKSİYONLAR ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and len(df.columns) >= 6:
            df.columns = ["Tarih", "Kimden", "Konu", "Mesaj", "Kategori", "AI_Cevap"]
        return df
    except: return None

def ai_analiz_yap(df):
    metin = " ".join(df["Mesaj"].astype(str).tail(15))
    prompt = f"Sen kıdemli bir iş analistisin. Mesajlar: '{metin}'. Şirket sahibi için 3 kısa stratejik öneri yaz."
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.analiz_sonucu = res.text
    except: st.error("AI gecikmesi.")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9187/9187604.png", width=70)
    st.markdown("### Yönetim Paneli")
    st.markdown("---")
    menu_secimi = st.radio("MENÜ", ["🏠 Ana Sayfa", "💰 Satış Analizi", "📦 Ürün Yönetimi", "📊 Müşteri Raporları", "⚙️ Ayarlar"])
    st.markdown("---")
    if st.button("🔄 Yenile"): st.cache_data.clear(); st.rerun()

# --- SAYFALAR ---
df = verileri_getir()

if menu_secimi == "🏠 Ana Sayfa":
    st.title("Genel Bakış")
    if df is not None and not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        toplam = len(df)
        iade = len(df[df["Kategori"] == "IADE"])
        c1.metric("Toplam Mesaj", toplam); c2.metric("İade", iade)
        c3.metric("Tahmini Ciro", "₺14,250"); c4.metric("Müşteri", "842")
        st.markdown("###")
        col1, col2 = st.columns(2)
        with col1:
            df_pie = df["Kategori"].value_counts().reset_index()
            df_pie.columns = ["Kategori", "Adet"]
            fig = px.pie(df_pie, values='Adet', names='Kategori', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with col2: st.info("📢 Günlük Özet: İadelerde düşüş var, satışlar stabil.")

elif menu_secimi == "💰 Satış Analizi":
    st.title("💸 Satış Performansı (Simülasyon)")
    sales = pd.DataFrame({"Tarih": pd.date_range("2024-01-01", periods=30), "Ciro": np.random.randint(5000, 25000, 30)})
    st.line_chart(sales.set_index("Tarih")["Ciro"], color="#34D399")

elif menu_secimi == "📦 Ürün Yönetimi":
    st.title("📦 Ürün ve Stok Yönetimi")
    try:
        urun_sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        st.dataframe(pd.DataFrame(urun_sheet.get_all_records()), use_container_width=True)
        
        with st.form("yeni_urun"):
            c1, c2 = st.columns(2)
            u_ad = c1.text_input("Ürün Adı"); u_fiyat = c1.number_input("Fiyat", min_value=0)
            u_stok = c2.number_input("Stok", min_value=0); u_desc = c2.text_input("Açıklama")
            if st.form_submit_button("Kaydet") and u_ad:
                urun_sheet.append_row([u_ad, u_stok, u_fiyat, u_desc])
                st.success("Kaydedildi!"); st.rerun()
    except: st.error("Veritabanı hatası: 'Urunler' sayfası bulunamadı.")

elif menu_secimi == "📊 Müşteri Raporları":
    st.title("Müşteri Raporları")
    if df is not None:
        st.dataframe(df, use_container_width=True)
        if st.button("AI Analiz Et"): ai_analiz_yap(df)
        if "analiz_sonucu" in st.session_state: st.info(st.session_state.analiz_sonucu)

elif menu_secimi == "⚙️ Ayarlar":
    st.title("Sistem Ayarları")
    st.warning("Bu panel sadece yönetici yetkisiyle düzenlenebilir.")