import httpx

def get_http_client():
    # Ambiente doméstico: verificação SSL habilitada por padrão
    return httpx.AsyncClient(timeout=30)
