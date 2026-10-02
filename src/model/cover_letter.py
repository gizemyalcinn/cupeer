import os
import re
import time
from typing import Literal

from google import genai
from google.genai.errors import ServerError

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


Tone = Literal["balanced", "formal", "friendly"]
Length = Literal["short", "medium", "long"]
Language = Literal["tr", "en"]

TONE_RULES = {
    "balanced": "Resmi ve profesyonel bir dil kullan ama katı/robotik olma — sıcak, kendinden emin, samimi ama saygılı bir ses tonu tut.",
    "formal": "Kurumsal ve resmi bir dil kullan: ölçülü, net, mesafeli ama kibar. Gündelik ifadelerden, ünlemlerden ve kişisel anekdotlardan kaçın.",
    "friendly": "Sıcak ve samimi ama profesyonel bir dil kullan: konuşur gibi doğal, akıcı cümleler kur; yine de saygılı kal ve karşı tarafa 'siz' diye hitap et.",
}

LENGTH_RULES = {
    "short": "100-140 kelime civarında, 2-3 kısa paragrafla çok kısa ve öz tut.",
    "medium": "180-230 kelime civarında olsun, kısa ve öz tut.",
    "long": "280-340 kelime civarında, 4-5 paragrafla daha ayrıntılı yaz; ek uzunluk için tekrar değil, daha fazla somut eşleşme kullan.",
}

LANGUAGE_RULES = {
    "tr": "CV hangi dilde olursa olsun (Türkçe veya İngilizce), ön yazıyı HER ZAMAN Türkçe yaz.",
    "en": "CV ve ilan hangi dilde olursa olsun, ön yazıyı HER ZAMAN İngilizce yaz (doğal, akıcı iş İngilizcesi).",
}

FORMAT_RULES = {
    "tr": 'Standart bir iş mektubu formatında yaz: hitapla başla ("Sayın ... Yetkilisi," gibi), 3-4 paragraf gövde, saygı ifadesiyle ve adayın adıyla bitir.',
    "en": 'Standart bir iş mektubu formatında yaz: hitapla başla ("Dear Hiring Manager," ya da şirkete uygun bir hitap), gövde paragrafları, "Sincerely," gibi bir kapanışla ve adayın adıyla bitir.',
}


def build_cover_letter_prompt(
    profile_text: str,
    job_title: str,
    company: str | None,
    job_description: str,
    tone: Tone = "balanced",
    length: Length = "medium",
    language: Language = "tr",
) -> str:
    return f"""Sen deneyimli bir kariyer danışmanısın. Aşağıdaki CV'ye ve iş ilanına dayanarak, bu pozisyona özel bir ön yazı (cover letter) yaz.

ADIM 1 — Eşleştirme analizi (çıktıya yazma, sadece kendi içinde yap):
İlan metnini dikkatle oku ve içinde geçen somut gereksinimleri çıkar (belirli teknolojiler, araçlar, metodolojiler, sorumluluklar, sektör terimleri — ilanın kendi kelimeleriyle). Sonra CV'yi tara ve bu gereksinimlerle gerçekten örtüşen 3-4 somut madde bul (bir proje, bir teknoloji, ölçülebilir bir sonuç, belirli bir sorumluluk). Genel/havada kalan eşleşmeleri değil, ilana özgü, "bu ilan olmasaydı bu cümle yazılmazdı" diyebileceğin somut eşleşmeleri seç.

ADIM 2 — Ön yazıyı yaz. Zorunlu kurallar:
- Bulduğun eşleşmelerden EN AZ İKİSİNDE, ilan metninde geçen somut bir terimi/teknolojiyi/sorumluluğu doğrudan adıyla kullan (örn. "ilanda belirtilen X konusundaki ihtiyacınıza karşılık, Y projemde tam olarak bunu yaptım" gibi bir bağ kur). Bu terimler ilanda gerçekten geçmeli, uydurma olmamalı.
- Her eşleşmeyi "bende bu var" değil, "bu sayede size şunu sağlarım" çerçevesinde, somut fayda/sonuç diliyle yaz.
- Şirketin ismini veya ilanın işaret ettiği ürün/alanı (varsa) en az bir kez doğal bir şekilde geçir — bu ön yazının başka hiçbir ilana kopyalanıp yapıştırılamayacağını hissettirmeli.
- İnsan eliyle yazılmış gibi doğal aksın; yapay zeka metinlerine özgü kalıp ifadelerden (örn. "büyük bir heyecanla", "güçlü bir zemin oluşturdu", "vizyonunu takip ediyorum", aşırı sıfat yığma) kesinlikle kaçın.
- {TONE_RULES[tone]}
- CV'de olmayan hiçbir beceri veya deneyimi uydurma.
- {LANGUAGE_RULES[language]}
- {FORMAT_RULES[language]}
- {LENGTH_RULES[length]}
- Sadece ön yazının kendisini döndür — başlık, konu satırı, açıklama veya not ekleme; doğrudan hitapla başlasın.

CV:
{profile_text}

İş İlanı:
Pozisyon: {job_title}
Şirket: {company or "Belirtilmemiş"}
Açıklama: {job_description}
"""


def generate_cover_letter(
    profile_text: str,
    job_title: str,
    company: str | None,
    job_description: str,
    tone: Tone = "balanced",
    length: Length = "medium",
    language: Language = "tr",
) -> str:
    prompt = build_cover_letter_prompt(
        profile_text, job_title, company, job_description, tone, length, language
    )

    client = _get_client()
    retries = 3
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt,
            )
            return response.text
        except ServerError:
            if attempt == retries - 1:
                raise
            time.sleep(3)
