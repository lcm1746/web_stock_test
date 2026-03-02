"""뉴스 API"""
from fastapi import APIRouter, Query
from app.services.news_service import get_domestic_news, get_international_news

router = APIRouter()


@router.get("/domestic")
async def domestic_news(limit: int = Query(10, ge=1, le=30)):
    """국내 경제/주식 뉴스"""
    return get_domestic_news(limit=limit)


@router.get("/international")
async def international_news(limit: int = Query(10, ge=1, le=30)):
    """해외 경제/주식 뉴스"""
    return get_international_news(limit=limit)
