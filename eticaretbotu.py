import json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- AYARLAR ---
GOOGLE_API_KEY = "AIzaSyB1C5JDPFbolsCZC4-UBzr0wTgSOc0ykS8"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"

# Yapay Zeka Kurulumu
genai.configure(api_key=GOOGLE_API_KEY)

# Sayfa Ayarı
st.set_page_config(page_title="İremStore Master Panel", page_icon="🛍️", layout="wide")

# --- GOOGLE SHEETS FONKSİYONU ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # --- YENİ SİSTEM: KASADAN ANAHTARI OKU ---
        # Streamlit Secrets'a yapıştırdığın json içeriğini çeker
        key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        # ----------------------------------------
        
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        # Hatayı merak edersen buraya st.error(e) yazabilirsin
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
        # Metrikler
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Mesaj", len(df))
        col2.metric("Son Mesaj", df.iloc[-1]["Gonderen"] if "Gonderen" in df.columns else "-")
        col3.metric("Sistem", "Aktif", "🟢")
        
        # Tablo
        st.dataframe(df, use_container_width=True)
        
        # Grafik
        if "Kategori" in df.columns:
            st.subheader("Kategori Analizi")
            st.bar_chart(df["Kategori"].value_counts())
    else:
        st.warning("Veri çekilemedi. Şunları kontrol et: 1. Secrets'ı kaydettin mi? 2. Koddaki 'google_anahtari' ismi doğru mu?")

# ==========================================
# MOD 2: AI SİMÜLATÖR (Test Alanı)
# ==========================================
elif mod == "🧪 AI Simülatör (Test)":
    st.title("🧪 Yapay Zeka Laboratuvarı")
    st.markdown("Burada botu müşteriye açmadan önce **test edebilirsin.**")
    
    # --- AYARLAR (SOL MENÜ) ---
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Bot Kuralları")
    
    firma_adi = st.sidebar.text_input("Firma Adı", "İremStore")
    iade_suresi = st.sidebar.slider("İade Süresi (Gün)", 14, 90, 30)
    kargo_ucreti = st.sidebar.number_input("Kargo Ücreti (TL)", 0, 100, 50)
    
    st.sidebar.info(f"📝 Kural: İade {iade_suresi} gün, Kargo {kargo_ucreti} TL.")

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
        Kurallar: İade süresi {iade_suresi} gün, kargo ücreti {kargo_ucreti} TL.
        Çok kibar ve çözüm odaklı davran.
        Müşteri sorusu: {prompt}
        """

        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(system_prompt)
            bot_reply = response.text
            
            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            
        except Exception as e:
            st.error(f"Hata oluştu: {e}")