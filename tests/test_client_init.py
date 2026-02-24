# tests/test_client_init.py
import pytest
from spfetch.auth import DeviceCodeAuth
from spfetch.client import SharePointClient

def test_client_initialization():
    """
    Verifica se o cliente pode ser instanciado corretamente com um objeto de autenticação.
    Verifies if the client can be instantiated correctly with an auth object.
    """
    auth = DeviceCodeAuth(tenant_id="fake", client_id="fake")
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