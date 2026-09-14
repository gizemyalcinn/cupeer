from src.scraping.eleman_scraper import scrape_eleman_jobs

jobs = scrape_eleman_jobs("veri", max_items=10)
for job in jobs:
    print(job.title, "-", job.company, "-", job.location)