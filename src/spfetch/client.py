# src/spfetch/client.py
import httpx
import fsspec
import io
import time
import asyncio
from datetime import datetime
from tqdm import tqdm
from typing import Any, Union, List
from urllib.parse import quote
from .auth import SharePointAuth
from spfetch.utils import retry_on_429

class SharePointClient:
    """
    Cliente moderno para ingestão de dados do SharePoint via Microsoft Graph API.
    Focado em performance de streaming, telemetria de barra dupla e concorrência (Worker Pool).
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

    async def download(
        self, 
        hostname: str, 
        site_path: str, 
        file_path: Union[str, List[str]], 
        dest_path: Union[str, List[str]],
        destination: Any = None,
        chunk_size_mb: int = 1,
        buffer_size_mb: int = 16,
        max_concurrency: int = 1
    ) -> Any:
        
        if destination is None:
            from .destinations import LocalDestination
            destination = LocalDestination()
            
        dest_type = destination.__class__.__name__

        files_src = [f.strip() for f in file_path.split('|')] if isinstance(file_path, str) else file_path
        files_dst = [d.strip() for d in dest_path.split('|')] if isinstance(dest_path, str) else dest_path

        if len(files_src) != len(files_dst):
            raise ValueError("O número de arquivos de origem deve ser igual ao de destino.")

        total_files = len(files_src)
        actual_concurrency = min(max_concurrency, total_files)

        available_slots = asyncio.Queue()
        for i in range(actual_concurrency):
            available_slots.put_nowait(i)

        print(f"\n🚀 Iniciando Ingestão | Starting Ingestion (Number of files: {total_files} | concurrency: {actual_concurrency})\n")

        # =====================================================================
        # WORKER INTERNO ISOLADO
        # =====================================================================
        @retry_on_429(max_retries=5)
        async def _process_file(src: str, dst: str) -> str:
            # 1. Pega o lugar na tela ANTES de começar e segura até a morte!
            slot = await available_slots.get()
            pos_offset = slot * 3 
            short_name = src.split('/')[-1][:20]
            
            try:
                max_attempts = 3
                for attempt in range(1, max_attempts + 1):
                    start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    start_perf = time.perf_counter()
                    sep = p1 = p2 = None
                    
                    try:
                        storage_options = destination.get_storage_options()
                        if "blocksize" not in storage_options:
                            storage_options["blocksize"] = buffer_size_mb * 1024 * 1024
                        chunk_size_bytes = chunk_size_mb * 1024 * 1024
                        
                        async with httpx.AsyncClient(follow_redirects=True, timeout=None) as http_client:
                            site_id = await self._get_site_id(http_client, hostname, site_path)
                            total_size = await self._get_file_size(http_client, site_id, src)
                            
                            download_url = f"{self.base_graph_url}/sites/{site_id}/drive/root:/{quote(src.strip('/'), safe='/')}:/content"
                            
                            async with http_client.stream("GET", download_url, headers=self._get_headers()) as response:
                                response.raise_for_status()
                                
                                sep = tqdm(total=0, bar_format="{desc}", desc="----------------------------------------", position=pos_offset, leave=False)
                                p1 = tqdm(total=total_size, unit='B', unit_scale=True, desc=f"📥 Reading | Leitura  ({short_name})", colour='#3498db', position=pos_offset + 1, leave=False)
                                p2 = tqdm(total=total_size, unit='B', unit_scale=True, desc=f"📤 Saving  | Salvando   ({short_name})", colour='#2ecc71', position=pos_offset + 2, leave=False)
                                
                                with fsspec.open(dst, "wb", **storage_options) as f:
                                    async for chunk in response.aiter_bytes(chunk_size=chunk_size_bytes):
                                        f.write(chunk)
                                        p1.update(len(chunk))
                                        p2.update(len(chunk))
                        
                        # 🟢 SUCESSO ABSOLUTO
                        duration = time.perf_counter() - start_perf
                        avg_speed = (total_size / (1024**2)) / duration if duration > 0 else 0
                        
                        m, s = divmod(int(duration), 60)
                        dur_fmt = f"{m:02d}:{s:02d}"
                        size_gb = total_size / (1024**3)
                        size_mb = total_size / (1024**2)
                        
                        BLUE = "\033[38;2;52;152;219m"
                        GREEN = "\033[38;2;46;204;113m"
                        RESET = "\033[0m"
                        blocks = "█" * 45
                        
                        bar_blue = f"{BLUE}{blocks}{RESET}"
                        bar_green = f"{GREEN}{blocks}{RESET}"

                        final_log = f"""
✅ INGESTION COMPLETED SUCCESSFULLY
📂 Source | Fonte: {src} ({size_gb:.2f} GB)
📍 Destination | Destino: {dest_type} -> {dst} (Chunk: {chunk_size_mb}MB | Buffer: {buffer_size_mb}MB)

⌛ Total Time | Tempo total: {duration:.2f}s
🚀 Started at | Começou em: {start_time_str}
🏁 Finished at | Terminou em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚡ Average Speed | Velocidade média: {avg_speed:.2f} MB/s

📥 Reading | Leitura: 100%|{bar_blue}| {size_mb:.1f}M/{size_mb:.1f}M [{dur_fmt}<00:00, {avg_speed:.1f}MB/s]
📤 Saving  | Salvando: 100%|{bar_green}| {size_mb:.1f}M/{size_mb:.1f}M [{dur_fmt}<00:00, {avg_speed:.1f}MB/s]
-------------------------------------------------------\n"""
                        # Apaga as barras normais e escreve o log final
                        if sep is not None: sep.close()
                        if p1 is not None: p1.close()
                        if p2 is not None: p2.close()
                        
                        tqdm.write(final_log)
                        return dst

                    except Exception as e:
                        # 🔴 OCORREU UM ERRO (Inicia Protocolo de Retry)
                        if sep is not None: sep.close()
                        if p1 is not None: p1.close()
                        if p2 is not None: p2.close()

                        if attempt < max_attempts:
                            # 💡 A MÁGICA: Em vez de sumir com a tela, desenha o aviso no exato mesmo lugar das barras
                            warn_sep = tqdm(total=0, bar_format="{desc}", desc="----------------------------------------", position=pos_offset, leave=False)
                            warn_p1 = tqdm(total=0, bar_format="{desc}", desc=f"⚠️ FALHA | RETRY ({short_name}) [{attempt}/{max_attempts}]", position=pos_offset + 1, leave=False)
                            warn_p2 = tqdm(total=0, bar_format="{desc}", desc=f"⏳ Aguardando 3s... Erro: {str(e)[:45]}", position=pos_offset + 2, leave=False)
                            
                            await asyncio.sleep(3) # Dorme os 3s com as mensagens ativas na tela
                            
                            warn_sep.close()
                            warn_p1.close()
                            warn_p2.close()
                            continue # Vai rodar o for novamente e recriar as barras azuis normais
                        else:
                            # ❌ MORREU DE VEZ (Imprime o erro bonitão)
                            duration = time.perf_counter() - start_perf
                            error_log = f"""
❌ INGESTION FAILED | FALHA NA INGESTÃO
📂 Source | Fonte: {src}
📍 Destination | Destino: {dest_type} -> {dst}
⚠️ Error | Erro: {str(e)}

⌛ Total Time | Tempo total da tentativa: {duration:.2f}s
🚀 Started at | Começou em: {start_time_str}
🏁 Failed at | Falhou em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-------------------------------------------------------\n"""
                            tqdm.write(error_log)
                            return f"ERROR: {src}"

            finally:
                # 🧹 LIMPEZA FINAL (Libera o Slot para o próximo arquivo da fila de verdade)
                available_slots.put_nowait(slot)

        # =====================================================================
        # DISPARADOR DAS TAREFAS
        # =====================================================================
        if actual_concurrency == 1:
            results = []
            for src, dst in zip(files_src, files_dst):
                results.append(await _process_file(src, dst))
            return results
        else:
            semaphore = asyncio.Semaphore(actual_concurrency)
            async def sem_worker(src, dst):
                async with semaphore:
                    return await _process_file(src, dst)
            
            tasks = [sem_worker(src, dst) for src, dst in zip(files_src, files_dst)]
            return await asyncio.gather(*tasks, return_exceptions=True)

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