from src.model.embeddings import embed_texts
import numpy as np

texts = [
    "Senior Python developer with machine learning experience",
    "Experienced data scientist skilled in Python and ML",
    "Looking for a chef with 5 years restaurant experience",
]

vectors = embed_texts(texts)
print("Vektör boyutu:", vectors.shape)

sim_1_2 = np.dot(vectors[0], vectors[1])
sim_1_3 = np.dot(vectors[0], vectors[2])
print(f"Python geliştirici <-> Veri bilimci benzerliği: {sim_1_2:.3f}")
print(f"Python geliştirici <-> Aşçı benzerliği: {sim_1_3:.3f}")