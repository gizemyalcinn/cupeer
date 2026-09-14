from src.scraping.collect_all import collect_all_jobs

jobs = collect_all_jobs("data scientist", "Istanbul", max_items_per_source=3)
print(f"Toplam {len(jobs)} ilan toplandı\n")
for job in jobs:
    print(f"[{job.source}] {job.title} - {job.company}")