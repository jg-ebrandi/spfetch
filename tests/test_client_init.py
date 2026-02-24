# tests/test_client_init.py
import pytest
from unittest.mock import MagicMock, patch
from spfetch.auth import DeviceCodeAuth
from spfetch.client import SharePointClient

def test_client_initialization():
    """
    Verifica se o cliente pode ser instanciado corretamente, mockando o MSAL.
    Verifies if the client can be instantiated correctly by mocking MSAL.
    """
    # Usamos o patch para impedir que o msal.PublicClientApplication faça chamadas reais
    # We use patch to prevent msal.PublicClientApplication from making real calls
    with patch("msal.PublicClientApplication"):
        auth = DeviceCodeAuth(tenant_id="fake-tenant", client_id="fake-client")
        client = SharePointClient(auth=auth)
        
        assert client.auth == auth
        assert client.base_graph_url == "https://graph.microsoft.com/v1.0"

def test_imports():
    """
    Verifica se as exportações principais estão funcionando.
    Verifies if main exports are working.
    """
    import spfetch
    assert hasattr(spfetch, 'SharePointClient')