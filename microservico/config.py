import os
from dataclasses import dataclass

# Tenta carregar variáveis de ambiente do arquivo .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass
class Config:
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "docjourney_db")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "senha123")
    
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    NOTIFIER_WEBHOOK_URL: str = os.getenv("NOTIFIER_WEBHOOK_URL", "https://api-mock.sicredi.local/webhook/status")
    
    # Se True, o FastAPI sobe o consumidor do RabbitMQ em uma thread paralela automaticamente
    ENABLE_EMBEDDED_WORKER: bool = os.getenv("ENABLE_EMBEDDED_WORKER", "true").lower() in ("true", "1", "yes")

config = Config()
