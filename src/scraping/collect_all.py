from concurrent.futures import ThreadPoolExecutor

from src.preprocessing.clean import clean_job, dedupe
from src.scraping.country_utils import resolve_location
from src.scraping.linkedin_scraper import scrape_linkedin_jobs
from src.scraping.indeed_scraper import scrape_indeed_jobs
from src.scraping.upwork_scraper import scrape_upwork_jobs
from src.scraping.kariyer_scraper import scrape_kariyer_jobs
from src.scraping.eleman_scraper import scrape_eleman_jobs
from src.scraping.glassdoor_scraper import scrape_glassdoor_jobs
from src.scraping.remoteok_scraper import scrape_remoteok_jobs
from src.preprocessing.schema import Job


def collect_all_jobs(keywords: str, location: str = "Turkey", max_items_per_source: int = 10) -> list[Job]:
    location = location.strip() or "Turkey"
    country, _, _ = resolve_location(location)

    tasks = [
        (scrape_linkedin_jobs, (keywords, location), {"max_items": max_items_per_source, "date_posted": "pastWeek"}),
        (scrape_indeed_jobs, (keywords, location), {"max_items": max_items_per_source, "from_days": "7"}),
        (scrape_upwork_jobs, (keywords,), {"max_items": max_items_per_source}),
        (scrape_glassdoor_jobs, (keywords, location), {"max_items": max_items_per_source, "days_old": 7}),
        (scrape_remoteok_jobs, (keywords,), {"max_items": max_items_per_source}),
    ]

    # Kariyer.net ve Eleman.net sadece Türkiye ilanı listeliyor — başka bir
    # ülke aranıyorsa bu iki platformu taramanın anlamı yok, atlıyoruz.
    if country == "tr":
        tasks.append((scrape_kariyer_jobs, (keywords, location), {"max_items": max_items_per_source, "max_age_days": 7}))
        tasks.append((scrape_eleman_jobs, (keywords,), {"max_items": max_items_per_source}))

    # Upwork ve RemoteOK global platformlar — belirli bir ülkeye bağlanmıyor,
    # bu yüzden bu ikisinin ilanlarını ülke etiketlemesinden muaf tutuyoruz.
    global_scrapers = {scrape_upwork_jobs, scrape_remoteok_jobs}

    jobs: list[Job] = []
    # Apify'ın ücretsiz planı aynı anda en fazla 5 actor çalışmasına izin veriyor.
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_fn = {executor.submit(fn, *args, **kwargs): fn for fn, args, kwargs in tasks}
        for future, fn in future_to_fn.items():
            try:
                result = future.result()
                if fn not in global_scrapers:
                    for job in result:
                        job.country = country
                jobs += result
            except Exception as e:
                print(f"Bir platform tarama sırasında hata verdi: {e}")

    jobs = [clean_job(job) for job in jobs]
    jobs = dedupe(jobs)

    return jobs
