from dataclasses import dataclass
import os


@dataclass
class Settings:
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    ml_grpc_port: int = int(os.getenv("ML_GRPC_PORT", "50051"))
