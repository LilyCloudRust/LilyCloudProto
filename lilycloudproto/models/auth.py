from typing import ClassVar

from pydantic import BaseModel, ConfigDict

class loginRequest(BaseModel):
  username:str
  password:str

class TokenResponse(BaseModel):
  access_token:str
  refresh_token:str
  model_config: ClassVar[ConfigDict] = {"from_attributes": True}