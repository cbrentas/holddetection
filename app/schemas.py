from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime

class WallUpdate(BaseModel):
    title: Optional[str] = None
    meta: Optional[dict] = None

class WallHoldCreate(BaseModel):
    class_name: str = "hold"
    label_text: Optional[str] = None
    label_x: Optional[float] = None
    label_y: Optional[float] = None
    x1: float
    y1: float
    x2: float
    y2: float
    is_hidden: bool = False
    geometry: Optional[dict] = None

    @model_validator(mode='after')
    def check_bbox(self):
        if self.x1 is not None and self.x2 is not None and self.x1 >= self.x2:
            raise ValueError('x2 must be strictly greater than x1')
        if self.y1 is not None and self.y2 is not None and self.y1 >= self.y2:
            raise ValueError('y2 must be strictly greater than y1')
        return self

class WallHoldUpdate(BaseModel):
    class_name: Optional[str] = None
    label_text: Optional[str] = None
    label_x: Optional[float] = None
    label_y: Optional[float] = None
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    is_hidden: Optional[bool] = None
    geometry: Optional[dict] = None

    @model_validator(mode='after')
    def check_bbox(self):
        if self.x1 is not None and self.x2 is not None and self.x1 >= self.x2:
            raise ValueError('x2 must be strictly greater than x1')
        if self.y1 is not None and self.y2 is not None and self.y1 >= self.y2:
            raise ValueError('y2 must be strictly greater than y1')
        return self

class RouteCreate(BaseModel):
    name: str
    difficulty: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None

class RouteUpdate(BaseModel):
    name: Optional[str] = None
    difficulty: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None

class RouteHoldCreate(BaseModel):
    wall_hold_id: str
    role: str = "hand"
    order_index: Optional[int] = None

class RouteHoldUpdate(BaseModel):
    role: Optional[str] = None
    order_index: Optional[int] = None

class UserRegister(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)
    display_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

