from typing import Optional, List
from pydantic import BaseModel


# ==========================================
# DEPARTMENT
# ==========================================

class DepartmentCreate(BaseModel):
    name: str


class DepartmentResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class DepartmentListResponse(BaseModel):
    items: List[DepartmentResponse]
    total: int


# ==========================================
# LOCATION
# ==========================================

class LocationCreate(BaseModel):
    name: str


class LocationResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class LocationListResponse(BaseModel):
    items: List[LocationResponse]
    total: int


# ==========================================
# CAUSE CODE
# ==========================================

class CauseCodeCreate(BaseModel):
    code: str
    description: Optional[str] = None


class CauseCodeResponse(BaseModel):
    id: int
    code: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CauseCodeListResponse(BaseModel):
    items: List[CauseCodeResponse]
    total: int
