from sentence_transformers import SentenceTransformer

class EmbeddingModel:
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
    ):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        return self.model.encode(texts)