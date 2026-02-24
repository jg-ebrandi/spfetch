import asyncio
import logging
import functools
from httpx import HTTPStatusError

logger = logging.getLogger("spfetch")

def retry_on_429(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorador para realizar retentativas automáticas em caso de erro 429 (Throttling).
    Decorator to automatically retry on 429 error (Throttling).
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except HTTPStatusError as e:
                    if e.response.status_code == 429 and retries < max_retries:
                        # Extrai o tempo de espera do header 'Retry-After' se existir
                        wait_time = float(e.response.headers.get("Retry-After", base_delay * (2 ** retries)))
                        
                        logger.warning(
                            f"⚠️ Erro 429 (Throttling) detectado em {func.__name__}. "
                            f"Tentativa {retries + 1}/{max_retries}. "
                            f"Aguardando {wait_time}s antes de tentar novamente..."
                        )
                        await asyncio.sleep(wait_time)
                        retries += 1
                        continue
                    raise e # Se não for 429 ou estourar as tentativas, lança o erro original
            return await func(*args, **kwargs)
        return wrapper
    return decorator