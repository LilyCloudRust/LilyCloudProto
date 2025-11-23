from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent 
class Settings(BaseSettings):
    # 1. 定义字段
    # 如果 .env 里有这个变量，就用 .env 的值
    SECRET_KEY: str ="26f1d8bca14a1a6e94a545f2d2efadfbfc09d859d510dc1014d78744f58b8b22"
    
    # 2. 定义带默认值的字段
    ALGORITHM: str="HS256"
    
    # 3. 自动类型转换
    # .env 里读出来虽然是字符串 "60"，但 Pydantic 会自动把它转成 int 类型
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 4. 指定 .env 文件路径 (Pydantic V2 写法)
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), 
        env_file_encoding="utf-8",
        extra="ignore" 
    )

# 实例化配置对象，单例模式
settings = Settings()  # type: ignore