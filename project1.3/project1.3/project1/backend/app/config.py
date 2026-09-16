import os

# Use HuggingFace mirror in China to avoid connection resets
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/ds_teaching.db"
    upload_dir: str = "./uploads"
    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    # LLM config — DeepSeek only
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    # Local embedding model (HuggingFace sentence-transformers)
    # DeepSeek does not provide an embedding API
    local_embedding_model: str = "BAAI/bge-small-zh-v1.5"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
