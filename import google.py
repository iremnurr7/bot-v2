import google.generativeai as genai

# BURAYA API KEY'İNİ YAPIŞTIR
GOOGLE_API_KEY = "AIzaSyBoCyRxgcWuOrtUesnEsG2egEOfpq2fkXU"

genai.configure(api_key=GOOGLE_API_KEY)

print("🔍 Bilgisayarın gördüğü modeller taranıyor...")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ BULUNDU: {m.name}")
except Exception as e:
    print(f"❌ HATA: {e}")