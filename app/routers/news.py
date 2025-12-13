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
        new_items = crawl_news(db)
        if new_items:
            background_tasks.add_task(index_to_chroma, new_items)
            return {"status": "success", "message": f"Crawled {len(new_items)} articles. Indexing started in background."}
        else:
             return {"status": "success", "message": "No new articles found."}
             
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
