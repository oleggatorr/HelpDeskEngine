# app\core\storage\local_storage.py
from pathlib import Path
import uuid
from .file_storage import FileStorage
from loguru import logger

class LocalFileStorage(FileStorage):

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("__init__")

    def save(self, content: bytes, filename: str) -> str:
        ext = Path(filename).suffix
        path = self.base_path / f"{uuid.uuid4().hex}{ext}"

        path.write_bytes(content)
        logger.info("write_bytes")    
        return str(path)

    def delete(self, path: str) -> bool:
        try:
            Path(path).unlink(missing_ok=True)
            logger.info("delete")
            return True
        except Exception:
            return False

    def read(self, path: str) -> bytes:
        logger.info("read")
        return Path(path).read_bytes()