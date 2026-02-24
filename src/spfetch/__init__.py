# src/spfetch/__init__.py

# Importa os componentes principais para expô-los no nível superior do pacote.
# Import the core components to expose them at the top level of the package.
from .client import SharePointClient
from .auth import DeviceCodeAuth, ClientSecretAuth
from .destinations import LocalDestination, S3Destination, AzureDestination
from .exceptions import SPFetchError, AuthenticationError

# A lista __all__ define exatamente o que é importado quando alguém usa: from spfetch import *
# The __all__ list defines exactly what gets imported when someone uses: from spfetch import *
__all__ = [
    "SharePointClient",
    "DeviceCodeAuth",
    "ClientSecretAuth",
    "LocalDestination",
    "S3Destination",
    "AzureDestination",
    "SPFetchError",
    "AuthenticationError"
]