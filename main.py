from fastapi import FastAPI
# from app.routers import crawl, search, summary # Will implement these later
import uvicorn

from contextlib import asynccontextmanager
from app.scheduler import scheduler
from app.database import engine
from app.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Start scheduler
    scheduler.start()
    yield
    # Shutdown scheduler
    scheduler.shutdown()

app = FastAPI(
    title="News RAG API",
    description="API for scraping news and performing RAG operations",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "Welcome to News RAG API"}

from fastapi.middleware.cors import CORSMiddleware
from app.routers import news, rag

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router)
app.include_router(rag.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
