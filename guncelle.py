import google.generativeai as genai

# Senin kodundaki API Key
GOOGLE_API_KEY = "AIzaSyB1C5JDPFbolsCZC4-UBzr0wTgSOc0ykS8"
genai.configure(api_key=GOOGLE_API_KEY)

print("--- 🔍 ERİŞİLEBİLİR MODELLER ARANIYOR ---")

try:
    # Google'a "Elimde ne var ne yok göster" diyoruz
    for m in genai.list_models():
        # Sadece metin üretebilen (generateContent) modelleri filtrele
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Bulundu: {m.name}")
            
except Exception as e:
    print(f"❌ HATA: {e}")
    print("İpucu: Eğer hata 'API Key not valid' ise anahtar yanlıştır.")
    print("İpucu: Eğer hata 'User location is not supported' ise VPN açman gerekebilir.")

print("-------------------------------------------")