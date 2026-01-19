import streamlit as st
import subprocess
import sys
import time
import json
import pandas as pd
import gspread
import smtplib
import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# --- 1. ZORLA GÜNCELLEME (BUNU KORUYORUZ) ---
# Sunucuyu en yeni AI sürümüne zorla geçirir.
try:
    import google.generativeai as genai
    import importlib.metadata
    version = importlib.metadata.version("google-generativeai")
    if version < "0.5.0":
        raise ImportError
except:
    # Kullanıcıya hissettirmeden arka planda günceller
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai"])
    import google.generativeai as genai

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Nexus Admin", layout="wide", page_icon="🌐")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0F172A; color: #F8FAFC; }
    section[data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; }
    div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; padding: 20px; border-radius: 15px; text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; color: #3B82F6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AYARLARI AL ---
try:
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    EMAIL_USER = st.secrets["email_user"]
    EMAIL_PASS = st.secrets["email_pass"]
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    SHEET_URL = st.secrets["sheet_url"]
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
except Exception as e:
    st.error(f"⚠️ Ayar Hatası: Secrets kısmını kontrol et. Hata: {e}")
    st.stop()

# --- 3. VERİ ÇEKME FONKSİYONLARI (DASHBOARD İÇİN) ---
@st.cache_data(ttl=60)
def get_data():
    try:
        try: sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except: sheet = client.open_by_url(SHEET_URL).sheet1
        data = sheet.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:])
            expected_headers = ["Date", "Sender", "Subject", "Message", "Category", "AI_Reply"]
            if len(df.columns) >= 6:
                df.columns = expected_headers + list(df.columns[6:])
            else:
                df.columns = expected_headers[:len(df.columns)]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_products():
    try:
        sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        data = sheet.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=["UrunAdi", "Stok", "Fiyat", "Aciklama"])
            # Temizlik
            df["Fiyat"] = pd.to_numeric(df["Fiyat"].astype(str).str.replace(' TL','').str.replace('$',''), errors='coerce').fillna(0)
            df["Stok"] = pd.to_numeric(df["Stok"], errors='coerce').fillna(0)
            total_value = (df["Fiyat"] * df["Stok"]).sum()
            return df, total_value
        return pd.DataFrame(), 0
    except: return pd.DataFrame(), 0

# --- 4. AKILLI AI CEVAPLAYICI ---
def get_ai_response(user_message):
    isletme_kurallari = f"""
    Bugün: {time.strftime("%Y-%m-%d")}
    KURAL 1: İade süresi 14 GÜNDÜR. (Geçtiyse reddet).
    KURAL 2: Ambalajı açılmış ürün iade alınmaz.
    KURAL 3: 500 TL altı kargo 50 TL'dir.
    """
    
    prompt = f"""
    Sen İremStore asistanısın. Kurallar: {isletme_kurallari}
    Müşteri Mesajı: "{user_message}"
    GÖREV: Kurallara göre cevap yaz.
    FORMAT: 
    KATEGORI: [IADE/KARGO/SORU]
    CEVAP: [Kısa Cevap]
    """
    
    try:
        # ÖNCE MODELLERİ LİSTELE VE SEÇ (En Garantisi)
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # İçinde 'gemini' geçen bir model bul
        model_name = next((m for m in available_models if 'gemini' in m), 'models/gemini-pro')
        
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text, model_name
        
    except Exception as e:
        return f"KATEGORI: HATA\nCEVAP: Teknik Hata: {str(e)}", "Yok"

# --- 5. MAİL GÖNDERME ---
def send_mail_reply(to_email, subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        return True
    except: return False

# --- 6. MAİL İŞLEME SÜRECİ (HATA DÜZELTİLDİ) ---
def process_emails():
    # 'with' bloğu burada başlıyor
    with st.status("Bot Çalışıyor...", expanded=True) as status:
        
        st.write("🔌 Gmail'e bağlanılıyor...")
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("is") # 'is' etiketi
        except Exception as e:
            status.update(label="Bağlantı Hatası!", state="error")
            st.error(f"Gmail Bağlantı Hatası: {e}. 'is' klasörü var mı?")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            # HATA DÜZELTİLDİ: Status update içeride kaldı
            status.update(label="Yeni mesaj yok", state="complete")
            st.toast("📭 Yeni mail yok.")
            return

        st.write(f"📢 {len(mail_ids)} adet yeni mail bulundu.")
        
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet = client.open_by_url(SHEET_URL).sheet1

        count = 0
        for i in mail_ids:
            try:
                res, msg_data = mail.fetch(i, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes): subject = subject.decode(encoding or "utf-8")
                        sender = email.utils.parseaddr(msg.get("From"))[1]
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else: body = msg.get_payload(decode=True).decode()

                        st.write(f"📩 İşleniyor: {subject}")

                        # AI CEVAPLIYOR
                        ai_full_response, used_model = get_ai_response(body)
                        st.caption(f"Model: {used_model}")

                        kategori = "GENEL"
                        cevap = ai_full_response
                        if "KATEGORI:" in ai_full_response:
                            parts = ai_full_response.split("CEVAP:")
                            if len(parts) > 1:
                                kategori = parts[0].split("KATEGORI:")[1].strip()
                                cevap = parts[1].strip()

                        # KAYDET & GÖNDER
                        sheet.append_row([time.strftime("%Y-%m-%d %H:%M"), sender, subject, body, kategori, cevap])
                        
                        if send_mail_reply(sender, f"Re: {subject}", cevap):
                            st.write(f"✅ Yanıtlandı: {kategori}")
                            count += 1
            except Exception as loop_e:
                st.error(f"Mail işleme hatası: {loop_e}")

        mail.close()
        mail.logout()
        
        # HATA DÜZELTİLDİ: Status update 'with' bloğunun hizasında
        if count > 0:
            status.update(label="İşlem Tamamlandı!", state="complete")
            st.success(f"🚀 {count} mail yanıtlandı!")
            time.sleep(2)
            st.rerun()

# --- 7. ARAYÜZ VE MENÜLER ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.caption("E-Commerce OS v2.0")
    
    # Mail Butonu (En Üstte)
    if st.button("📥 Mailleri Çek & Yanıtla", type="primary"):
        process_emails()
        
    st.markdown("---")
    menu_selection = st.radio("MENÜ", ["🏠 Dashboard", "📦 Stok Yönetimi", "📊 Mesaj Analizi", "⚙️ Ayarlar"])
    
    st.markdown("---")
    if st.button("🔄 Yenile"): 
        st.cache_data.clear()
        st.rerun()

# --- VERİLERİ HAZIRLA ---
df_msgs = get_data()
df_prods, total_stock_value = get_products()

# --- SAYFA İÇERİKLERİ ---

# 1. DASHBOARD
if menu_selection == "🏠 Dashboard":
    st.title("Yönetim Paneli")
    st.markdown(f"*{datetime.date.today().strftime('%d %B %Y')}*")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Mesaj", len(df_msgs))
    
    iade_sayisi = len(df_msgs[df_msgs["Category"] == "IADE"]) if "Category" in df_msgs.columns else 0
    c2.metric("İade Talepleri", iade_sayisi)
    
    c3.metric("Envanter Değeri", f"{total_stock_value:,.0f} TL")
    c4.metric("Ürün Çeşidi", len(df_prods))
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Talep Dağılımı")
        if not df_msgs.empty and "Category" in df_msgs.columns:
            fig = px.pie(df_msgs, names='Category', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.info("💡 Bot Durumu: **ÇALIŞIYOR** (Kütüphane Güncel)")

# 2. STOK YÖNETİMİ
elif menu_selection == "📦 Stok Yönetimi":
    st.title("📦 Ürünler & Stok")
    if not df_prods.empty:
        st.dataframe(df_prods, use_container_width=True)
    else:
        st.warning("Ürün listeniz boş.")
        
    with st.expander("➕ Yeni Ürün Ekle"):
        with st.form("add_prod"):
            c1, c2 = st.columns(2)
            isim = c1.text_input("Ürün Adı")
            fiyat = c1.number_input("Fiyat (TL)", min_value=0.0)
            stok = c2.number_input("Stok", min_value=0)
            aciklama = c2.text_input("Açıklama")
            if st.form_submit_button("Kaydet"):
                try:
                    sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
                    sheet.append_row([isim, stok, fiyat, aciklama])
                    st.success("Ürün eklendi!")
                    st.cache_data.clear()
                    st.rerun()
                except: st.error("Kayıt hatası.")

# 3. MESAJ ANALİZİ
elif menu_selection == "📊 Mesaj Analizi":
    st.title("Müşteri İletişimi")
    if not df_msgs.empty:
        st.dataframe(df_msgs, use_container_width=True)
    else:
        st.info("Henüz mesaj yok.")

# 4. AYARLAR
elif menu_selection == "⚙️ Ayarlar":
    st.title("Ayarlar")
    st.write("Sistem: **Nexus Admin v2**")
    st.write("Bağlı Hesap: " + EMAIL_USER)