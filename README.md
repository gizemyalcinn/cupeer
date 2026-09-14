# Cupeer — cupid for your career

Cupeer, CV'ni analiz edip 7 farklı iş platformundan (LinkedIn, Indeed, Upwork,
Kariyer.net, Eleman.net, Glassdoor, RemoteOK) topladığı güncel ilanları sana
en uygun olacak şekilde sıralayan, kişisel kullanım için geliştirilmiş
uçtan uca bir iş öneri sistemi.

CV'ni yükle, Cupeer sana en uygun ilanları bulsun ve dilersen ilana özel bir
ön yazıyı da senin için yazsın.

![Cupeer mascot](frontend/assets/cupeer.png)

## Özellikler

- **7 platformdan tek seferde tarama** — Apify Actor'ları üzerinden LinkedIn,
  Indeed, Upwork, Kariyer.net, Eleman.net, Glassdoor ve RemoteOK'tan ilan
  toplar.
- **Anlamsal eşleştirme** — CV metnini ve ilanları çok dilli (TR/EN) bir
  embedding modeliyle karşılaştırıp anlam bazlı sıralar; sadece anahtar
  kelime eşleşmesine bakmaz.
- **Ülkeye göre filtreleme** — her ilan, hangi ülke için tarandıysa o ülke
  koduyla etiketlenir; "Türkiye", "ABD" gibi bir filtre seçtiğinde yalnızca
  o ülkedeki ilanlar gösterilir.
- **Güncellik takibi** — süresi dolmuş ya da eski ilanlar (kaynağın kendi
  bilgisine ve ilan tarihine göre) otomatik olarak elenir.
- **AI destekli ön yazı** — seçtiğin bir ilan için CV'ne ve ilan metnine göre
  kişiselleştirilmiş bir ön yazı üretir, PDF olarak indirebilirsin.
- **Tamamen yerel çalışır** — verilerin kendi bilgisayarında kalır; harici
  bağımlılık sadece tarama (Apify) ve ön yazı üretimi (Gemini) için
  kullanılır.

## Teknoloji yığını

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI, Pydantic |
| Tarama | Apify Python SDK |
| Öneri modeli | sentence-transformers (çok dilli embedding) |
| Depolama | SQLite |
| Ön yazı üretimi | Google Gemini API |
| PDF üretimi | fpdf2 |
| Frontend | Statik HTML/CSS/JS (FastAPI `StaticFiles` üzerinden aynı origin'den servis edilir) |

## Kurulum

```bash
git clone <bu-repo>
cd cupeer
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

`.env.example` dosyasını `.env` olarak kopyala ve kendi API anahtarlarını gir:

```bash
cp .env.example .env
```

```
APIFY_API_TOKEN=...   # https://console.apify.com adresinden alınır
GEMINI_API_KEY=...    # https://aistudio.google.com adresinden alınır
```

## Çalıştırma

```bash
uvicorn src.api.main:app --reload
```

Sonra tarayıcıda `http://127.0.0.1:8000` adresini aç. Frontend, backend ile
aynı origin'den servis edildiği için ayrı bir sunucu kurmana gerek yok.

## Testler

Dış servislere (Apify, Gemini) bağlı olmayan, tamamen yerel/ücretsiz birim
testleri `tests/` klasöründe:

```bash
pytest
```

`scripts/manual/` klasöründeki dosyalar otomatik test değildir — geliştirme
sırasında tek tek platformları elle doğrulamak için yazılmış scriptlerdir ve
çalıştırıldıklarında gerçek (ücretli) API isteği atarlar. Bilerek ve
farkında olarak çalıştırılmalıdır.

## Maliyet notu

Apify ve Gemini'nin ücretsiz katmanları vardır ancak sınırlıdır. Bu proje her
ikisini de yalnızca gerektiğinde, düşük `max_items` değerleriyle çağıracak
şekilde tasarlandı; yine de kendi API anahtarınla kullanırken kullanım/kota
sayfalarını takip etmen önerilir.

## Proje yapısı

```
src/
  api/            FastAPI uçları
  scraping/       Platform bazlı scraper'lar + ülke tespiti
  preprocessing/  Ortak Job şeması, temizleme/dedupe
  model/          Embedding, öneri, güncellik, ön yazı üretimi
  db/             SQLite depolama katmanı
frontend/         Statik HTML/CSS/JS arayüz
tests/            Otomatik pytest testleri
scripts/manual/   Geliştirme sırasında kullanılan manuel debug scriptleri
```
