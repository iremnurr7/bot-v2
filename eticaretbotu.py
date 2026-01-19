import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np # Rastgele veri üretmek için
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
st.set_page_config(page_title="İremStore Admin", layout="wide", page_icon="🛍️")

# --- ÖZEL TASARIM (CSS) ---
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
    
    /* Kart Tasarımları */
    div[data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #3B82F6;
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
    prompt = f"Sen kıdemli bir iş analistisin. Müşteri mesajları: '{metin}'. Şirket sahibi için 3 kısa stratejik öneri yaz."
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(prompt)
        st.session_state.analiz_sonucu = res.text
    except:
        st.error("AI bağlantısında gecikme var.")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9187/9187604.png", width=70)
    st.markdown("### İremStore Panel")
    st.markdown("---")
    
    # GÜNCELLENMİŞ MENÜ (Ürün Yönetimi Eklendi)
    menu_secimi = st.radio("MENÜ", ["🏠 Ana Sayfa", "💰 Satış Analizi", "📦 Ürün Yönetimi", "📊 Müşteri Raporları", "⚙️ Ayarlar"])
    
    st.markdown("---")
    if st.button("🔄 Verileri Yenile"):
        st.cache_data.clear()
        st.rerun()

# --- SAYFA YÖNLENDİRMELERİ ---
df = verileri_getir()

# 1. ANA SAYFA (Dashboard)
if menu_secimi == "🏠 Ana Sayfa":
    st.title("Genel Bakış")
    st.markdown(f"*{datetime.date.today().strftime('%d %B %Y')} durumu.*")
    
    if df is not None and not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        toplam = len(df)
        iade = len(df[df["Kategori"] == "IADE"])
        
        col1.metric("Toplam Mesaj", toplam)
        col2.metric("İade Talebi", iade, f"%{(iade/toplam)*100:.0f} Oran")
        col3.metric("Günlük Satış (Tahmini)", "₺14,250", "+%12")
        col4.metric("Aktif Müşteri", "842", "+5")
        
        st.markdown("###")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📁 Kategori Dağılımı")
            df_pie = df["Kategori"].value_counts().reset_index()
            df_pie.columns = ["Kategori", "Adet"]
            fig1 = px.pie(df_pie, values='Adet', names='Kategori', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            st.info("💡 **Günün İpucu:** İade talepleri son 2 günde %5 arttı. Kargo firmasını kontrol etmelisin.")

# 2. SATIŞ ANALİZİ
elif menu_secimi == "💰 Satış Analizi":
    st.title("💸 Satış Performansı")
    st.caption("Veriler pazaryeri entegrasyonundan otomatik çekilmektedir (Simülasyon).")
    st.markdown("---")

    # SİMÜLASYON VERİSİ
    dates = pd.date_range(start="2024-01-01", periods=30)
    sales_data = pd.DataFrame({
        "Tarih": dates,
        "Ciro": np.random.randint(5000, 25000, size=30),
        "Siparis": np.random.randint(20, 100, size=30)
    })
    
    # Üst Kartlar
    k1, k2, k3 = st.columns(3)
    k1.metric("Aylık Toplam Ciro", f"₺{sales_data['Ciro'].sum():,}", "+%8.4")
    k2.metric("Toplam Sipariş", f"{sales_data['Siparis'].sum()}", "-%2.1")
    k3.metric("Ortalama Sepet Tutarı", "₺345.50", "+₺12.40")

    # Grafikler
    tab_s1, tab_s2 = st.tabs(["📊 Ciro Trendi", "🏆 En Çok Satanlar"])
    
    with tab_s1:
        st.subheader("Günlük Ciro Grafiği")
        st.line_chart(sales_data.set_index("Tarih")["Ciro"], color="#34D399")
    
    with tab_s2:
        st.subheader("Top 5 Ürün")
        urunler = {"Kulaklık": 150, "Mouse": 120, "Klavye": 90, "Laptop Standı": 60, "USB Hub": 45}
        st.bar_chart(pd.Series(urunler), color="#F472B6")

# 3. ÜRÜN YÖNETİMİ (YENİ EKLENEN KISIM)
elif menu_secimi == "📦 Ürün Yönetimi":
    st.title("📦 Ürün ve Stok Yönetimi")
    st.caption("Botun müşterilere hangi ürünleri satabileceğini buradan yönetirsiniz.")
    st.markdown("---")

    # A) MEVCUT ÜRÜNLERİ GÖSTER
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        # 'Urunler' sayfasına bağlanıyoruz
        urun_sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        urunler_df = pd.DataFrame(urun_sheet.get_all_records())
        
        st.subheader("📋 Mevcut Stok Listesi")
        if not urunler_df.empty:
            st.dataframe(urunler_df, use_container_width=True)
        else:
            st.info("Henüz ürün eklenmemiş.")
            
    except Exception as e:
        st.error(f"Veritabanı hatası (Urunler sayfası yok olabilir): {e}")

    st.markdown("---")

    # B) YENİ ÜRÜN EKLEME FORMU
    st.subheader("➕ Yeni Ürün Ekle")
    with st.form("urun_ekle_form"):
        col1, col2 = st.columns(2)
        with col1:
            u_adi = st.text_input("Ürün Adı (Örn: iPhone 13)")
            u_fiyat = st.number_input("Fiyat (TL)", min_value=0)
        with col2:
            u_stok = st.number_input("Stok Adedi", min_value=0, step=1)
            u_aciklama = st.text_input("Kısa Açıklama (Örn: 128GB, Kırmızı)")
            
        ekle_btn = st.form_submit_button("💾 Ürünü Kaydet")
        
        if ekle_btn:
            if u_adi and u_fiyat > 0:
                try:
                    urun_sheet.append_row([u_adi, u_stok, u_fiyat, u_aciklama])
                    st.success(f"✅ {u_adi} başarıyla sisteme eklendi! Bot artık bu ürünü tanıyor.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt hatası: {e}")
            else:
                st.warning("Lütfen ürün adı ve fiyatını doğru giriniz.")

# 4. MÜŞTERİ RAPORLARI
elif menu_secimi == "📊 Müşteri Raporları":
    st.title("Müşteri İletişim Raporları")
    if df is not None:
        tab1, tab2 = st.tabs(["📋 Tüm Mesajlar", "🧠 AI Strateji"])
        with tab1:
            st.dataframe(df, use_container_width=True)
        with tab2:
            if st.button("✨ Raporu Oluştur"):
                with st.spinner("AI Çalışıyor..."):
                    ai_analiz_yap(df)
            if "analiz_sonucu" in st.session_state:
                st.info(st.session_state.analiz_sonucu)

# 5. AYARLAR
elif menu_secimi == "⚙️ Ayarlar":
    st.title("Ayarlar")
    st.warning("Demo Modu")
    st.text_input("Entegrasyon Anahtarı", "TR-8822-KEY", disabled=True)