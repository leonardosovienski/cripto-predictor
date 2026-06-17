"""predictor-core.net — download utilitário com suporte a proxy corporativo."""
import urllib.request
import urllib.error
import pathlib
import logging
import hashlib
import shutil
import time

logger = logging.getLogger(__name__)

_USER_AGENT = "predictor-stocks/0.1 (research)"


def download_file(url: str, dest: pathlib.Path, timeout: int = 120,
                  retries: int = 3, backoff: float = 5.0) -> pathlib.Path:
    """Baixa url para dest (cria diretórios necessários). Retorna dest."""
    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    for attempt in range(1, retries + 1):
        try:
            logger.info("download attempt %d/%d: %s", attempt, retries, url)
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as out:
                shutil.copyfileobj(resp, out)
            tmp.replace(dest)
            logger.info("saved to %s", dest)
            return dest
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.warning("attempt %d failed: %s", attempt, exc)
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                raise
    raise RuntimeError("unreachable")


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
