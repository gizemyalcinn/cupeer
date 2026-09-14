import os
import re

from google import genai

_client = None


def guess_file_name(profile_text: str) -> str:
    first_line = profile_text.strip().split("\n")[0].strip()
    cleaned = re.sub(r"[^\w\s]", "", first_line, flags=re.UNICODE).strip()
    if not cleaned or len(cleaned) > 60:
        return "on_yazi"
    return cleaned.replace(" ", "_") + "_coverletter"


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate_cover_letter(
    profile_text: str, job_title: str, company: str | None, job_description: str
) -> str:
    prompt = f"""Sen deneyimli bir kariyer danışmanısın. Aşağıdaki CV'ye ve iş ilanına dayanarak, bu pozisyona özel bir ön yazı (cover letter) yaz.

ADIM 1 — Eşleştirme analizi (çıktıya yazma, sadece kendi içinde yap):
İlan metnini dikkatle oku ve içinde geçen somut gereksinimleri çıkar (belirli teknolojiler, araçlar, metodolojiler, sorumluluklar, sektör terimleri — ilanın kendi kelimeleriyle). Sonra CV'yi tara ve bu gereksinimlerle gerçekten örtüşen 3-4 somut madde bul (bir proje, bir teknoloji, ölçülebilir bir sonuç, belirli bir sorumluluk). Genel/havada kalan eşleşmeleri değil, ilana özgü, "bu ilan olmasaydı bu cümle yazılmazdı" diyebileceğin somut eşleşmeleri seç.

ADIM 2 — Ön yazıyı yaz. Zorunlu kurallar:
- Bulduğun eşleşmelerden EN AZ İKİSİNDE, ilan metninde geçen somut bir terimi/teknolojiyi/sorumluluğu doğrudan adıyla kullan (örn. "ilanda belirtilen X konusundaki ihtiyacınıza karşılık, Y projemde tam olarak bunu yaptım" gibi bir bağ kur). Bu terimler ilanda gerçekten geçmeli, uydurma olmamalı.
- Her eşleşmeyi "bende bu var" değil, "bu sayede size şunu sağlarım" çerçevesinde, somut fayda/sonuç diliyle yaz.
- Şirketin ismini veya ilanın işaret ettiği ürün/alanı (varsa) en az bir kez doğal bir şekilde geçir — bu ön yazının başka hiçbir ilana kopyalanıp yapıştırılamayacağını hissettirmeli.
- İnsan eliyle yazılmış gibi doğal aksın; yapay zeka metinlerine özgü kalıp ifadelerden (örn. "büyük bir heyecanla", "güçlü bir zemin oluşturdu", "vizyonunu takip ediyorum", aşırı sıfat yığma) kesinlikle kaçın.
- Resmi ve profesyonel bir dil kullan ama katı/robotik olma — sıcak, kendinden emin, samimi ama saygılı bir ses tonu tut.
- CV'de olmayan hiçbir beceri veya deneyimi uydurma.
- CV hangi dildeyse (Türkçe veya İngilizce) ön yazıyı da o dilde yaz.
- Standart bir iş mektubu formatında yaz: hitapla başla ("Sayın ... Yetkilisi," gibi), 3-4 paragraf gövde, saygı ifadesiyle ve adayın adıyla bitir.
- 250-350 kelime civarında olsun.
- Sadece ön yazının kendisini döndür — başlık, konu satırı, açıklama veya not ekleme; doğrudan hitapla başlasın.

CV:
{profile_text}

İş İlanı:
Pozisyon: {job_title}
Şirket: {company or "Belirtilmemiş"}
Açıklama: {job_description}
"""

    client = _get_client()
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    return response.text
