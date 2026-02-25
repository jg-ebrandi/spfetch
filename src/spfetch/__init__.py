# src/spfetch/__init__.py
import logging

# Importa os componentes principais para expô-los no nível superior do pacote.
# Import the core components to expose them at the top level of the package.
from .client import SharePointClient
from .auth import DeviceCodeAuth, ClientSecretAuth
from .destinations import LocalDestination, S3Destination, AzureDestination
from .exceptions import SPFetchError, AuthenticationError

# ==============================================================================
# CONFIGURAÇÃO GLOBAL DE LOGS (TELEMETRIA LIMPA)
# GLOBAL LOGGING CONFIGURATION (CLEAN TELEMETRY)
# ==============================================================================

# 1. Cria o logger padrão da biblioteca / Creates the standard library logger
logger = logging.getLogger("spfetch")
logger.addHandler(logging.NullHandler()) 

# 2. Silencia bibliotecas de terceiros que são muito verbosas no nível INFO
# Silences third-party libraries that are too verbose at the INFO level
noisy_loggers = [
    "azure",                                            # Azure Core
    "azure.core.pipeline.policies.http_logging_policy", # Azure Blob Storage uploads
    "httpx",                                            # Graph API requests
    "httpcore",                                         # httpx engine
    "adlfs",                                            # Azure native data lake/blob
    "s3fs",                                             # Amazon S3
    "gcsfs",                                            # Google Cloud Storage
    "fsspec",                                           # File system engine
    "urllib3"                                           # Generic requests
]

for name in noisy_loggers:
    logging.getLogger(name).setLevel(logging.WARNING)

def enable_console_logs():
    """
    Ativa do SPfetch no terminal.
    SPfetch activation on the terminal.
    """
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')

# ==============================================================================

# A lista __all__ define exatamente o que é importado quando alguém usa: from spfetch import *
# The __all__ list defines exactly what gets imported when someone uses: from spfetch import *
__all__ = [
    "SharePointClient",
    "DeviceCodeAuth",
    "ClientSecretAuth",
    "LocalDestination",
    "S3Destination",
    "GCSDestination",
    "AzureDestination",
    "SPFetchError",
    "enable_console_logs",
    "AuthenticationError"
]