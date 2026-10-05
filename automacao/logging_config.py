"""
Módulo de Configuração de Logs Estruturados com Loguru para a Automação RPA.
Configura consoles coloridos, arquivos com rotação diária e por tamanho, diagnóstico de exceções
e interceptação de logs da biblioteca padrão do Python (HTTPX, etc.).
"""

import sys
import logging
from pathlib import Path
from loguru import logger
from automacao.config import config


class InterceptHandler(logging.Handler):
    """
    Handler para interceptar mensagens do módulo padrão logging do Python
    e redirecioná-las para os sinks configurados do Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(
    log_level: str = None,
    log_dir: str = None,
    service_name: str = "DocJourneyAutomation"
) -> None:
    """
    Inicializa e padroniza o sistema de logging com Loguru para o robô RPA.
    Cria diretório de logs e configura saídas de console e arquivos rotativos.
    """
    level = log_level or getattr(config, "LOG_LEVEL", "INFO")
    logs_directory = Path(log_dir or getattr(config, "LOG_DIR", "logs"))
    logs_directory.mkdir(parents=True, exist_ok=True)

    # Remove handlers padrão do Loguru para evitar duplicidade
    logger.remove()

    # 1. Console / Terminal (Colorido e Estruturado)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[component]}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level=level,
        format=console_format,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 2. Arquivo Geral com Rotação Diária e Limite de 20 MB (logs/automacao_YYYY-MM-DD.log)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{extra[component]} | "
        "{name}:{function}:{line} - "
        "{message}"
    )

    log_file_path = logs_directory / "automacao_{time:YYYY-MM-DD}.log"
    logger.add(
        str(log_file_path),
        level=level,
        format=file_format,
        rotation="20 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # 3. Arquivo Exclusivo para Erros Críticos (logs/automacao_errors.log)
    error_file_path = logs_directory / "automacao_errors.log"
    logger.add(
        str(error_file_path),
        level="ERROR",
        format=file_format,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # Vincula o componente padrão no contexto
    logger.configure(extra={"component": service_name})

    # Intercepta loggers do Python padrão (HTTPX, etc.)
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.getLevelName(level))

    for logger_name in ("httpx", "httpcore", "urllib3"):
        mod_logger = logging.getLogger(logger_name)
        mod_logger.handlers = [InterceptHandler()]
        mod_logger.propagate = False


# Inicialização automática no momento da importação
setup_logging()

__all__ = ["logger", "setup_logging"]
