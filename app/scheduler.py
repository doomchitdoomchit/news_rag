from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import SessionLocal
from app.crawler import crawl_news
from app.indexing import index_to_chroma
from datetime import datetime
import pytz

def scheduled_crawl():
    print(f"[{datetime.now()}] Starting scheduled crawl...")
    db = SessionLocal()
    try:
        new_items = crawl_news(db)
        if new_items:
            print(f"Crawled {len(new_items)} items. Starting indexing...")
            index_to_chroma(new_items)
        else:
             print("No new items crawled.")
    except Exception as e:
        print(f"Scheduled crawl failed: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler()

# Schedule to run at 8:00 AM KST (Asia/Seoul)
kst = pytz.timezone('Asia/Seoul')
trigger = CronTrigger(hour=8, minute=0, timezone=kst)

scheduler.add_job(scheduled_crawl, trigger)
