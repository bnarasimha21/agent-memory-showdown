"""Configuration loaded from environment variables / .env file."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # Vector DBs
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "benchmark")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "benchmark")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "memory_bench")

    # Benchmark parameters
    NUM_RUNS: int = int(os.getenv("NUM_RUNS", "10"))
    NUM_TURNS: int = int(os.getenv("NUM_TURNS", "50"))
    SEED_TURNS: list[int] = [
        int(t) for t in os.getenv("SEED_TURNS", "3,10,25,40").split(",")
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
