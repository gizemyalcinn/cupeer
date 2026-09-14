from src.scraping.indeed_scraper import scrape_indeed_jobs

jobs = scrape_indeed_jobs("data scientist", "Istanbul", max_items=5)
for job in jobs:
    print(job.title, "-", job.company, "-", job.location, "-", job.url)