# tests/test_client_ls.py
import pytest
import httpx
from unittest.mock import MagicMock, patch, AsyncMock
from spfetch.client import SharePointClient

@pytest.mark.asyncio
async def test_ls_success():
    """
    Verifica se o método ls processa corretamente a resposta da API Graph.
    """
    # 1. Mock do Auth
    mock_auth = MagicMock()
    mock_auth.get_token = AsyncMock(return_value="fake_token")
    
    client = SharePointClient(auth=mock_auth)
    
    # 2. Mock da resposta da API Graph
    mock_response_data = {
        "value": [
            {
                "name": "Folder A",
                "folder": {},
                "size": 0,
                "id": "123",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                "webUrl": "https://..."
            },
            {
                "name": "Data.csv",
                "file": {},
                "size": 1024,
                "id": "456",
                "lastModifiedDateTime": "2024-01-02T00:00:00Z",
                "webUrl": "https://..."
            }
        ]
    }

    # 3. Patch nos métodos internos para evitar chamadas reais
    with patch.object(SharePointClient, "_get_site_id", AsyncMock(return_value="site_id_123")):
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            # Configura o retorno simulado do httpx
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response_data
            mock_get.return_value = mock_resp

            # Executa o método
            items = await client.ls("hostname", "/sites/path", "/folder")

            # 4. Asserções
            assert len(items) == 2
            assert items[0]["name"] == "Folder A"
            assert items[0]["is_folder"] is True
            assert items[1]["name"] == "Data.csv"
            assert items[1]["is_folder"] is False
            assert items[1]["size"] == 1024