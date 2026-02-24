# src/spfetch/destinations.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseDestination(ABC):
    """
    Classe base abstrata para todos os destinos de armazenamento.
    Abstract base class for all storage destinations.
    """
    
    @abstractmethod
    def get_storage_options(self) -> Dict[str, Any]:
        """
        Retorna um dicionário de configurações para o fsspec.
        Returns a configuration dictionary for fsspec.
        """
        pass

class LocalDestination(BaseDestination):
    """
    Configuração para destino de Sistema de Arquivos Local.
    Configuration for Local File System destination.
    """
    def get_storage_options(self) -> Dict[str, Any]:
        # Nenhuma credencial necessária para o disco local
        # No credentials required for local disk
        return {}

class AzureDestination(BaseDestination):
    """
    Configuração para Azure Blob Storage e Azure Data Lake Gen 2 (abfs).
    Configuration for Azure Blob Storage and Azure Data Lake Gen 2 (abfs).
    """
    def __init__(self, account_name: str, account_key: str = None, sas_token: str = None):
        self.account_name = account_name
        self.account_key = account_key
        self.sas_token = sas_token

    def get_storage_options(self) -> Dict[str, Any]:
        options = {"account_name": self.account_name}
        
        # Injeta a chave ou o token dependendo do que o usuário informou
        # Injects the key or token depending on what the user provided
        if self.account_key:
            options["account_key"] = self.account_key
        elif self.sas_token:
            options["sas_token"] = self.sas_token
            
        return options

class S3Destination(BaseDestination):
    """
    Configuração para armazenamento Amazon S3.
    Configuration for Amazon S3 storage.
    """
    def __init__(self, key: str, secret: str, token: str = None):
        self.key = key
        self.secret = secret
        self.token = token

    def get_storage_options(self) -> Dict[str, Any]:
        options = {"key": self.key, "secret": self.secret}
        
        # O token de sessão (session token) da AWS é opcional
        # The AWS session token is optional
        if self.token:
            options["token"] = self.token
            
        return options