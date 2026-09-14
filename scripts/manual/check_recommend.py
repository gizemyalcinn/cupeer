from src.model.recommender import recommend_jobs

results = recommend_jobs("I am a Python developer with machine learning skills", top_n=5)

for job, score in results:
    print(f"{score:.3f} - {job.title}")