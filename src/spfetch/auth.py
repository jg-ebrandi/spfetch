# src/spfetch/auth.py
import msal
import logging
from abc import ABC, abstractmethod
from .exceptions import AuthenticationError

# Configuração do logger para este módulo
# Logger configuration for this module
logger = logging.getLogger("spfetch")

class SharePointAuth(ABC):
    """
    Classe base abstrata para métodos de autenticação.
    Abstract base class for authentication methods.
    """
    @abstractmethod
    def get_token(self) -> str:
        """
        Retorna o Access Token (Bearer).
        Returns the Access Token (Bearer).
        """
        pass

class DeviceCodeAuth(SharePointAuth):
    """
    Autenticação interativa via Device Code (Suporta MFA).
    Interactive authentication via Device Code (Supports MFA).
    """
    def __init__(self, tenant_id: str, client_id: str, scopes: list = None):
        self.tenant_id = tenant_id
        self.client_id = client_id
        # Escopo padrão para leitura de sites
        # Default scope for reading sites
        self.scopes = scopes or ["https://graph.microsoft.com/Sites.Read.All"]
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app = msal.PublicClientApplication(self.client_id, authority=self.authority)

    def get_token(self) -> str:
        logger.info("Iniciando fluxo de autenticação via Device Code...")
        logger.info("Starting Device Code authentication flow...")
        
        flow = self.app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            logger.error("Falha ao criar o fluxo de dispositivo.")
            logger.error("Failed to create device flow.")
            raise AuthenticationError("Falha ao criar o fluxo de dispositivo. / Failed to create device flow.")

        # Usamos print aqui porque o usuário FINALMENTE precisa ver essa mensagem na tela para o MFA
        # We use print here because the user ULTIMATELY needs to see this message on the screen for MFA
        print(f"\n[AÇÃO NECESSÁRIA / ACTION REQUIRED]: {flow['message']}\n")
        
        result = self.app.acquire_token_by_device_flow(flow)
        
        if "access_token" in result:
            logger.info("Autenticação concluída com sucesso!")
            logger.info("Authentication completed successfully!")
            return result["access_token"]
            
        error_msg = result.get('error_description', 'Erro desconhecido / Unknown error')
        logger.error(f"Erro de Autenticação: {error_msg}")
        logger.error(f"Authentication Error: {error_msg}")
        raise AuthenticationError(error_msg)

class ClientSecretAuth(SharePointAuth):
    """
    Autenticação silenciosa via Client Secret (Service Principal).
    Silent authentication via Client Secret (Service Principal).
    """
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, scopes: list = None):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        # Escopo padrão para aplicações sem usuário interativo
        # Default scope for non-interactive user applications
        self.scopes = scopes or ["https://graph.microsoft.com/.default"]
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app = msal.ConfidentialClientApplication(
            self.client_id, 
            authority=self.authority,
            client_credential=self.client_secret
        )

    def get_token(self) -> str:
        # Usamos debug em vez de info para não poluir os logs de pipelines automatizados
        # We use debug instead of info to avoid polluting automated pipeline logs
        logger.debug("Obtendo token via Client Secret...")
        logger.debug("Getting token via Client Secret...")
        
        result = self.app.acquire_token_for_client(scopes=self.scopes)
        
        if "access_token" in result:
            logger.debug("Token obtido com sucesso!")
            logger.debug("Token successfully acquired!")
            return result["access_token"]
            
        error_msg = result.get('error_description', 'Erro desconhecido / Unknown error')
        logger.error(f"Erro de Autenticação (Client Secret): {error_msg}")
        logger.error(f"Authentication Error (Client Secret): {error_msg}")
        raise AuthenticationError(error_msg)