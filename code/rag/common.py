
#Shared setup for the three chunking pipelines (Token / Semantic / Sentence-window)

from llama_index.core import SimpleDirectoryReader, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

CORPUS_DIR = "data/corpus"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_embed_model():
   
    return HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)


def load_documents():
    
    reader = SimpleDirectoryReader(input_dir=CORPUS_DIR)
    documents = reader.load_data()
    return documents


def configure_global_settings():
   
    Settings.embed_model = get_embed_model()



if __name__ == "__main__":
    configure_global_settings()
    docs = load_documents()
    print(f"Loaded {len(docs)} documents from {CORPUS_DIR}")
    print(f"Embedding model: {EMBED_MODEL_NAME}")
    print(f"Example document (first 200 chars):")
    print(docs[0].text[:200])
    print(f"...")
    print(f"Total corpus characters: {sum(len(d.text) for d in docs)}")