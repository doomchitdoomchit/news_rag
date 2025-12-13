import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import News
import uuid

SOURCE_URL = "https://www.hankyung.com/mr"

def crawl_news(db: Session):
    response = requests.get(SOURCE_URL)
    if response.status_code != 200:
        print(f"Failed to fetch {SOURCE_URL}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    # This selector might need adjustment based on actual page structure
    # Inspecting hankyung.com/mr structure usually involves specific classes
    # Assuming a generic structure for now, user might need to refine selectors
    articles = soup.select("ul.news_list li .txt_wrap") 
    
    if not articles:
         # Fallback or different selector attempt
         articles = soup.select(".news-list .article")

    new_items = []
    crawled_count = 0
    for article in articles:
        try:
            title_tag = article.select_one("h3.news_tit a") or article.select_one("h2.news_tit a")
            if not title_tag:
                 continue
            
            title = title_tag.get_text(strip=True)
            url = title_tag['href']
            
            # Check duplication
            existing = db.query(News).filter(News.url == url).first()
            if existing:
                continue

            # Fetch content (simple fetch)
            # content_res = requests.get(url)
            # content_soup = BeautifulSoup(content_res.text, 'html.parser')
            # content = content_soup.select_one("#article-body").get_text(strip=True) # Hypothetical ID
            content = title # Placeholder if deep crawling is expensive/blocked, but PRD implies content.
            # Real implementation needs per-article Request, which can be slow. 
            # For now, let's just store Title as content or try to fetch if easy.
            
            # Let's assume we want full content
            try:
                article_res = requests.get(url)
                if article_res.status_code == 200:
                    a_soup = BeautifulSoup(article_res.text, 'html.parser')
                    body = a_soup.select_one("#articletxt") or a_soup.select_one(".article-body")
                    content = body.get_text(strip=True) if body else title
            except Exception as e:
                print(f"Error fetching article content: {e}")
                content = title

            # Author extraction
            author_tag = article.select_one(".guest-author-name-wrap")
            author = "Unknown"
            if author_tag:
                author = author_tag.get_text(strip=True)

            # Save to SQL
            news_item = News(title=title, url=url, content=content, author=author)
            db.add(news_item)
            db.commit()
            db.refresh(news_item)
            
            crawled_count += 1
            new_items.append({
                "id": str(news_item.id),
                "title": news_item.title,
                "content": news_item.content,
                "url": news_item.url,
                "author": news_item.author
            })
            
        except Exception as e:
            print(f"Error processing article: {e}")
            continue
            
    return new_items
