import streamlit as st
import google.generativeai as genai

# ==========================================
# 1. AYARLAR & KURULUM
# ==========================================
st.set_page_config(page_title="IremStore AI Panel", page_icon="🛍️")

# Anahtarını buraya yapıştır
genai.configure(api_key='AIzaSyBoCyRxgcWuOrtUesnEsG2egEOfpq2fkXU')

# ==========================================
# 2. SOL MENÜ (PATRON PANELİ)
# ==========================================
st.sidebar.title("⚙️ Dükkan Ayarları")
st.sidebar.write("Buradaki ayarlar botun zekasını anlık değiştirir.")

magaza_adi = st.sidebar.text_input("Mağaza Adı:", value="IremStore")
iade_suresi = st.sidebar.slider("İade Süresi (Gün):", 0, 90, 14)
kargo_firmasi = st.sidebar.selectbox("Kargo Firması:", ["Aras Kargo", "Yurtiçi Kargo", "MNG", "HepsiJet"])

# Temizle Butonu
if st.sidebar.button("Sohbeti Temizle"):
    st.session_state.messages = []
    st.rerun()

# ==========================================
# 3. BOTUN BEYNİ (DİNAMİK KURAL OLUŞTURMA)
# ==========================================
# Sen soldan ayarı değiştirdikçe bu metin otomatik güncelleniyor!
system_prompt = f"""
SENİN ROLÜN: Sen '{magaza_adi}' mağazasının yapay zeka asistanısın.
KURALLAR:
1. İade süremiz {iade_suresi} gündür.
2. Kargo firmamız {kargo_firmasi}'dur.
3. Kibar, kısa ve çözüm odaklı konuş.
4. Müşteri 'Patron kim?' derse 'Benim patronum İrem Hanım' de.
"""

# Modeli çağır (Senin güçlü modelin)
model = genai.GenerativeModel(
    model_name='models/gemini-2.5-flash',
    system_instruction=system_prompt
)

# ==========================================
# 4. SOHBET EKRANI (CHAT ARAYÜZÜ)
# ==========================================
st.title(f"🛍️ {magaza_adi} - Canlı Destek")
st.caption("Müşteri Temsilcisi: Yapay Zeka (Online 🟢)")

# Geçmişi Hatırla (Session State)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Eski mesajları ekrana çiz
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# KULLANICI MESAJ YAZINCA...
if prompt := st.chat_input("Sorunuzu buraya yazın..."):
    # 1. Kullanıcı mesajını ekrana bas
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Bot cevap versin
    try:
        chat = model.start_chat(history=[]) # Basitlik için her seferinde taze sohbet gibi davranıyoruz şimdilik
        response = chat.send_message(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        
    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")