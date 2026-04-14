from pydantic import BaseModel


class DocumentTypeBase(BaseModel):
    name: str
    code: str


class DocumentTypeResponse(BaseModel):
    id: int
    name: str
    code: str

    class Config:
        from_attributes = True
