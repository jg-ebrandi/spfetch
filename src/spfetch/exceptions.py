# src/spfetch/exceptions.py

class SPFetchError(Exception):
    """
    Exceção base para todos os erros da spfetch.
    Base exception for all spfetch errors.
    """
    pass

class AuthenticationError(SPFetchError):
    """
    Levantado quando a autenticação com o Microsoft Entra ID (Azure AD) falha.
    Raised when authentication with Microsoft Entra ID (Azure AD) fails.
    
    Isso pode ocorrer devido a credenciais inválidas ou tempo limite do MFA expirado.
    This could be due to invalid credentials or expired MFA timeout.
    """
    pass

class DownloadError(SPFetchError):
    """
    Levantado quando um arquivo não pode ser baixado do SharePoint.
    Raised when a file cannot be downloaded from SharePoint.
    """
    pass

class DestinationError(SPFetchError):
    """
    Levantado quando há um problema ao gravar no destino alvo.
    Raised when there is an issue writing to the target destination.
    """
    pass