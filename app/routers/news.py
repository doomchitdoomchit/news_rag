from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.crawler import crawl_news
from app.indexing import index_to_chroma

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
