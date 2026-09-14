from src.preprocessing.schema import Job
from src.model.embeddings import embed_texts
from src.db.storage import save_new_jobs, load_all_jobs, get_existing_ids

jobs = [
    Job(id="test:1", source="test", title="Data Scientist", description="Python, ML", url="https://a.com/1"),
    Job(id="test:2", source="test", title="Chef", description="Cooking", url="https://a.com/2"),
]

vectors = embed_texts([j.title + " " + j.description for j in jobs])

inserted = save_new_jobs(jobs, vectors)
print(f"{inserted} yeni ilan eklendi")

inserted_again = save_new_jobs(jobs, vectors)
print(f"Tekrar denendiğinde: {inserted_again} yeni ilan eklendi (0 olmalı, çünkü zaten var)")

all_jobs, all_vectors = load_all_jobs()
print(f"\nVeritabanında toplam {len(all_jobs)} ilan var, vektör boyutu: {all_vectors.shape}")
for j in all_jobs:
    print("-", j.title)