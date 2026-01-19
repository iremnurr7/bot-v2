import json
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime
import imaplib
import smtplib 
import email
from email.header import decode_header
from email.mime.text import MIMEText

# --- AYARLAR ---
try:
    # 1. GEMINI AI
    GOOGLE_API_KEY = st.secrets["gemini_anahtari"]
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 2. GOOGLE SHEETS
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["google_anahtari"]["dosya_icerigi"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    SHEET_URL = st.secrets["sheet_url"] 
    
    # 3. GMAIL
    EMAIL_USER = st.secrets["email_user"]
    EMAIL_PASS = st.secrets["email_pass"]
    
except Exception as e:
    st.error(f"Sistem Hatası: Ayarlar eksik. Secrets kısmını kontrol et. Hata: {e}")
    st.stop()

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

# --- FONKSİYON 1: MESAJLARI GETİR ---
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
            # Sütunları ayarla
            current_cols = len(df.columns)
            if current_cols >= 6:
                df.columns = expected_headers + list(df.columns[6:])
            else:
                df.columns = expected_headers[:current_cols]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- FONKSİYON 2: ÜRÜNLERİ GETİR (GERÇEK HESAPLAMA İÇİN) ---
@st.cache_data(ttl=60)
def get_products():
    try:
        sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
        data = sheet.get_all_values()
        if len(data) > 1:
            # Başlıkları al (Ad, Stok, Fiyat, Açıklama varsayıyoruz)
            df = pd.DataFrame(data[1:], columns=["UrunAdi", "Stok", "Fiyat", "Aciklama"])
            
            # Sayısal dönüşümler (Hata vermemesi için temizlik)
            df["Fiyat"] = pd.to_numeric(df["Fiyat"].astype(str).str.replace(' TL','').str.replace('$','').str.replace(',','.'), errors='coerce').fillna(0)
            df["Stok"] = pd.to_numeric(df["Stok"], errors='coerce').fillna(0)
            
            # Toplam Değeri Hesapla (Ciro yerine Stok Değeri)
            total_value = (df["Fiyat"] * df["Stok"]).sum()
            return df, total_value
        return pd.DataFrame(), 0
    except: return pd.DataFrame(), 0

# --- FONKSİYON 3: PRO MODEL MAİL BOTU ---
def fetch_and_reply_emails():
    status_box = st.status("İş Zekası Botu Çalışıyor...", expanded=True) 
    
    try:
        status_box.write("1. Gmail sunucusuna bağlanılıyor...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        try:
            mail.select("is") 
            status_box.write("✅ 'is' klasörüne girildi.")
        except:
            status_box.error("❌ HATA: 'is' etiketi bulunamadı.")
            return

        status, messages = mail.search(None, 'UNSEEN')
        mail_ids = messages[0].split()

        if not mail_ids:
            status_box.warning("📭 Yeni (okunmamış) mail yok.")
            status_box.update(label="İşlem Tamamlandı", state="complete")
            return

        status_box.write(f"📢 {len(mail_ids)} adet yeni mail işleniyor.")
        sheet = client.open_by_url(SHEET_URL).worksheet("Mesajlar")
        
        # En sağlam model: gemini-pro
        model = genai.GenerativeModel('gemini-pro')
        count = 0

        for i in mail_ids: 
            res, msg = mail.fetch(i, "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    msg_content = email.message_from_bytes(response[1])
                    subject, encoding = decode_header(msg_content["Subject"])[0]
                    if isinstance(subject, bytes): subject = subject.decode(encoding if encoding else "utf-8")
                    sender = msg_content.get("From")
                    sender_email = email.utils.parseaddr(sender)[1] 
                    
                    body = ""
                    if msg_content.is_multipart():
                        for part in msg_content.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg_content.get_payload(decode=True).decode()

                    # --- YAPAY ZEKA DEVREDE ---
                    status_box.write(f"🤖 AI Cevaplıyor: {subject}")
                    bugun = datetime.datetime.now().strftime("%Y-%m-%d")
                    prompt = f"""
                    Sen İremStore profesyonel destek asistanısın.
                    MÜŞTERİ MESAJI: "{body}"
                    
                    KURALLARIMIZ:
                    1. Bugünün Tarihi: {bugun}
                    2. İade Süresi: Satın alımdan itibaren 14 gündür. (Geçtiyse kesinlikle reddet).
                    3. Kargo: 500 TL altı siparişlerde kargo 50 TL'dir.
                    4. Ürün Durumu: Paketi açılmış ürün iade alınmaz.
                    
                    GÖREV: Bu kurallara sadık kalarak müşteriye kısa, kibar ve çözüm odaklı bir yanıt yaz.
                    """
                    
                    try:
                        ai_reply = model.generate_content(prompt).text
                    except Exception as ai_e:
                        status_box.error(f"AI Model Hatası: {ai_e}")
                        ai_reply = "Sistem yoğunluğu nedeniyle şu an cevap verilemiyor."

                    # Mail Gönder
                    try:
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(EMAIL_USER, EMAIL_PASS)
                        msg = MIMEText(ai_reply, 'plain', 'utf-8')
                        msg['Subject'] = f"Re: {subject}"
                        msg['From'] = EMAIL_USER
                        msg['To'] = sender_email
                        server.sendmail(EMAIL_USER, sender_email, msg.as_string())
                        server.quit()
                    except Exception as e:
                        status_box.error(f"Mail hatası: {e}")

                    # Kaydet
                    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    kategori = "IADE" if "İADE" in ai_reply.upper() or "IADE" in ai_reply.upper() else "GENEL"
                    sheet.append_row([date_now, sender, subject, body, kategori, ai_reply])
                    count += 1
        
        mail.close()
        mail.logout()
        
        if count > 0:
            status_box.update(label=f"🚀 {count} işlem başarıyla tamamlandı!", state="complete")
            st.success(f"🚀 {count} mail profesyonelce yanıtlandı!")
            st.cache_data.clear()
            st.rerun()
            
    except Exception as e:
        status_box.error(f"GENEL HATA: {e}")

# --- FONKSİYON 4: RAPORLAMA (AI) ---
def ai_report(df):
    if df.empty: return
    text_data = " ".join(df["Message"].astype(str).tail(10))
    prompt = f"Sen bir e-ticaret danışmanısın. Müşteri mesajları: '{text_data}'. İşletme sahibine 3 kritik uyarı veya öneri yaz."
    try:
        model = genai.GenerativeModel('gemini-pro')
        res = model.generate_content(prompt)
        st.info(res.text)
    except: st.error("Rapor oluşturulamadı.")

# --- MENÜ & ARAYÜZ ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.caption("E-Commerce Business OS")
    st.markdown("---")
    
    if st.button("📥 Mailleri Çek & Yanıtla", type="primary"):
        fetch_and_reply_emails()
    
    st.markdown("---")
    menu_selection = st.radio("MENÜ", ["🏠 Ana Sayfa", "📦 Ürünler & Stok", "📊 Müşteri Analizi", "⚙️ Ayarlar"])
    if st.button("🔄 Verileri Yenile"): st.cache_data.clear(); st.rerun()

# --- VERİLERİ ÇEK ---
df_msgs = get_messages()
df_prods, total_stock_value = get_products()

# --- EKRANLAR ---

# 1. ANA SAYFA (DASHBOARD)
if menu_selection == "🏠 Ana Sayfa":
    st.title("Yönetim Paneli")
    st.markdown(f"*{datetime.date.today().strftime('%d %B %Y')}*")
    
    # METRİKLER (ARTIK GERÇEK VERİ)
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Toplam Mesaj", len(df_msgs))
    
    iade_sayisi = len(df_msgs[df_msgs["Category"] == "IADE"]) if "Category" in df_msgs.columns else 0
    c2.metric("İade Talepleri", iade_sayisi)
    
    # GERÇEK HESAPLAMA BURADA:
    c3.metric("Toplam Envanter Değeri", f"{total_stock_value:,.0f} TL")
    
    toplam_urun = len(df_prods) if not df_prods.empty else 0
    c4.metric("Ürün Çeşidi", toplam_urun)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Mesaj Kategorileri")
        if not df_msgs.empty and "Category" in df_msgs.columns:
            fig = px.pie(df_msgs, names='Category', title='Talep Dağılımı', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.info("💡 **Bilgi:** 'Toplam Envanter Değeri', Ürünler sayfasındaki (Stok x Fiyat) formülüyle canlı hesaplanmaktadır.")

# 2. ÜRÜNLER
elif menu_selection == "📦 Ürünler & Stok":
    st.title("📦 Stok Yönetimi")
    if not df_prods.empty:
        st.dataframe(df_prods, use_container_width=True)
    else:
        st.warning("Ürün bulunamadı veya 'Urunler' sayfası yok.")
        
    with st.expander("➕ Yeni Ürün Ekle"):
        with st.form("add_prod"):
            c1, c2 = st.columns(2)
            isim = c1.text_input("Ürün Adı")
            fiyat = c1.number_input("Fiyat (TL)", min_value=0.0)
            stok = c2.number_input("Stok Adedi", min_value=0)
            aciklama = c2.text_input("Açıklama")
            if st.form_submit_button("Veritabanına Kaydet"):
                try:
                    sheet = client.open_by_url(SHEET_URL).worksheet("Urunler")
                    sheet.append_row([isim, stok, fiyat, aciklama])
                    st.success("Ürün eklendi!")
                    st.cache_data.clear()
                    st.rerun()
                except: st.error("Kaydedilemedi.")

# 3. MÜŞTERİ ANALİZİ
elif menu_selection == "📊 Müşteri Analizi":
    st.title("Müşteri Mesajları")
    if not df_msgs.empty:
        st.dataframe(df_msgs, use_container_width=True)
        st.markdown("### 🧠 Yapay Zeka Raporu")
        if st.button("✨ Mesajları Analiz Et"):
            with st.spinner("AI mesajları inceliyor..."):
                ai_report(df_msgs)

# 4. AYARLAR
elif menu_selection == "⚙️ Ayarlar":
    st.title("Sistem Ayarları")
    st.text_input("Bot Durumu", "AKTİF (Gemini Pro)", disabled=True)
    st.caption("Bu panel sadece yönetici erişimine açıktır.")