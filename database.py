from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("LOCAL_DATABASE_URL", "")
engine = create_async_engine(url, pool_pre_ping=True) 
AsyncSessionLocal = async_sessionmaker(autoflush=False, autocommit=False, bind=engine)

