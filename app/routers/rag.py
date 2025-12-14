from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.rag_graph import app_rag
from langchain_core.messages import HumanMessage, ToolMessage


router = APIRouter(
    prefix="/rag",
    tags=["rag"],
    responses={404: {"description": "Not found"}},
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    documents: list[str]

@router.post("/search", response_model=QueryResponse)
async def search_news(request: QueryRequest):
    """
    Search news articles using RAG.
    """
    try:
        inputs = {"messages": [HumanMessage(content=request.query)]}
        result = app_rag.invoke(inputs)
        return {
            "answer": result.get("generation", "No answer generated."),
            "documents": result.get("documents", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
