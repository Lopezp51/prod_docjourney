"""
Módulo de Configurações e Limites Operacionais da Automação RPA.
Permite edição rápida das variáveis de ambiente e limites documentais.
"""

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class AutomationConfig:
    """
    Configurações centralizadas da Automação RPA.
    Altere os valores padrão aqui ou defina-os no seu arquivo .env.
    """

    # =========================================================================
    # 1. LIMITES DOCUMENTAIS (FÁCIL EDIÇÃO)
    # =========================================================================
    # Limite máximo por arquivo PDF individual (padrão: 20 MB)
    MAX_DOCUMENT_SIZE_MB: float = float(os.getenv("MAX_DOCUMENT_SIZE_MB", "20.0"))

    # Limite máximo consolidado por envelope (padrão: 200 MB)
    MAX_ENVELOPE_SIZE_MB: float = float(os.getenv("MAX_ENVELOPE_SIZE_MB", "200.0"))

    # =========================================================================
    # 2. INTEGRAÇÃO E REDE
    # =========================================================================
    # URL Base da API do Microsserviço de Backend
    MICROSERVICE_BASE_URL: str = os.getenv("MICROSERVICE_BASE_URL", "http://localhost:8000")

    # OpenAPI v2 (Sicredi / Certisign)
    OPENAPI_BASE_URL: str = os.getenv("OPENAPI_BASE_URL", "https://api-mock.sicredi.local/assinatura-open-api")
    OPENAPI_CLIENT_ID: str = os.getenv("OPENAPI_CLIENT_ID", "mock_client_id")
    OPENAPI_ACCESS_TOKEN: str = os.getenv("OPENAPI_ACCESS_TOKEN", "mock_access_token")

    # =========================================================================
    # 3. LOGGING E OBSERVABILIDADE (LOGURU)
    # =========================================================================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")



    @property
    def max_document_size_bytes(self) -> int:
        """Retorna o limite por arquivo convertido em bytes."""
        return int(self.MAX_DOCUMENT_SIZE_MB * 1024 * 1024)

    @property
    def max_envelope_size_bytes(self) -> int:
        """Retorna o limite por envelope convertido em bytes."""
        return int(self.MAX_ENVELOPE_SIZE_MB * 1024 * 1024)


# Instância global reutilizável
config = AutomationConfig()
