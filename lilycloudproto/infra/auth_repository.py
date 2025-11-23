from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import jwt
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from lilycloudproto.entities.user import User
from lilycloudproto.config import settings
from lilycloudproto.models.auth import TokenResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
class AuthRepository:
  """Repository class for auth-related database operations."""
  db: AsyncSession
  def __init__(self, db: AsyncSession):
    self.db = db
  # 将password数据表user里的hashed_password对比
  def verify_password(self,pwd:str,hashed_pwd:str)->bool:
    """
    校验密码
    :param pwd: 用户输入的明文密码
    :param hashed_pwd: 数据库中的哈希密码
    """

    return pwd_context.verify(pwd, hashed_pwd)
  #生成access_token
  def generate_token(self,data: dict,minutes:int|None=None)->str:
    to_encode = data.copy()
    expire_minutes = minutes if minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

  async def authenticate(self,username:str,pwd:str)->Optional[TokenResponse]:
    # 通过username查询user
    statement=select(User).where(User.username==username)
    result = await self.db.execute(statement)
    user = result.scalar_one_or_none()
    #若用户不存在：None
    if not user:
      return None
    #若密码错误，返回None
    if not self.verify_password(pwd,user.hashed_password):
      return None
    #验证通过，返回TokenResponse
    access_token=self.generate_token({"sub":str(user.user_id)})
    refresh_token=self.generate_token({"sub":str(user.user_id)},settings.ACCESS_TOKEN_EXPIRE_MINUTES*24*7)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

