import faiss
import numpy as np

from embeddings import EmbeddingModel


class VectorStore:

    def __init__(self):

        self.model = EmbeddingModel()

        self.dimension = 1024

        self.index = faiss.IndexFlatIP(
            self.dimension,
        )

        self.documents = []

    def add_documents(
        self,
        docs,
    ):

        embeddings = self.model.encode(docs)

        embeddings = np.array(
            embeddings
        ).astype("float32")

        faiss.normalize_L2(embeddings)

        self.index.add(embeddings)

        self.documents.extend(docs)

    def search(
        self,
        query,
        top_k: int = 3,
    ):

        if len(self.documents) == 0:
            return []

        embedding = self.model.encode([query])

        embedding = np.array(
            embedding
        ).astype("float32")

        faiss.normalize_L2(embedding)

        distances, indexes = self.index.search(
            embedding,
            min(top_k, len(self.documents)),
        )

        results = []

        for idx in indexes[0]:

            if idx >= 0:
                results.append(
                    self.documents[idx]
                )

        return results
