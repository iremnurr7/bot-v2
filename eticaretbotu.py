import json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- GÜVENLİ AYARLAR ---
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Hata: 'gemini_anahtari' Secrets içinde bulunamadı!")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# Sayfa Ayarı
st.set_page_config(page_title="İremStore Master Panel", page_icon="🛍️", layout="wide")

# --- ANALİZ FONKSİYONU (YENİ) ---
def ai_analiz_raporu(df):
    st.markdown("---")
    st.subheader("🤖 AI Stratejik Yönetici Özeti")
    
    # Analiz için veriyi hazırlayalım (Özellikle Mesaj ve Kategori sütunlarını birleştiriyoruz)
    # Çok fazla mesaj varsa GPT limitine takılmamak için son 15 mesajı alıyoruz
    analiz_verisi = ""
    for index, row in df.tail(15).iterrows():
        analiz_verisi += f"Kategori: {row.get('Kategori', 'Belirtilmemiş')} | Mesaj: {row.get('Mesaj', '')}\n"

    analiz_prompt = f"""
    Sen bir e-ticaret iş analisti asistanısın. Aşağıdaki son müşteri mesajlarını incele:
    
    {analiz_verisi}
    
    Lütfen şu 3 soruya profesyonel, kısa ve net cevaplar ver:
    1. En çok şikayet edilen veya sorulan 3 ana konu nedir?
    2. Müşterilerin genel memnuniyet tonu nasıl? (Pozitif, Negatif, Nötr?)
    3. İşletme sahibinin acilen aksiyon alması gereken (kargo gecikmesi, bozuk ürün vb.) bir durum var mı?
    
    Cevapları bir yöneticiye rapor sunar gibi maddeler halinde yaz.
    """
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(analiz_prompt)
        st.info(response.text)
    except Exception as e:
        st.error(f"Analiz sırasında bir hata oluştu: {e}")

# --- GOOGLE SHEETS FONKSİYONU ---
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
        st.error(f"Sistemsel Hata (Sheets): {e}") 
        return None

# --- YAN MENÜ ---
st.sidebar.title("🎛️ Kontrol Merkezi")
mod = st.sidebar.selectbox("Mod Seç:", ["📊 Canlı Panel (Gerçek)", "🧪 AI Simülatör (Test)"])

# ==========================================
# MOD 1: CANLI PANEL
# ==========================================
if mod == "📊 Canlı Panel (Gerçek)":
    st.title("📊 Gerçek Müşteri Verileri")
    st.markdown("Bu panel, maillerden gelen verileri analiz ederek **karar destek sistemi** olarak çalışır.")
    
    if st.button("🔄 Verileri Yenile"):
        st.cache_data.clear()
        st.rerun()

    df = verileri_getir()
    
    if df is not None and not df.empty:
        # Üst Metrikler
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Mesaj", len(df))
        col2.metric("Aktif Sistem", "Gemini AI", "🟢")
        col3.metric("Durum", "Veri Akışı Var")
        
        # --- ANALİZ BUTONU ---
        if st.button("🧐 AI İle Stratejik Rapor Oluştur"):
            with st.spinner("Yapay zeka mesajları okuyor ve analiz ediyor..."):
                ai_analiz_raporu(df)
        
        st.divider()
        st.subheader("📁 Tüm Kayıtlar")
        st.dataframe(df, use_container_width=True)
        
        if "Kategori" in df.columns:
            st.subheader("📊 Konu Dağılımı")
            st.bar_chart(df["Kategori"].value_counts())
    else:
        st.warning("Henüz veri bulunamadı veya bağlantı hatası var.")

# ==========================================
# MOD 2: AI SİMÜLATÖR
# ==========================================
elif mod == "🧪 AI Simülatör (Test)":
    st.title("🧪 Yapay Zeka Laboratuvarı")
    st.sidebar.header("⚙️ Bot Kuralları")
    
    firma_adi = st.sidebar.text_input("Firma Adı", "İremStore")
    iade_suresi = st.sidebar.slider("İade Süresi (Gün)", 14, 90, 30)
    kargo_ucreti = st.sidebar.number_input("Kargo Ücreti (TL)", 0, 100, 50)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Müşteri gibi bir soru sor...")

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        system_prompt = f"Sen {firma_adi} temsilcisisin. İade: {iade_suresi} gün, Kargo: {kargo_ucreti} TL. Kibar ve çözüm odaklı ol. Müşteri: {prompt}"

        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(system_prompt)
            bot_reply = response.text
            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        except Exception as e:
            st.error(f"AI Hatası: {e}")