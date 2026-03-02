"""일일 리포트 생성 서비스"""
from datetime import datetime
from app.services.stock_service import get_index_overview, get_top_stocks, get_stock_ohlcv, get_stock_indicators, get_intraday_targets
from app.services.news_service import get_domestic_news, get_international_news


def generate_daily_report() -> dict:
    """일일 추천 리포트 생성"""
    market_overview = get_index_overview()
    kospi_stocks = get_top_stocks("KOSPI", limit=5)
    kosdaq_stocks = get_top_stocks("KOSDAQ", limit=3)
    
    # 추천 종목 (거래량 상위 + 지표 기반 + 일일 단타 예상가)
    recommended = []
    for s in kospi_stocks[:3] + kosdaq_stocks[:2]:
        indicators = get_stock_indicators(s["ticker"])
        targets = get_intraday_targets(s["ticker"])
        recommended.append({
            **s,
            "indicators": indicators,
            "targets": targets,
            "reason": _get_reason(s, indicators),
        })
    
    domestic = get_domestic_news(limit=8)
    international = get_international_news(limit=6)
    
    return {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "report_time": datetime.now().strftime("%H:%M"),
        "market_overview": market_overview,
        "recommended_stocks": recommended,
        "domestic_news": domestic,
        "international_news": international,
    }


def _get_reason(stock: dict, indicators: dict) -> str:
    """추천 이유 생성"""
    reasons = []
    
    if indicators.get("rsi"):
        rsi = indicators["rsi"]
        if rsi < 30:
            reasons.append("RSI 과매도 구간(저평가)")
        elif rsi > 70:
            reasons.append("RSI 과매수 구간(모멘텀)")
        elif 40 <= rsi <= 60:
            reasons.append("RSI 균형 구간")
    
    if stock.get("change_pct", 0) > 0:
        reasons.append("상승 모멘텀")
    elif stock.get("change_pct", 0) < 0:
        reasons.append("하락 후 반등 기대")
    
    if indicators.get("ma5") and indicators.get("ma20"):
        if indicators["ma5"] > indicators["ma20"]:
            reasons.append("골든크로스(MA5 > MA20)")
        else:
            reasons.append("단기 이평선 분석 필요")
    
    return "; ".join(reasons) if reasons else "거래량 급증, 관심 종목"
