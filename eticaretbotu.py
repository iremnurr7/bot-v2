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
    st.error("Sistem Hatası: API anahtarı doğrulanamadı.")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# --- SAYFA VE TEMA AYARLARI ---
st.set_page_config(
    page_title="İremStore Yönetim Paneli",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS ile arayüzü daha kurumsal hale getirme
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div.stButton > button:first-child {
        background-color: #007bff;
        color: white;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ANALİZ FONKSİYONU ---
def ai_analiz_raporu(df):
    st.markdown("### Stratejik Analiz Raporu")
    
    analiz_verisi = ""
    for index, row in df.tail(15).iterrows():
        analiz_verisi += f"Kategori: {row.get('Kategori', '')} | Mesaj: {row.get('Mesaj', '')}\n"

    analiz_prompt = f"""
    Sen bir profesyonel iş analistisin. Aşağıdaki müşteri geri bildirimlerini inceleyerek bir yönetici özeti hazırla:
    
    {analiz_verisi}
    
    Lütfen şu başlıklar altında raporla:
    1. Operasyonel Sorunlar: En sık karşılaşılan 3 teknik veya lojistik problem.
    2. Müşteri Deneyimi Özeti: Genel memnuniyet seviyesi ve tonu.
    3. Acil Aksiyon Önerisi: İşletme sahibinin bugün yapması gereken en kritik müdahale.
    
    Resmi ve profesyonel bir dil kullan.
    """
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(analiz_prompt)
        st.info(response.text)
    except Exception as e:
        st.error(f"AI Analiz Hatası: {e}")

# --- VERİ ÇEKME FONKSİYONU ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Veri Bağlantı Hatası: {e}") 
        return None

# --- YAN MENÜ ---
st.sidebar.markdown("## Yönetim Merkezi")
mod = st.sidebar.radio("Görünüm Seçiniz:", ["Canlı Veri Analizi", "Sistem Simülatörü"])

# --- MOD 1: CANLI VERİ ANALİZİ ---
if mod == "Canlı Veri Analizi":
    st.title("Müşteri İlişkileri Karar Destek Sistemi")
    st.markdown("İşletmenizin güncel performans verileri ve müşteri etkileşimleri.")
    
    df = verileri_getir()
    
    if df is not None and not df.empty:
        # Üst Bilgi Kartları
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Etkileşim", len(df))
        m2.metric("Sistem Durumu", "Aktif / Optimize")
        m3.metric("Son Güncelleme", "Otomatik")

        st.markdown("---")
        
        # Analiz Bölümü
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("#### Raporlama Araçları")
            if st.button("AI Analizini Başlat"):
                with st.spinner("Veriler işleniyor..."):
                    ai_analiz_raporu(df)
            
            if st.button("Verileri Yenile"):
                st.cache_data.clear()
                st.rerun()

        with col_right:
            if "Kategori" in df.columns:
                st.markdown("#### Kategori Dağılımı")
                st.bar_chart(df["Kategori"].value_counts())

        st.markdown("#### Güncel Mesaj Kayıtları")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sistem şu an yeni veri girişi bekliyor.")

# --- MOD 2: SİSTEM SİMÜLATÖRÜ ---
elif mod == "Sistem Simülatörü":
    st.title("Sistem Yapılandırma ve Test")
    st.markdown("Botun çalışma kurallarını güncelleyin ve davranışlarını test edin.")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Operasyonel Kurallar")
    firma_adi = st.sidebar.text_input("Şirket İsmi", "İremStore")
    iade_suresi = st.sidebar.slider("İade Politikası (Gün)", 14, 90, 30)
    kargo_ucreti = st.sidebar.number_input("Standart Kargo Ücreti (TL)", 0, 200, 50)

    # Chat Arayüzü
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Test mesajınızı giriniz...")

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        sys_prompt = f"Şirket: {firma_adi}. İade: {iade_suresi} gün. Kargo: {kargo_ucreti} TL. Profesyonel ve çözüm odaklı temsilci olarak cevapla. Müşteri: {prompt}"

        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(sys_prompt)
            bot_reply = response.text
            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        except Exception as e:
            st.error(f"AI Yanıt Hatası: {e}")