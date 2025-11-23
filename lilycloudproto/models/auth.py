from typing import ClassVar

from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel):
  username:str
  password:str

class TokenResponse(BaseModel):
  access_token:str
  refresh_token:str
  token_type: str = "bearer" # 加上这个符合标准规范
  model_config: ClassVar[ConfigDict] = {"from_attributes": True}