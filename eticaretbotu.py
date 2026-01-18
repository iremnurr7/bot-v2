import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- AYARLAR (Buraları Doldur) ---
GOOGLE_API_KEY = "AIzaSyB1C5JDPFbolsCZC4-UBzr0wTgSOc0ykS8"  # mailbot.py'deki şifren
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kCGPLzlkI--gYtSFXu1fYlgnGLQr127J90xeyY4Xzgg/edit?usp=sharing"      # mailbot.py'deki link

# Yapay Zeka Kurulumu
genai.configure(api_key=GOOGLE_API_KEY)

# Sayfa Ayarı
st.set_page_config(page_title="İremStore Master Panel", page_icon="🛍️", layout="wide")

# --- GOOGLE SHEETS FONKSİYONU ---
@st.cache_data(ttl=60)
def verileri_getir():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('google-key.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
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
        st.warning("Veri çekilemedi. Linki ve JSON dosyasını kontrol et.")

# ==========================================
# MOD 2: AI SİMÜLATÖR (Senin İstediğin Yer)
# ==========================================
elif mod == "🧪 AI Simülatör (Test)":
    st.title("🧪 Yapay Zeka Laboratuvarı")
    st.markdown("Burada botu müşteriye açmadan önce **test edebilirsin.** Kuralları soldan değiştir!")
    
    # --- AYARLAR (SOL MENÜ) ---
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Bot Kuralları")
    
    firma_adi = st.sidebar.text_input("Firma Adı", "İremStore")
    iade_suresi = st.sidebar.slider("İade Süresi (Gün)", 14, 90, 30) # 14 ile 90 arası, varsayılan 30
    kargo_ucreti = st.sidebar.number_input("Kargo Ücreti (TL)", 0, 100, 50)
    
    st.sidebar.info(f"📝 Şu anki kural: İade {iade_suresi} gün, Kargo {kargo_ucreti} TL.")

    # --- CHAT EKRANI (ChatGPT Tarzı) ---
    
    # Geçmişi hafızada tut (Session State)
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Eski mesajları ekrana çiz
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Kullanıcıdan soru al
    prompt = st.chat_input("Müşteri gibi bir soru sor... (Örn: İade süresi kaç gün?)")

    if prompt:
        # 1. Kullanıcı mesajını ekrana bas
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. YAPAY ZEKA SİSTEM PROMPTU (Kuralları buraya gömüyoruz)
        system_prompt = f"""
        Sen {firma_adi} adında bir markanın müşteri temsilcisisin.
        Kurallarımız şunlar:
        - İade süresi: {iade_suresi} gün.
        - Kargo ücreti: {kargo_ucreti} TL.
        - Müşteriye her zaman çok kibar ve çözüm odaklı davran.
        
        Müşteri sorusu: {prompt}
        """

        # 3. Gemini'ye sor
        try:
            # Bilgisayarının listesinde çıkan isim tam olarak bu:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(system_prompt)
            bot_reply = response.text
            
            # 4. Cevabı ekrana bas
            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            
        except Exception as e:
            st.error(f"Hata oluştu: {e}")