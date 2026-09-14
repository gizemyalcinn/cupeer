from src.scraping.upwork_scraper import scrape_upwork_jobs

jobs = scrape_upwork_jobs("data scientist", max_items=10)
for job in jobs:
    print(job.title, "-", job.company, "-", job.salary)