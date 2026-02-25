# src/spfetch/client.py
import httpx
import fsspec
import logging
import io
import time
from datetime import datetime
from tqdm import tqdm
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

    @retry_on_429(max_retries=3)
    async def _get_file_size(self, http_client: httpx.AsyncClient, site_id: str, file_path: str) -> int:
        """
        Obtém o tamanho do arquivo em bytes para configurar a barra de progresso.
        Gets the file size in bytes to configure the progress bar.
        """
        clean_file_path = file_path.strip("/")
        encoded_file_path = quote(clean_file_path, safe='/')
        url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{encoded_file_path}"
        
        response = await http_client.get(url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json().get("size", 0)
        return 0

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
        Faz o streaming de um arquivo do SharePoint para um URI de destino com telemetria padronizada.
        Streams a file from SharePoint to a destination URI with standardized telemetry.
        """
        if destination is None:
            from .destinations import LocalDestination
            destination = LocalDestination()
            
        storage_options = destination.get_storage_options()
        dest_type = destination.__class__.__name__
        
        start_perf = time.perf_counter()
        start_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"\n🚀 [INGESTÃO STREAMING | STREAMING INGESTION] Iniciada em | Started at: {start_date}")
        logger.info(f"📍 Destino | Destination: {dest_type} -> {dest_path}")
        
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            
            site_id = await self._get_site_id(http_client, hostname, site_path)
            total_size = await self._get_file_size(http_client, site_id, file_path)
            
            logger.info(f"📂 Origem | Source:  {file_path} ({total_size / (1024**3):.2f} GB)")
            
            clean_file_path = file_path.strip("/")
            encoded_file_path = quote(clean_file_path, safe='/')
            
            download_url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{encoded_file_path}:/content"
            
            async with http_client.stream("GET", download_url, headers=self._get_headers()) as response:
                if response.status_code != 200:
                    logger.error(f"❌ Falha ao baixar o arquivo. Status: {response.status_code} | Failed to download the file. Status: {response.status_code}")
                    response.raise_for_status()
                
                # Barra de progresso visual adaptável
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"📦 {dest_type}", colour='green') as pbar:
                    with fsspec.open(dest_path, "wb", **storage_options) as f:
                        async for chunk in response.aiter_bytes(chunk_size=1024 * 1024): # 1MB chunks
                            f.write(chunk)
                            pbar.update(len(chunk))
        
        # Cálculos de Performance
        end_perf = time.perf_counter()
        duration = end_perf - start_perf
        avg_speed = (total_size / (1024**2)) / duration if duration > 0 else 0
        
        logger.info("\n" + "-" * 55)
        logger.info(f"✅ INGESTÃO CONCLUÍDA COM SUCESSO | INGESTION COMPLETED SUCCESSFULLY")
        logger.info(f"⏱️ Tempo Total | Total Time: {duration:.2f}s")
        logger.info(f"⚡ Velocidade Média | Average Speed: {avg_speed:.2f} MB/s")
        logger.info(f"🏁 Finalizado em | Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 55 + "\n")
                        
        return dest_path
    
    
    # ---------------------------------------------------------
    # TIPO DE INGESTÃO 2: DIRETO PARA MEMÓRIA (PANDAS)
    # INGESTION TYPE 2: DIRECT TO MEMORY (PANDAS)
    # ---------------------------------------------------------
    @retry_on_429(max_retries=3)
    async def read_df(self, hostname: str, site_path: str, file_path: str, **kwargs) -> Any:
        """
        Baixa um arquivo do SharePoint diretamente para a RAM (Pandas DataFrame) com telemetria padronizada.
        Downloads a file from SharePoint directly into RAM (Pandas DataFrame) with standardized telemetry.
        """
        try:
            import pandas as pd
        except ImportError:
            erro_msg = "Pandas não encontrado. Instale com: pip install spfetch[pandas] / Pandas not found."
            logger.error(erro_msg)
            raise ImportError(erro_msg)

        start_perf = time.perf_counter()
        start_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"\n🚀 [INGESTÃO MEMÓRIA | MEMORY INGESTION] Iniciada em | Started at: {start_date}")
        logger.info(f"📍 Destino | Destination: Pandas DataFrame (RAM)")
        
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            site_id = await self._get_site_id(http_client, hostname, site_path)
            total_size = await self._get_file_size(http_client, site_id, file_path)
            
            logger.info(f"📂 Origem | Source:  {file_path} ({total_size / (1024**2):.2f} MB)")
            
            clean_file_path = file_path.strip("/")
            encoded_file_path = quote(clean_file_path, safe='/')
            
            download_url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{encoded_file_path}:/content"
            
            # Usando streaming também para o Pandas para atualizar a barra de progresso
            virtual_file = io.BytesIO()
            async with http_client.stream("GET", download_url, headers=self._get_headers()) as response:
                if response.status_code != 200:
                    logger.error(f"❌ Falha ao ler o arquivo. Status: {response.status_code} | Failed to read the file. Status: {response.status_code}")
                    response.raise_for_status()
                
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"📦 Pandas DF", colour='blue') as pbar:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        virtual_file.write(chunk)
                        pbar.update(len(chunk))
            
            virtual_file.seek(0)
            
            file_lower = file_path.lower()
            if file_lower.endswith('.csv'):
                df = pd.read_csv(virtual_file, **kwargs)
            elif file_lower.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(virtual_file, **kwargs)
            else:
                erro_msg = "Formato não suportado. Use .csv, .xlsx ou .xls / Unsupported format. Use .csv, .xlsx, or .xls"
                logger.error(erro_msg)
                raise ValueError(erro_msg)
            
            # Cálculos de Performance
            end_perf = time.perf_counter()
            duration = end_perf - start_perf
            avg_speed = (total_size / (1024**2)) / duration if duration > 0 else 0
            
            logger.info("\n" + "-" * 55)
            logger.info(f"✅ INGESTÃO CONCLUÍDA COM SUCESSO | INGESTION COMPLETED SUCCESSFULLY")
            logger.info(f"📊 Dimensões | Dimensions: {df.shape[0]} linhas/rows x {df.shape[1]} colunas/cols")
            logger.info(f"⏱️ Tempo Total | Total Time: {duration:.2f}s | ⚡ Vel. Média | Avg Speed: {avg_speed:.2f} MB/s")
            logger.info(f"🏁 Finalizado em | Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("-" * 55 + "\n")
            
            return df
            
            
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
        logger.info(f"Iniciando listagem da pasta: '{folder_path}' em {site_path} | Starting listing of folder: '{folder_path}' in {site_path}")
        
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

            logger.debug(f"Requisição para endpoint: {endpoint} | Request to endpoint: {endpoint}")
            
            # 3. Executa a chamada com os headers de autenticação
            response = await http_client.get(endpoint, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.error(f"Erro na API Graph (Status {response.status_code}): {response.text} | Graph API Error (Status {response.status_code}): {response.text}")
                response.raise_for_status()

            items = response.json().get("value", [])
            logger.info(f"Sucesso: {len(items)} itens encontrados em '{folder_path}'. | Success: {len(items)} items found in '{folder_path}'.")

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