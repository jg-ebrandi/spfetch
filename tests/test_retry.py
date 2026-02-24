import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from spfetch.client import SharePointClient

@pytest.mark.asyncio
async def test_retry_on_429_logic():
    """
    Testa se o decorador realmente tenta novamente quando recebe um 429.
    """
    mock_auth = MagicMock()
    mock_auth.get_token = MagicMock(return_value="token")
    client = SharePointClient(auth=mock_auth)

    # Simulação da resposta 429 (Too Many Requests)
    mock_response_429 = MagicMock(spec=httpx.Response)
    mock_response_429.status_code = 429
    mock_response_429.headers = {"Retry-After": "0.1"} # Espera curta para o teste

    # Simulação da resposta 200 (Sucesso)
    mock_response_200 = MagicMock(spec=httpx.Response)
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"id": "site_id_123"}

    with patch("httpx.AsyncClient.get") as mock_get:
        # Definimos que a primeira chamada falha e a segunda passa
        mock_get.side_effect = [
            httpx.HTTPStatusError("Throttled", request=MagicMock(), response=mock_response_429),
            mock_response_200
        ]

        async with httpx.AsyncClient() as http_client:
            site_id = await client._get_site_id(http_client, "host", "site")
            
            assert site_id == "site_id_123"
            # Prova que o httpx.get foi chamado 2 vezes (1 erro + 1 retry)
            assert mock_get.call_count == 2