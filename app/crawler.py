import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Article, Author
from typing import List, Optional
import re
import time
import random

SOURCE_URL = "https://www.hankyung.com/mr"

def crawl_news(db: Session) -> List[Article]:
    """
    Main entry point for crawling news.
    1. Fetches the source page to find new article links.
    2. Filters out articles that already exist in the DB.
    3. Crawls content for new articles.
    4. Saves Article and Author information, linking them.
    5. Returns the list of newly created Article objects.
    """
    print(f"Fetching {SOURCE_URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(SOURCE_URL, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch {SOURCE_URL}: Status {response.status_code}")
            return []
    except Exception as e:
        print(f"Request failed: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try primary selector
    articles_elements = soup.select('h3.news-tit > a[target="_blank"]')
    if not articles_elements:
        print("Primary selector failed. Trying fallback...")
        articles_elements = soup.select(".news-list .article")

    new_articles = []
    
    for element in articles_elements:
        try:
            url = element.get('href')
            if not url or 'article' not in url:
                continue
                
            # deduplicate
            if db.query(Article).filter(Article.url == url).first():
                continue

            # This is a new article, crawl it
            article = crawl_article(db, url, headers)
            if article:
                new_articles.append(article)
                # Random delay to avoid blocking
                time.sleep(random.uniform(1, 3))
                
        except Exception as e:
            print(f"Error processing element: {e}")
            continue

    return new_articles

def crawl_article(db: Session, url: str, headers: dict) -> Optional[Article]:
    """
    Fetches a single article, extracts data, and saves to DB.
    """
    print(f"Crawling article: {url}")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch {url}")
            return None
    except Exception as e:
        print(f"Failed to request {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 1. Title
    title_elem = soup.select_one('.headline') or soup.find('h1')
    title = title_elem.get_text(strip=True) if title_elem else "No Title"

    # 2. Content
    body = soup.select_one("#articletxt") or soup.select_one(".article-body")
    content = body.get_text(strip=True) if body else ""

    # 3. Date
    write_time_elems = soup.select(".txt-date")
    recent_write = datetime.utcnow()
    if write_time_elems:
        date_str = write_time_elems[-1].get_text(strip=True)
        recent_write = parse_date(date_str)

    # 4. Authors
    author_tags = soup.select(".guest-author-name-wrap")
    authors = []
    
    for author_tag in author_tags:
        raw_code = author_tag.get('data-user', '').strip()
        name = author_tag.get('data-name', '').strip()
        
        if raw_code:
            # Format code as per requirement: "hk" + code + "06"
            # Note: The original code had "hk" + f"{author_code:06}"
            # I will preserve this logic.
            if isinstance(raw_code, int) or raw_code.isdigit():
                author_code = f"hk{int(raw_code):06}"
            else:
                author_code = raw_code
            
            # Check if author exists
            author_obj = db.query(Author).filter(Author.code == author_code).first()
            if not author_obj:
               author_obj = Author(code=author_code, name=name)
               db.add(author_obj)
               # We need to flush to get the ID if we were using IDs, 
               # but SQLAlchemy object identity is enough for relationship assignment before commit.
            
            authors.append(author_obj)

    # Create Article
    new_article = Article(
        title=title,
        url=url,
        content=content,
        recent_write=recent_write,
        authors=authors # SQLAlchemy handles the association
    )
    
    db.add(new_article)
    try:
        db.commit()
        db.refresh(new_article)
        return new_article
    except Exception as e:
        print(f"Failed to save article {url}: {e}")
        db.rollback()
        return None

def parse_date(date_str: str) -> datetime:
    """
    Parses date string like '2024.05.28 14:30' or '2024-05-28 14:30'
    """
    try:
        # Remove Korean chars '입력', '수정' if present
        cleaned = re.sub(r'[^\d\.\-\: ]', '', date_str).strip()
        for fmt in ["%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M"]:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        return datetime.now()
    except Exception:
        return datetime.now()
