from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.crawler import crawl_news
from app.indexing import index_to_chroma
from datetime import date
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import cast, Date
from app.models import Article

router = APIRouter(
    prefix="/news",
    tags=["news"],
    responses={404: {"description": "Not found"}},
)

@router.post("/crawl")
async def trigger_crawl(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger the news crawler to fetch latest articles from Korean Economic Daily.
    Indexing to ChromaDB happens in the background.
    """
    try:
        new_articles = crawl_news(db)
        if new_articles:
            # Convert Article objects to dicts for indexing
            news_items = []
            for article in new_articles:
                news_items.append({
                    "id": str(article.id), # ID might be None if not flushed/refreshed, but crawl_news does refresh
                    "title": article.title,
                    "content": article.content,
                    "url": article.url,
                    "authors": [a.name for a in article.authors],
                    "recent_write": article.recent_write
                })
            
            background_tasks.add_task(index_to_chroma, news_items)
            return {"status": "success", "message": f"Crawled {len(new_articles)} articles. Indexing started in background."}
        else:
             return {"status": "success", "message": "No new articles found."}
             
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
class DateRequest(BaseModel):
    date: date

@router.post("/index-by-date")
async def index_by_date(request: DateRequest, db: Session = Depends(get_db)):
    """
    Index articles from the database that match the given date.
    Date format: YYYY-MM-DD
    """
    try:
        # Query articles by date (filtering on crawled_at)
        articles = db.query(Article).filter(cast(Article.crawled_at, Date) == request.date).all()
        
        if not articles:
             return {"status": "success", "message": "No new articles found."}

        # Convert to news_items format
        news_items = []
        for article in articles:
            news_items.append({
                "id": str(article.id),
                "title": article.title,
                "content": article.content,
                "url": article.url,
                "authors": [a.name for a in article.authors],
                "recent_write": article.recent_write
            })
            
        # Index to ChromaDB
        indexed, skipped = index_to_chroma(news_items)
        
        return {
            "status": "success",
            "message": "Indexing complete.",
            "data": {
                "total_found": len(articles),
                "indexed_count": indexed,
                "skipped_count": skipped
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
