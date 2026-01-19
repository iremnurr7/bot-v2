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
import datetime # Eksik olan kütüphane eklendi
from email.header import decode_header
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# --- 1. ZORLA GÜNCELLEME ---
try:
    import google.generativeai as genai
    import importlib.metadata
    version = importlib.metadata.version("google-generativeai")
    if version < "0.5.0":
        raise ImportError
except:
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
    div[data-baseweb="textarea"] { background-color: #334155 !important; color: white !important; }
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

# --- 3. DİNAMİK KURALLAR (SESSION STATE) ---
if "bot_rules" not in st.session_state:
    st.session_state.bot_rules = """1. İade süresi 14 gündür.
2. Ambalajı açılmış ürün iade alınmaz.
3. 500 TL altı kargo 50 TL'dir."""

# --- 4. VERİ ÇEKME FONKSİYONLARI ---
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
            df["Fiyat"] = pd.to_numeric(df["Fiyat"].astype(str).str.replace(' TL','').str.replace('$',''), errors='coerce').fillna(0)
            df["Stok"] = pd.to_numeric(df["Stok"], errors='coerce').fillna(0)
            total_value = (df["Fiyat"] * df["Stok"]).sum()
            return df, total_value
        return pd.DataFrame(), 0
    except: return pd.DataFrame(), 0

# --- 5. AKILLI AI CEVAPLAYICI ---
def get_ai_response(user_message, custom_rules):
    prompt = f"""
    Sen profesyonel bir e-ticaret asistanısın.
    
    İŞLETME KURALLARI (Buna göre cevap ver):
    Bugün: {datetime.date.today().strftime("%Y-%m-%d")}
    {custom_rules}

    Müşteri Mesajı: "{user_message}"
    
    GÖREV:
    1. Kurallara sadık kalarak nazikçe cevap yaz.
    2. Formatı bozma.
    
    FORMAT: 
    KATEGORI: [IADE/KARGO/SORU]
    CEVAP: [Cevap Metni]
    """
    
    try:
        # Önce Flash, olmazsa Pro (Akıllı seçim)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
        except:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
        return response.text
    except Exception as e:
        return f"KATEGORI: HATA\nCEVAP: AI Hatası: {str(e)}"

# --- 6. MAİL GÖNDERME ---
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

# --- 7. MAİL İŞLEME SÜRECİ (CRASH FIXED) ---
def process_emails():
    # 'status' nesnesini with bloğu ile açıyoruz
    with st.status("Bot Çalışıyor...", expanded=True) as status:
        
        st.write("🔌 Gmail'e bağlanılıyor...")
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("is") 
        except Exception as e:
            status.update(label="Bağlantı Hatası!", state="error")
            st.error(f"Gmail Bağlantı Hatası: {e}. 'is' klasörü var mı?")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            # HATA DÜZELTİLDİ: status.update() artık doğru yerde
            status.update(label="Yeni mesaj yok", state="complete")
            st.toast("📭 Yeni mail yok.")
            return

        st.write(f"📢 {len(mail_ids)} adet yeni mail bulundu.")
        
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        except:
            sheet = client.open_by_url(SHEET_URL).sheet1

        count = 0
        current_rules = st.session_state.bot_rules # Ayarlardaki kuralları al

        for i in mail_ids:
            try:
                res, msg_data = mail.fetch(i, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes): subject = subject.decode(encoding or "utf-8")
                        sender = email.utils.parseaddr(msg.get("From"))[1]
                        
                        # Body decode
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else: body = msg.get_payload(decode=True).decode()

                        st.write(f"📩 İşleniyor: {subject}")

                        # AI CEVAPLIYOR (Dinamik kuralları gönderiyoruz)
                        ai_full_response = get_ai_response(body, current_rules)

                        kategori = "GENEL"
                        cevap = ai_full_response
                        if "KATEGORI:" in ai_full_response:
                            parts = ai_full_response.split("CEVAP:")
                            if len(parts) > 1:
                                kategori = parts[0].split("KATEGORI:")[1].strip()
                                cevap = parts[1].strip()

                        # KAYDET & GÖNDER
                        sheet.append_row([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), sender, subject, body, kategori, cevap])
                        
                        if send_mail_reply(sender, f"Re: {subject}", cevap):
                            st.write(f"✅ Yanıtlandı: {kategori}")
                            count += 1
            except Exception as loop_e:
                st.error(f"Mail işleme hatası: {loop_e}")

        mail.close()
        mail.logout()
        
        if count > 0:
            status.update(label="İşlem Tamamlandı!", state="complete")
            st.success(f"🚀 {count} mail yanıtlandı!")
            time.sleep(2)
            st.rerun()

# --- 8. MENÜ VE ARAYÜZ ---
with st.sidebar:
    st.title("🌐 NEXUS")
    
    # Mail Butonu
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

# 1. DASHBOARD
if menu_selection == "🏠 Dashboard":
    st.title("Yönetim Paneli")
    # HATA DÜZELTİLDİ: datetime import edildiği için burası çalışacak
    st.markdown(f"*{datetime.date.today().strftime('%d %B %Y')}*")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Mesaj", len(df_msgs))
    iade_sayisi = len(df_msgs[df_msgs["Category"] == "IADE"]) if "Category" in df_msgs.columns else 0
    c2.metric("İade Talepleri", iade_sayisi)
    c3.metric("Envanter Değeri", f"{total_stock_value:,.0f} TL")
    c4.metric("Ürün Çeşidi", len(df_prods))
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Talep Dağılımı")
        if not df_msgs.empty and "Category" in df_msgs.columns:
            fig = px.pie(df_msgs, names='Category', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.info("💡 Bot durumu aktif. Ayarlar sekmesinden kuralları değiştirebilirsiniz.")

# 2. STOK YÖNETİMİ
elif menu_selection == "📦 Stok Yönetimi":
    st.title("📦 Ürünler & Stok")
    if not df_prods.empty:
        st.dataframe(df_prods, use_container_width=True)
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
                    st.success("Eklendi!"); st.rerun()
                except: st.error("Hata.")

# 3. MESAJ ANALİZİ
elif menu_selection == "📊 Mesaj Analizi":
    st.title("Müşteri İletişimi")
    if not df_msgs.empty:
        st.dataframe(df_msgs, use_container_width=True)
    else:
        st.info("Henüz mesaj yok.")

# 4. AYARLAR (DİNAMİK KURAL EKRANI)
elif menu_selection == "⚙️ Ayarlar":
    st.title("Bot Ayarları")
    st.write("Bağlı Mail: " + EMAIL_USER)
    
    st.subheader("📜 İşletme Kuralları (Prompt)")
    st.caption("Botun müşterilere nasıl cevap vereceğini buradan değiştirebilirsiniz. Her işletme için buraya farklı kurallar yazılabilir.")
    
    # Kullanıcı buraya yazarak kuralları değiştirebilir
    new_rules = st.text_area("Kuralları Düzenle:", value=st.session_state.bot_rules, height=200)
    
    if st.button("Kuralları Kaydet"):
        st.session_state.bot_rules = new_rules
        st.success("Kurallar güncellendi! Bot artık bu kurallara göre cevap verecek.")