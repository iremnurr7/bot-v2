import json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- GÜVENLİ AYARLAR (Secrets'tan Okunur) ---
# Artık anahtarları buraya yazmıyoruz, Streamlit Secrets panelinden alıyoruz.
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Hata: 'gemini_anahtari' Secrets içinde bulunamadı!")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# Sayfa Ayarı
st.set_page_config(page_title="İremStore Master Panel", page_icon="🛍️", layout="wide")

# --- GOOGLE SHEETS FONKSİYONU ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Secrets içindeki JSON anahtarını sözlüğe çeviriyoruz
        key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Sistemsel Hata (Sheets): {e}") 
        return None

# --- YAN MENÜ (MOD SEÇİMİ) ---
st.sidebar.title("🎛️ Kontrol Merkezi")
mod = st.sidebar.selectbox("Mod Seç:", ["📊 Canlı Panel (Gerçek)", "🧪 AI Simülatör (Test)"])

# ==========================================
# MOD 1: CANLI PANEL (Google Sheets Verisi)
# ==========================================
if mod == "📊 Canlı Panel (Gerçek)":
    st.title("📊 Gerçek Müşteri Verileri")
    st.markdown("Burada mail botunun Google Sheets'e kaydettiği **gerçek** veriler görünür.")
    st.divider()

    if st.button("🔄 Verileri Yenile"):
        st.cache_data.clear()
        st.rerun()

    df = verileri_getir()
    
    if df is not None and not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Mesaj", len(df))
        col2.metric("Son Mesaj", df.iloc[-1]["Gonderen"] if "Gonderen" in df.columns else "-")
        col3.metric("Sistem", "Aktif", "🟢")
        
        st.dataframe(df, use_container_width=True)
        
        if "Kategori" in df.columns:
            st.subheader("Kategori Analizi")
            st.bar_chart(df["Kategori"].value_counts())
    else:
        st.warning("Veri şu an çekilemiyor. Secrets ve Paylaşım ayarlarını kontrol et.")

# ==========================================
# MOD 2: AI SİMÜLATÖR (Test Alanı)
# ==========================================
elif mod == "🧪 AI Simülatör (Test)":
    st.title("🧪 Yapay Zeka Laboratuvarı")
    st.markdown("Bot kurallarını soldan değiştirip anında test edebilirsin.")
    
    st.sidebar.markdown("---")
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

        system_prompt = f"""
        Sen {firma_adi} adında bir markanın müşteri temsilcisisin.
        İade: {iade_suresi} gün, Kargo: {kargo_ucreti} TL. Kibar ol.
        Müşteri: {prompt}
        """

        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(system_prompt)
            bot_reply = response.text
            
            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            
        except Exception as e:
            st.error(f"AI Hatası: {e}")