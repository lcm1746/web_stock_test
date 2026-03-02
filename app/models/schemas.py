"""API 스키마 정의"""
from datetime import date
from typing import Optional
from pydantic import BaseModel


class StockQuote(BaseModel):
    """주가 정보"""
    ticker: str
    name: str
    close: float
    change: float
    change_pct: float
    volume: int
    market: str  # KOSPI | KOSDAQ


class StockIndicator(BaseModel):
    """기술적 지표"""
    ticker: str
    date: str
    ma5: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None


class ChartData(BaseModel):
    """차트용 OHLCV 데이터"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class NewsItem(BaseModel):
    """뉴스 항목"""
    title: str
    link: str
    source: str  # domestic | international
    published: Optional[str] = None
    summary: Optional[str] = None


class DailyReport(BaseModel):
    """일일 리포트"""
    report_date: date
    market_overview: dict
    data_meta: Optional[dict] = None  # 지연시간, 출처 등
    recommended_stocks: list  # confidence_score, explainable_reason 포함
    domestic_news: list
    international_news: list
