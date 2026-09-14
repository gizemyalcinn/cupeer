from src.scraping.linkedin_scraper import scrape_linkedin_jobs

jobs = scrape_linkedin_jobs("data scientist", "Istanbul", max_items=5)
for job in jobs:
    print(job.title, "-", job.company, "-", job.url)