"""Configuration loaded from environment variables / .env file."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # DigitalOcean Serverless Inference
    DO_API_KEY: str = os.getenv("DO_API_KEY", "")
    DO_INFERENCE_URL: str = "https://inference.do-ai.run/v1"

    # LLM (Claude via DO Serverless Inference)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "anthropic-claude-4.5-sonnet")

    # Embeddings: local sentence-transformers (see src/llm_factory.py). The dimension
    # must match the model output (all-MiniLM-L6-v2 = 384) and scripts/init_pgvector.sql.
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    # Vector DBs
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "benchmark")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "benchmark")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "memory_bench")

    # Benchmark parameters
    NUM_RUNS: int = int(os.getenv("NUM_RUNS", "5"))
    NUM_TURNS: int = int(os.getenv("NUM_TURNS", "50"))
    SEED_TURNS: list[int] = [
        int(t) for t in os.getenv("SEED_TURNS", "1,3,7,12,18,25,30,35,40,45").split(",")
    ]
    RECALL_TURNS: list[int] = [
        int(t) for t in os.getenv("RECALL_TURNS", "15,25,35,50").split(",")
    ]

    # Output
    RESULTS_DIR: str = os.getenv("RESULTS_DIR", "results")

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


config = Config()
