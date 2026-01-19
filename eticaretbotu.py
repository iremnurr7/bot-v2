import streamlit as st
import pandas as pd
import gspread
import smtplib
import imaplib
import email
import datetime
import time
import json
from email.header import decode_header
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import plotly.express as px

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

# --- 1. AYARLARI AL ---
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
    st.error(f"⚠️ Ayar Hatası: Secrets dosyanızı kontrol edin. Hata: {e}")
    st.stop()

# --- 2. AKILLI AI FONKSİYONU (YEDEKLİ SİSTEM) ---
def get_ai_response(user_message):
    isletme_kurallari = f"""
    Bugünün Tarihi: {datetime.datetime.now().strftime("%Y-%m-%d")}
    KURAL 1: İade süresi satın alımdan itibaren 14 GÜNDÜR. 
    KURAL 2: Eğer müşteri 14 günü aşan bir süre belirtiyorsa, iadeyi KESİNLİKLE REDDET.
    KURAL 3: Ambalajı açılmış ürünler iade alınmaz.
    KURAL 4: 500 TL altı kargo 50 TL'dir.
    """
    
    prompt = f"""
    Sen İremStore profesyonel asistanısın. Kurallarımız:
    {isletme_kurallari}

    Müşteri Mesajı: "{user_message}"
    
    GÖREV:
    1. Kurallara göre profesyonel cevap yaz.
    2. Kategoriyi seç: IADE, KARGO, SORU, SIKAYET.
    
    Format (Sadece bu formatta cevap ver):
    KATEGORI: [Kategori]
    CEVAP: [Cevabın]
    """

    # Model Deneme Sırası: Önce Flash, olmazsa Pro
    try:
        # 1. Deneme: Hızlı Model
        model = genai.GenerativeModel('gemini-1.5-flash') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Eğer Flash hata verirse (404 vb.), Pro modeline geç
        try:
            # 2. Deneme: Klasik Model (Daha uyumlu)
            model_backup = genai.GenerativeModel('gemini-pro')
            response = model_backup.generate_content(prompt)
            return response.text
        except Exception as e2:
            return f"KATEGORI: HATA\nCEVAP: AI Servis Hatası (Tüm modeller denendi): {str(e2)}"

# --- 3. MAİL GÖNDERME ---
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
    except Exception as e:
        st.error(f"Mail Gönderme Hatası: {e}")
        return False

# --- 4. MAİL İŞLEME MOTORU ---
def process_emails():
    status_box = st.status("Bot Çalışıyor...", expanded=True)
    
    try:
        status_box.write("🔌 Gmail'e bağlanılıyor...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        try:
            mail.select("is")
            status_box.write("✅ 'is' klasörü bulundu.")
        except:
            status_box.error("❌ 'is' etiketi bulunamadı! Gmail'de 'is' adında klasör olduğundan emin ol.")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            status_box.warning("📭 Yeni (okunmamış) mail yok.")
            status_box.update(label="İşlem Bitti", state="complete")
            return

        status_box.write(f"📢 {len(mail_ids)} adet yeni mail bulundu. AI Cevaplıyor...")
        
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
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        sender = msg.get("From")
                        sender_email = email.utils.parseaddr(sender)[1]
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()

                        status_box.write(f"📩 İşleniyor: {subject}")

                        # AI ZEKASI (YEDEKLİ SİSTEM DEVREDE)
                        ai_full_response = get_ai_response(body)
                        
                        kategori = "GENEL"
                        cevap = ai_full_response
                        
                        if "KATEGORI:" in ai_full_response and "CEVAP:" in ai_full_response:
                            try:
                                parts = ai_full_response.split("CEVAP:")
                                kategori = parts[0].split("KATEGORI:")[1].strip()
                                cevap = parts[1].strip()
                            except: pass

                        # Kaydet
                        date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        sheet.append_row([date_now, sender, subject, body, kategori, cevap])
                        
                        # Gönder
                        if send_mail_reply(sender_email, f"Re: {subject}", cevap):
                            status_box.write(f"✅ Yanıtlandı: {kategori}")
                            count += 1
            except Exception as mail_e:
                status_box.error(f"Mail hatası: {mail_e}")

        mail.close()
        mail.logout()
        
        if count > 0:
            status_box.update(label=f"🚀 {count} mail yanıtlandı!", state="complete")
            st.success(f"{count} adet mail işlendi.")
            st.cache_data.clear()
            time.sleep(2)
            st.rerun()

    except Exception as e:
        status_box.error(f"Genel Hata: {e}")

# --- 5. VERİ ÇEKME FONKSİYONLARI ---
@st.cache_data(ttl=60)
def get_messages():
    try:
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet = client.open_by_url(SHEET_URL).sheet1
        data = sheet.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:])
            expected_headers = ["Date", "Sender", "Subject", "Message", "Category", "AI_Reply"]
            current_cols = len(df.columns)
            if current_cols >= 6:
                df.columns = expected_headers + list(df.columns[6:])
            else:
                df.columns = expected_headers[:current_cols]
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
            df["Fiyat"] = pd.to_numeric(df["Fiyat"].astype(str).str.replace(' TL','').str.replace('$',''), errors='coerce').fillna(0)
            df["Stok"] = pd.to_numeric(df["Stok"], errors='coerce').fillna(0)
            total_value = (df["Fiyat"] * df["Stok"]).sum()
            return df, total_value
        return pd.DataFrame(), 0
    except: return pd.DataFrame(), 0

# --- MENÜ VE ARAYÜZ (ESKİ HALİNE DÖNDÜ) ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.caption("E-Commerce OS v1.2")
    
    # Mail Botu Butonu (En üstte)
    if st.button("📥 Mailleri Çek & Yanıtla", type="primary"):
        process_emails()
        
    st.markdown("---")
    menu_selection = st.radio("MENÜ", ["🏠 Dashboard", "💰 Sales Analytics", "📦 Inventory Manager", "📊 Customer Insights", "⚙️ Settings"])
    
    st.markdown("---")
    if st.button("🔄 Verileri Yenile"): 
        st.cache_data.clear()
        st.rerun()

# --- SAYFALAR ---
df_msgs = get_messages()
df_prods, total_stock_value = get_products()

if menu_selection == "🏠 Dashboard":
    st.title("Yönetim Paneli")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Mesaj", len(df_msgs))
    iade_sayisi = len(df_msgs[df_msgs["Category"] == "IADE"]) if "Category" in df_msgs.columns else 0
    c2.metric("İade Talepleri", iade_sayisi)
    c3.metric("Envanter Değeri", f"{total_stock_value:,.0f} TL")
    c4.metric("Ürün Çeşidi", len(df_prods))
    
    st.markdown("###")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Kategori Dağılımı")
        if not df_msgs.empty and "Category" in df_msgs.columns:
            fig = px.pie(df_msgs, names='Category', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.info("💡 **Bilgi:** Sistem şu an hem 'gemini-1.5-flash' hem de 'gemini-pro' modellerini destekliyor.")

elif menu_selection == "💰 Sales Analytics":
    st.title("Satış Analitiği")
    st.warning("Bu modül geliştirme aşamasındadır.")

elif menu_selection == "📦 Inventory Manager":
    st.title("Stok Yönetimi")
    if not df_prods.empty:
        st.dataframe(df_prods, use_container_width=True)
    with st.form("add_prod"):
        c1, c2 = st.columns(2)
        isim = c1.text_input("Ürün Adı")
        fiyat = c1.number_input("Fiyat", min_value=0.0)
        stok = c2.number_input("Stok", min_value=0)
        aciklama = c2.text_input("Açıklama")
        if st.form_submit_button("Kaydet"):
            try:
                sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
                sheet.append_row([isim, stok, fiyat, aciklama])
                st.success("Eklendi!"); st.rerun()
            except: st.error("Hata.")

elif menu_selection == "📊 Customer Insights":
    st.title("Müşteri Mesajları")
    if not df_msgs.empty:
        st.dataframe(df_msgs, use_container_width=True)

elif menu_selection == "⚙️ Settings":
    st.title("Ayarlar")
    st.write("Sistem Durumu: **AKTİF**")