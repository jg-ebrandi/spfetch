# src/spfetch/client.py
import httpx
import fsspec
import logging
import io
from typing import Any, Optional
from urllib.parse import quote
from .auth import SharePointAuth
from spfetch.utils import retry_on_429

# Configuração padrão do logger para a biblioteca spfetch
# Standard logger configuration for the spfetch library
logger = logging.getLogger("spfetch")
logger.addHandler(logging.NullHandler())

class SharePointClient:
    """
    Cliente principal para interagir com o SharePoint via Microsoft Graph API.
    Main client to interact with SharePoint via Microsoft Graph API.
    """
    
    def __init__(self, auth: SharePointAuth):
        self.auth = auth
        self.base_graph_url = "https://graph.microsoft.com/v1.0"

    def _get_headers(self) -> dict:
        """
        Recupera os cabeçalhos HTTP com o Token Bearer atualizado.
        Retrieves HTTP headers containing the active Bearer token.
        """
        token = self.auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
    
    @retry_on_429(max_retries=3)
    async def _get_site_id(self, http_client: httpx.AsyncClient, hostname: str, site_path: str) -> str:
        """
        Obtém o ID único do Site no SharePoint para evitar erros de formatação (Erro 400).
        Gets the unique Site ID in SharePoint to avoid formatting errors (Error 400).
        """
        clean_site_path = site_path.strip("/")
        
        # O Graph API aceita buscar o site pelo caminho relativo
        # The Graph API accepts fetching the site by relative path
        url = f"{self.base_graph_url}/sites/{hostname}:/{clean_site_path}"
        
        response = await http_client.get(url, headers=self._get_headers())
        if response.status_code != 200:
            logger.error(f"Site '{site_path}' não encontrado. / Site '{site_path}' not found.")
            response.raise_for_status()
            
        return response.json()["id"]


    # ---------------------------------------------------------
    # TIPO DE INGESTÃO 1: STREAM PARA DESTINO (Disco, S3, GCS)
    # INGESTION TYPE 1: STREAM TO DESTINATION (Disk, S3, GCS)
    # ---------------------------------------------------------
    @retry_on_429(max_retries=5)
    async def download(
        self, 
        hostname: str, 
        site_path: str, 
        file_path: str, 
        dest_path: str,
        destination: Any = None
    ) -> str:
        """
        Faz o streaming de um arquivo do SharePoint para um URI de destino.
        Streams a file from SharePoint to a destination URI.
        """
        if destination is None:
            from .destinations import LocalDestination
            destination = LocalDestination()
            
        storage_options = destination.get_storage_options()
        
        logger.info(f"Iniciando o download de {file_path} para {dest_path}...")
        logger.info(f"Starting download from {file_path} to {dest_path}...")
        
        # Adicionamos 'follow_redirects=True' para permitir o redirecionamento 302 da Microsoft
        # We added 'follow_redirects=True' to allow Microsoft's 302 redirect
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            
            site_id = await self._get_site_id(http_client, hostname, site_path)
            
            clean_file_path = file_path.strip("/")
            encoded_file_path = quote(clean_file_path, safe='/')
            
            download_url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{encoded_file_path}:/content"
            
            async with http_client.stream("GET", download_url, headers=self._get_headers()) as response:
                if response.status_code != 200:
                    logger.error(f"Falha ao baixar o arquivo. Status: {response.status_code}")
                    logger.error(f"Failed to download the file. Status: {response.status_code}")
                    response.raise_for_status()
                
                with fsspec.open(dest_path, "wb", **storage_options) as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
        
        logger.info("Download concluído com sucesso!")
        logger.info("Download completed successfully!")
                        
        return dest_path
    
    
    # ---------------------------------------------------------
    # TIPO DE INGESTÃO 2: DIRETO PARA MEMÓRIA (PANDAS)
    # INGESTION TYPE 2: DIRECT TO MEMORY (PANDAS)
    # ---------------------------------------------------------
    @retry_on_429(max_retries=3)
    async def read_df(self, hostname: str, site_path: str, file_path: str, **kwargs) -> Any:
        """
        Baixa um arquivo (Excel ou CSV) do SharePoint diretamente para um DataFrame Pandas.
        Downloads a file (Excel or CSV) from SharePoint directly into a Pandas DataFrame.
        """
        # Lazy Import: Só exige o Pandas se o dev usar esta função!
        # Lazy Import: Only requires Pandas if the dev uses this function!
        try:
            import pandas as pd
        except ImportError:
            erro_msg = "Pandas não encontrado. Instale com: pip install spfetch[pandas] / Pandas not found."
            logger.error(erro_msg)
            raise ImportError(erro_msg)

        logger.info(f"Lendo o arquivo {file_path} para a memória...")
        logger.info(f"Reading file {file_path} into memory...")
        
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            site_id = await self._get_site_id(http_client, hostname, site_path)
            clean_file_path = file_path.strip("/")
            encoded_file_path = quote(clean_file_path, safe='/')
            
            download_url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{encoded_file_path}:/content"
            
            response = await http_client.get(download_url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Falha ao ler o arquivo. Status: {response.status_code}")
                logger.error(f"Failed to read the file. Status: {response.status_code}")
                response.raise_for_status()
            
            virtual_file = io.BytesIO(response.content)
            
            # Decide qual motor usar com base na extensão do arquivo
            # Decides which engine to use based on the file extension
            file_lower = file_path.lower()
            if file_lower.endswith('.csv'):
                logger.info("Convertendo bytes para Pandas DataFrame (Formato CSV)...")
                return pd.read_csv(virtual_file, **kwargs)
            elif file_lower.endswith(('.xlsx', '.xls')):
                logger.info("Convertendo bytes para Pandas DataFrame (Formato Excel)...")
                return pd.read_excel(virtual_file, **kwargs)
            else:
                erro_msg = "Formato não suportado. Use .csv, .xlsx ou .xls / Unsupported format. Use .csv, .xlsx, or .xls"
                logger.error(erro_msg)
                raise ValueError(erro_msg)
            
            
    # ---------------------------------------------------------
    # EXPLORAÇÃO: LISTAGEM DE ARQUIVOS E PASTAS
    # EXPLORATION: FOLDER AND FILE LISTING
    # ---------------------------------------------------------
    @retry_on_429(max_retries=3)
    async def ls(self, hostname: str, site_path: str, folder_path: str = "/") -> list:
        """
        Lista o conteúdo de uma pasta no SharePoint e retorna metadados.
        Lists SharePoint folder contents and returns metadata.
        """
        logger.info(f"Iniciando listagem da pasta: '{folder_path}' em {site_path}")
        
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            # 1. Resolve o Site ID
            site_id = await self._get_site_id(http_client, hostname, site_path)
            
            # 2. Normaliza e codifica o caminho para a Graph API
            clean_folder_path = folder_path.strip("/")
            if clean_folder_path:
                encoded_path = quote(clean_folder_path, safe='/')
                endpoint = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{encoded_path}:/children"
            else:
                endpoint = f"{self.base_graph_url}/sites/{site_id}/drive/root/children"

            logger.debug(f"Requisição para endpoint: {endpoint}")
            
            # 3. Executa a chamada com os headers de autenticação
            response = await http_client.get(endpoint, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Erro na API Graph (Status {response.status_code}): {response.text}")
                response.raise_for_status()

            items = response.json().get("value", [])
            logger.info(f"Sucesso: {len(items)} itens encontrados em '{folder_path}'.")

        # 4. Retorna metadados estruturados
        return [
            {
                "name": item["name"],
                "is_folder": "folder" in item,
                "size": item.get("size", 0),
                "id": item["id"],
                "last_modified": item.get("lastModifiedDateTime"),
                "web_url": item.get("webUrl")
            }
            for item in items
        ]