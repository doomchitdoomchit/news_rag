from typing import List, Dict
from app.database import vector_store
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from uuid import uuid4


def index_to_chroma(news_items: List[Dict]):
    """
    Index a list of news items to ChromaDB using LangChain wrapper.
    Expected format for news_items: 
    [{"id": str, "title": str, "content": str, "url": str, "authors": List[str], "recent_write": str}]
    """

    # Check for existing URLs
    new_items = []
    skipped_count = 0
    
    for item in news_items:
        # Check if URL already exists
        results = vector_store.get(where={"url": item["url"]})
        if results and results["ids"]:
            skipped_count += 1
            continue
        new_items.append(item)
    
    if skipped_count > 0:
        print(f"Skipped {skipped_count} articles that were already indexed.")

    if not new_items:
        print("No new articles to index.")
        return 0, skipped_count

    # Create Document objects
    documents = [
        Document(
            page_content=item["content"], 
            metadata={
                "title": item["title"],
                "url": item["url"],
                "authors": ", ".join(item.get("authors", [])) if isinstance(item.get("authors"), list) else str(item.get("authors", "Unknown")),
                "published_at": item.get("recent_write", datetime.now()).isoformat()
            }
        ) 
        for item in new_items
    ]

    documents = split_documents(documents)

    ids = [str(uuid4()) for _ in range(len(documents))]

    try:
        vector_store.add_documents(
            documents=documents,
            ids=ids
        )
        print(f"Successfully indexed {len(new_items)} articles to ChromaDB.")
        return len(new_items), skipped_count
    except Exception as e:
        print(f"Error indexing to ChromaDB: {e}")
        return 0, skipped_count

def split_documents(documents: List[Document]):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size = 1000, chunk_overlap = 200, add_start_index=True)
    return text_splitter.split_documents(documents)
