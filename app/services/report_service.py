"""일일 리포트 생성 서비스"""
from datetime import datetime
from app.services.stock_service import (
    get_index_overview,
    get_top_stocks,
    get_stock_ohlcv,
    get_stock_indicators,
    get_intraday_targets,
)
from app.services.news_service import get_domestic_news, get_international_news


def generate_daily_report() -> dict:
    """일일 추천 리포트 생성 (상승 예측 TOP10: 우량주 + 소형주)"""
    market_overview = get_index_overview()

    # 후보 풀: 거래량 상위 우량주/소형주
    kospi_stocks = get_top_stocks("KOSPI", limit=30)
    kosdaq_stocks = get_top_stocks("KOSDAQ", limit=20)

    domestic = get_domestic_news(limit=12)
    international = get_international_news(limit=10)
    all_news = (domestic or []) + (international or [])

    # 추천 종목 (거래량 상위 + 지표 기반 + 일일 단타 예상가)
    scored = []
    for s in kospi_stocks + kosdaq_stocks:
        ticker = s.get("ticker")
        if not ticker:
            continue

        indicators = get_stock_indicators(ticker)
        targets = get_intraday_targets(ticker)
        expect = targets.get("expect_return_pct") if targets else None

        # 기대 수익률이 없는 경우는 제외
        if expect is None:
            continue

        price = s.get("close") or 0
        segment = "smallcap" if price and price < 50000 else "bluechip"
        related_news = _get_related_news(s.get("name", ""), all_news, limit=3)

        scored.append(
            {
                **s,
                "segment": segment,
                "indicators": indicators,
                "targets": targets,
                "expected_return_pct": expect,
                "related_news": related_news,
                "reason": _get_reason(s, indicators),
            }
        )

    # 상승예측 TOP10 (기대 수익률 기준 내림차순)
    scored.sort(
        key=lambda x: x.get("expected_return_pct") or 0,
        reverse=True,
    )
    recommended = scored[:10]

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


def _get_related_news(name: str, news_list: list, limit: int = 3) -> list:
    """종목명 기반 관련 뉴스 추출 (없으면 상단 뉴스 사용)"""
    if not news_list or not name:
        return []

    key = str(name).replace(" ", "")
    candidates = []
    for n in news_list:
        title = str(n.get("title", "")).replace(" ", "")
        if key and key in title:
            candidates.append(n)

    if not candidates:
        return news_list[:limit]

    return candidates[:limit]
