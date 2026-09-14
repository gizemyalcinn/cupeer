from src.scraping.kariyer_scraper import scrape_kariyer_jobs

jobs = scrape_kariyer_jobs("veri bilimci", max_items=10)
for job in jobs:
    print(job.title, "-", job.company, "-", job.location, "-", job.remote)