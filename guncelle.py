# --- SİMÜLATÖR (CHATBOT) PARÇASI ---
# Bunu kullanacağın zaman Sidebar'a inputları, Main kısmına da bu bloğu eklemelisin.

st.title("Müşteri Deneyimi Simülatörü")
st.caption("Senaryo Modu")

# Sidebar'a eklenecekler:
# f_adi = st.sidebar.text_input("Şirket", "İremStore")
# iade = st.sidebar.slider("İade Süresi", 14, 90, 30)
# kargo = st.sidebar.number_input("Kargo Limiti", 0, 200, 50)

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

prompt = st.chat_input("Bir müşteri sorusu yazın...")

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Prompt Mühendisliği
    sys_p = f"Şirket: {f_adi}. İade Süresi: {iade} gün. Kargo Limiti: {kargo} TL. Müşteri Sorusu: {prompt}"
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        res = model.generate_content(sys_p)
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
    except Exception as e: 
        st.error(f"Hata: {e}")