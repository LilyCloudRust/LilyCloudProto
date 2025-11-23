from fastapi import APIRouter, Depends, HTTPException, status
from lilycloudproto.models.auth import TokenResponse, LoginRequest
from  lilycloudproto.infra.auth_repository import AuthRepository
from sqlalchemy.ext.asyncio import AsyncSession
from lilycloudproto.database import get_db
router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = AuthRepository(db)
    token = await repo.authenticate(payload.username, payload.password)
    if not token:
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return token