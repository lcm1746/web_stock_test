"""주식 데이터 API"""
from fastapi import APIRouter, Query
from app.services.stock_service import (
    get_index_overview,
    get_stock_ohlcv,
    get_stock_indicators,
    get_intraday_targets,
    get_top_stocks,
)

router = APIRouter()


@router.get("/index")
async def index_overview():
    """KOSPI/KOSDAQ 지수 현황"""
    return get_index_overview()


@router.get("/top")
async def top_stocks(
    market: str = Query("KOSPI", description="KOSPI | KOSDAQ"),
    limit: int = Query(10, ge=1, le=50),
):
    """거래량 상위 종목"""
    return get_top_stocks(market=market, limit=limit)


@router.get("/{ticker}/chart")
async def stock_chart(
    ticker: str,
    days: int = Query(120, ge=30, le=365),
):
    """종목 OHLCV 차트 데이터"""
    return get_stock_ohlcv(ticker, days=days)


@router.get("/{ticker}/indicators")
async def stock_indicators(ticker: str):
    """종목 기술적 지표"""
    return get_stock_indicators(ticker)


@router.get("/{ticker}/targets")
async def stock_targets(ticker: str):
    """일일 단타 예상가 (매수/매도/손절)"""
    return get_intraday_targets(ticker)
