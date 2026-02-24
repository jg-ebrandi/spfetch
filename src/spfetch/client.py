# src/spfetch/client.py
import httpx
import fsspec
import logging
from typing import Any, Optional
from urllib.parse import quote
from .auth import SharePointAuth

# Configuração padrão do logger para a biblioteca spfetch
# Standard logger configuration for the spfetch library
logger = logging.getLogger("spfetch")

# Adiciona um NullHandler para evitar avisos se o usuário final não configurar o logging
# Adds a NullHandler to prevent warnings if the end user does not configure logging
logger.addHandler(logging.NullHandler())

class SharePointClient:
    """
    Cliente principal para interagir com o SharePoint via Microsoft Graph API.
    Main client to interact with SharePoint via Microsoft Graph API.
    """
    
    # ... (métodos __init__, _get_headers, _build_download_url continuam iguais) ...

    # ---------------------------------------------------------
    # TIPO DE INGESTÃO 1: STREAM PARA DESTINO (Disco, S3, GCS)
    # INGESTION TYPE 1: STREAM TO DESTINATION (Disk, S3, GCS)
    # ---------------------------------------------------------
    async def download(
        self, 
        hostname: str, 
        site_path: str, 
        file_path: str, 
        dest_path: str,
        destination: "BaseDestination" = None
    ) -> str:
        """
        Faz o streaming de um arquivo do SharePoint para um URI de destino.
        Streams a file from SharePoint to a destination URI.
        """
        download_url = self._build_download_url(hostname, site_path, file_path)
        
        # Se nenhuma configuração de destino for fornecida, assume que é local
        # If no destination config is provided, assume it is local
        if destination is None:
            from .destinations import LocalDestination
            destination = LocalDestination()
            
        storage_options = destination.get_storage_options()
        
        # Substituímos o print por logger.info
        # We replaced print with logger.info
        logger.info(f"Iniciando o download de {file_path} para {dest_path}...")
        logger.info(f"Starting download from {file_path} to {dest_path}...")
        
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream("GET", download_url, headers=self._get_headers()) as response:
                
                # Se houver erro HTTP, podemos usar o logger.error antes de falhar
                # If there's an HTTP error, we can use logger.error before failing
                if response.status_code != 200:
                    logger.error(f"Falha ao baixar o arquivo. Status: {response.status_code}")
                    logger.error(f"Failed to download the file. Status: {response.status_code}")
                    response.raise_for_status()
                
                with fsspec.open(dest_path, "wb", **storage_options) as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
        
        # Substituímos o print final por logger.info
        # We replaced the final print with logger.info
        logger.info("Download concluído com sucesso!")
        logger.info("Download completed successfully!")
                        
        return dest_path