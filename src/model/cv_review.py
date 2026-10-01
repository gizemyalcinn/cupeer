import os
import time
from datetime import date

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from pydantic import BaseModel

_client = None


class CategoryScore(BaseModel):
    name: str
    score: int
    comment: str


class CVReview(BaseModel):
    overall_score: int
    summary: str
    categories: list[CategoryScore]
    strengths: list[str]
    improvements: list[str]


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


def review_cv(cv_text: str) -> CVReview:
    today = date.today().strftime("%d %B %Y")
    prompt = f"""Sen bir İK uzmanı ve kariyer koçusun. Aşağıdaki CV'yi değerlendir.

Bugünün tarihi: {today}. CV'deki tarihleri (iş deneyimi, eğitim, staj vb.)
bu tarihe göre değerlendir — bir tarihin "gelecekte" olduğunu ancak bugünün
tarihinden sonraysa söyle, kendi tahminine göre değil.

Not: Bu metin bir PDF dosyasından otomatik olarak çıkarılmıştır. Bu süreçte
kelimelerin ortasına yanlışlıkla boşluk girebilir (örn. "Developed" kelimesinin
"Deve loped" olarak görünmesi) veya satırlar farklı sırada birleşebilir. Böyle
teknik çıkarım kaynaklı bozulmaları gerçek bir yazım hatası veya format sorunu
olarak değerlendirme ve raporlama; sadece CV'nin kendi içeriğine (gerçekten
eksik bilgi, tutarsız tarih, zayıf ifade vb.) odaklan.

Sana sadece düz metin veriliyor — PDF'in görsel tasarımını, renklerini,
fontlarını, link/URL'lerin tıklanabilir veya aktif olup olmadığını göremiyorsun.
Bu tür göremeyeceğin şeyler hakkında ("bağlantının aktif olduğundan emin olun"
gibi) tahmine dayalı yorum yapma; sadece metinden gerçekten okuyabildiğin
şeyleri değerlendir.

Değerlendirme kriterleri:
- ATS Uyumluluğu: Anahtar kelime kullanımı, standart bölüm başlıkları, ATS tarayıcıların okuyabileceği sade bir yapı var mı.
- İçerik Etkisi: Somut başarılar, ölçülebilir sonuçlar (rakam/yüzde), eylem fiilleriyle yazılmış maddeler var mı, yoksa genel/havada ifadeler mi kullanılmış.
- Format ve Okunabilirlik: Tutarlılık, düzen, gereksiz bilgi veya eksik bölüm var mı.

Kurallar:
- CV hangi dilde olursa olsun (Türkçe veya İngilizce), değerlendirmeyi HER ZAMAN Türkçe yaz.
- overall_score ve her kategorinin score değeri 0-100 arası bir tam sayı olsun.
- summary alanına 2-3 cümlelik genel bir değerlendirme yaz.
- strengths ve improvements listelerinde her madde somut ve uygulanabilir olsun (CV'de gerçekten var olan veya eksik olan şeylere referansla, genel geçer tavsiye verme).
- Her improvements maddesi, okuyan kişinin ne yapması gerektiğini birebir anlayacağı kadar net ve somut olsun, ama emir kipi yerine öneri kipiyle yaz (örn. "ekle" değil "eklenebilir", "konumlandır" değil "konumlandırılabilir" — "X cümlesine somut bir rakam/yüzde eklenebilir", "Y bölümü Z'den önce konumlandırılabilir" gibi). "Daha belirgin hale getirilmeli", "netleştirilebilir", "zenginleştirilebilir" gibi soyut, ne yapılacağını söylemeyen ifadelerden kaçın; gereksiz/alakasız gerekçe cümleleri ekleme.
- categories listesinde tam olarak şu üç kategori olsun: "ATS Uyumluluğu", "İçerik Etkisi", "Format ve Okunabilirlik".
- Her kategorinin comment alanı, bu CV'ye özgü somut bir referans içersin (gerçekten kullanılan bir bölüm başlığı, geçen bir anahtar kelime, belirli bir staj/proje adı veya maddesi gibi). "Standart bölüm başlıkları kullanılmış", "anahtar kelimeler uygun" gibi, bu CV'yi okumadan da yazılabilecek şablon/genel geçer cümlelerden kaçın — her cümle, sadece BU CV okunduğunda yazılabilecek kadar özgül olsun.
- Objektif ve tutarlı bir İK uzmanı gibi davran: ne CV'yi iyi göstermek için yapay güçlü yönler uydur, ne de eksiksiz bir "4 strengths + 4 improvements" listesi doldurmak için zorlama, önemsiz maddeler ekle. Her liste, o CV için gerçekten geçerli olan madde sayısı kadar uzun olsun (1 ile 5 arası değişebilir); gerçekten güçlü/zayıf bir yön yoksa listeyi doldurmaya çalışma. Puanlar da buna paralel olsun: gerçekten güçlü bir CV'ye yapay bir şekilde düşük, zayıf bir CV'ye yapay bir şekilde yüksek puan verme.
- Bir eksiklik önerisi yazmadan önce CV metnini tekrar dikkatlice kontrol et: o bilgi (tarih, link, iletişim bilgisi, süre vb.) metinde zaten açıkça yazılıyorsa, "eksik" veya "netleştirilebilir" deme — bunu bir öneri olarak yazma.
- Puanlamada cömert davranma, sert ve gerçekçi bir işe alım uzmanı gibi ol. Binlerce CV gördüğünü, bu CV'yi gerçek bir iş piyasasındaki rakip adaylarla kıyasladığını düşün. 90-100 aralığı neredeyse hiç kullanılmamalı ve sadece gerçekten istisnai, sektör lideri seviyesinde bir CV'ye verilmeli. İyi ama geliştirilebilir CV'ler (ki çoğu CV böyledir) 55-75 aralığında olmalı. Belirgin eksiklikleri olan CV'ler 55'in altında olabilir. "Bu CV iyi ama X, Y, Z eksik" diyorsan, puan buna göre düşük olmalı — eksiklik listelediğin halde yüksek puan verme tutarsızlığına düşme.

CV:
{cv_text}
"""

    client = _get_client()
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CVReview,
    )

    retries = 3
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt,
                config=config,
            )
            return response.parsed
        except ServerError:
            if attempt == retries - 1:
                raise
            time.sleep(3)
