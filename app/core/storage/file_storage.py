from abc import ABC, abstractmethod


class FileStorage(ABC):

    @abstractmethod
    def save(self, content: bytes, filename: str) -> str:
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        pass

    @abstractmethod
    def read(self, path: str) -> bytes:
        pass