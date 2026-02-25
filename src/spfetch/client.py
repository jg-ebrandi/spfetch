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

# Configuração do logger
logger = logging.getLogger("spfetch")
logger.addHandler(logging.NullHandler())

class SharePointClient:
    """
    Cliente moderno para ingestão de dados do SharePoint via Microsoft Graph API.
    Focado em performance de streaming e telemetria de barra dupla.
    """
    
    def __init__(self, auth: SharePointAuth):
        self.auth = auth
        self.base_graph_url = "https://graph.microsoft.com/v1.0"

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.auth.get_token()}", "Accept": "application/json"}
    
    @retry_on_429(max_retries=3)
    async def _get_site_id(self, http_client: httpx.AsyncClient, hostname: str, site_path: str) -> str:
        url = f"{self.base_graph_url}/sites/{hostname}:/{site_path.strip('/')}"
        response = await http_client.get(url, headers=self._get_headers())
        if response.status_code != 200:
            response.raise_for_status()
        return response.json()["id"]

    @retry_on_429(max_retries=3)
    async def _get_file_size(self, http_client: httpx.AsyncClient, site_id: str, file_path: str) -> int:
        url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{quote(file_path.strip('/'), safe='/')}"
        response = await http_client.get(url, headers=self._get_headers())
        return response.json().get("size", 0) if response.status_code == 200 else 0

    @retry_on_429(max_retries=5)
    async def download(
        self, 
        hostname: str, 
        site_path: str, 
        file_path: str, 
        dest_path: str,
        destination: Any = None,
        chunk_size_mb: int = 1,
        buffer_size_mb: int = 16  # <-- Readicionado para evitar o TypeError
    ) -> str:
        if destination is None:
            from .destinations import LocalDestination
            destination = LocalDestination()
            
        storage_options = destination.get_storage_options()
        
        # Smart Buffering: configura o blocksize do fsspec
        if "blocksize" not in storage_options:
            storage_options["blocksize"] = buffer_size_mb * 1024 * 1024

        dest_type = destination.__class__.__name__
        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        
        start_perf = time.perf_counter()
        
        # Log inicial limpo (idêntico ao print)
        print(f"\n🚀 [INGESTÃO STREAMING | STREAMING INGESTION] Iniciada em | Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📍 Destino | Destination: {dest_type} -> {dest_path} (Chunk: {chunk_size_mb}MB | Buffer: {buffer_size_mb}MB)")
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=None) as http_client:
            site_id = await self._get_site_id(http_client, hostname, site_path)
            total_size = await self._get_file_size(http_client, site_id, file_path)
            
            print(f"📂 Origem | Source:  {file_path} ({total_size / (1024**3):.2f} GB)")
            
            download_url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{quote(file_path.strip('/'), safe='/')}:/content"
            
            async with http_client.stream("GET", download_url, headers=self._get_headers()) as response:
                response.raise_for_status()
                
                # Barras empilhadas com cores idênticas ao print de sucesso
                p2 = tqdm(total=total_size, unit='B', unit_scale=True, desc=f"📤 Saving | Salvando ({dest_type})", colour='#2ecc71', position=0, leave=True)
                p1 = tqdm(total=total_size, unit='B', unit_scale=True, desc=f"📥 Reading | Leitura (SP)", colour='#3498db', position=1, leave=True)
                
                with fsspec.open(dest_path, "wb", **storage_options) as f:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size_bytes):
                        f.write(chunk)
                        p1.update(len(chunk))
                        p2.update(len(chunk))
                
                p1.close()
                p2.close()

        duration = time.perf_counter() - start_perf
        avg_speed = (total_size / (1024**2)) / duration if duration > 0 else 0
        
        # Rodapé de conclusão
        print("\n-------------------------------------------------------")
        print(f"✅ INGESTÃO CONCLUÍDA COM SUCESSO | INGESTION COMPLETED SUCCESSFULLY")
        print(f"⏱️ Tempo Total | Total Time: {duration:.2f}s")
        print(f"⚡ Velocidade Média | Average Speed: {avg_speed:.2f} MB/s")
        print(f"🏁 Finalizado em | Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-------------------------------------------------------\n")
                        
        return dest_path

    @retry_on_429(max_retries=3)
    async def read_df(self, hostname: str, site_path: str, file_path: str, chunk_size_mb: int = 1, **kwargs) -> Any:
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("Pandas não encontrado. Instale com: pip install spfetch[pandas]")

        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        async with httpx.AsyncClient(follow_redirects=True, timeout=None) as http_client:
            site_id = await self._get_site_id(http_client, hostname, site_path)
            total_size = await self._get_file_size(http_client, site_id, file_path)
            download_url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{quote(file_path.strip('/'), safe='/')}:/content"
            
            virtual_file = io.BytesIO()
            async with http_client.stream("GET", download_url, headers=self._get_headers()) as response:
                response.raise_for_status()
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="📦 Pandas DF", colour='#3498db') as pbar:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size_bytes):
                        virtual_file.write(chunk)
                        pbar.update(len(chunk))
            
            virtual_file.seek(0)
            file_lower = file_path.lower()
            if file_lower.endswith('.csv'):
                return pd.read_csv(virtual_file, **kwargs)
            elif file_lower.endswith(('.xlsx', '.xls')):
                return pd.read_excel(virtual_file, **kwargs)
            else:
                raise ValueError("Formato não suportado (.csv, .xlsx, .xls)")

    @retry_on_429(max_retries=3)
    async def ls(self, hostname: str, site_path: str, folder_path: str = "/") -> list:
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            site_id = await self._get_site_id(http_client, hostname, site_path)
            clean_folder = folder_path.strip("/")
            endpoint = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{quote(clean_folder, safe='/')}:/children" if clean_folder else f"{self.base_graph_url}/sites/{site_id}/drive/root/children"
            response = await http_client.get(endpoint, headers=self._get_headers())
            response.raise_for_status()
            return [{"name": item["name"], "is_folder": "folder" in item, "size": item.get("size", 0)} for item in response.json().get("value", [])]