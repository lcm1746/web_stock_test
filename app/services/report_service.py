"""
일일 리포트 생성 - Explainable Quant (소형주 일일 단타 특화)

- 수익 예측 확신도(Confidence Score) 0~100
- 설득적 근거: 기술지표 + 거래량패턴 + 뉴스감성 종합
- 정보 부족 시 명시
"""
from datetime import datetime
from app.services.stock_service import (
    get_index_overview,
    get_smallcap_candidates,
    get_stock_ohlcv,
    get_stock_indicators,
    get_intraday_targets,
    get_volume_pattern,
)
from app.services.news_service import get_domestic_news, get_international_news, analyze_sentiment


def generate_daily_report() -> dict:
    """소형주 일일 단타 추천 리포트 (확신도, 설득적 근거 포함)"""
    market_overview = get_index_overview()
    data_meta = market_overview.get("data_meta", {})

    domestic = get_domestic_news(limit=12)
    international = get_international_news(limit=10)
    all_news = (domestic or []) + (international or [])

    # 소형주 후보 (KOSDAQ 위주)
    kdaq_cands, _ = get_smallcap_candidates("KOSDAQ", limit=40)
    kospi_cands, _ = get_smallcap_candidates("KOSPI", limit=20)
    candidates = kdaq_cands + kospi_cands

    if not candidates:
        candidates = _fallback_candidates()

    recommended = []
    for s in candidates[:25]:  # 상위 25개만 상세 분석
        ticker = s.get("ticker")
        if not ticker:
            continue
        indicators = get_stock_indicators(ticker)
        targets = get_intraday_targets(ticker)
        vol_pattern = get_volume_pattern(ticker)
        if not targets or targets.get("expect_return_pct") is None:
            continue
        related_news = _get_related_news_with_sentiment(s.get("name", ""), all_news, limit=5)
        explainable = _build_explainable_reason(s, indicators, vol_pattern, related_news, targets)
        confidence = _compute_confidence(s, indicators, vol_pattern, related_news)
        recommended.append({
            **s,
            "segment": "smallcap",
            "indicators": indicators,
            "targets": targets,
            "volume_pattern": vol_pattern,
            "related_news": related_news,
            "expected_return_pct": targets.get("expect_return_pct", 0),
            "confidence_score": confidence,
            "explainable_reason": explainable,
            "reason": explainable,  # 하위 호환
        })

    recommended.sort(key=lambda x: (x.get("confidence_score", 0) * 0.5 + x.get("expected_return_pct", 0) * 0.5), reverse=True)
    recommended = recommended[:10]

    return {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "report_time": datetime.now().strftime("%H:%M"),
        "market_overview": market_overview,
        "data_meta": data_meta,
        "recommended_stocks": recommended,
        "domestic_news": domestic,
        "international_news": international,
    }


def _fallback_candidates() -> list:
    """mock 후보 (PyKRX 실패 시)"""
    return [
        {"ticker": "247540", "name": "에코플라스틱", "close": 12500, "change_pct": 2.1, "volume": 3500000, "market": "KOSDAQ"},
        {"ticker": "086520", "name": "에코프로", "close": 38500, "change_pct": -1.2, "volume": 2800000, "market": "KOSDAQ"},
        {"ticker": "322180", "name": "티로보틱스", "close": 4200, "change_pct": 5.2, "volume": 12000000, "market": "KOSDAQ"},
    ]


def _get_related_news_with_sentiment(name: str, news_list: list, limit: int = 5) -> list:
    """종목 관련 뉴스 + 감성 포함 (키워드 매칭 + 감성 분석)"""
    if not news_list or not name:
        return []
    key = str(name).replace(" ", "")
    candidates = []
    for n in news_list:
        title = str(n.get("title", "")).replace(" ", "")
        if key and key in title:
            candidates.append(n)
    if not candidates:
        return [{"title": n.get("title"), "link": n.get("link"), "source": n.get("source"), "sentiment": n.get("sentiment", "neutral"), "sentiment_score": n.get("sentiment_score", 0)} for n in news_list[:limit]]
    return [{"title": n.get("title"), "link": n.get("link"), "source": n.get("source"), "sentiment": n.get("sentiment", "neutral"), "sentiment_score": n.get("sentiment_score", 0)} for n in candidates[:limit]]


def _build_explainable_reason(stock: dict, indicators: dict, vol_pattern: dict, related_news: list, targets: dict) -> str:
    """
    "왜 이 소형주가 오늘 오를 것인지" 설득적 리포트
    [기술적 지표 + 거래량 패턴 + 뉴스 감성] 종합
    """
    parts = []

    # 1. 기술적 지표
    tech_parts = []
    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi < 30:
            tech_parts.append(f"RSI {rsi:.0f}(과매도) → 반등 기대")
        elif rsi < 45:
            tech_parts.append(f"RSI {rsi:.0f}(저평가 구간)")
        elif 55 <= rsi <= 70:
            tech_parts.append(f"RSI {rsi:.0f}(상승 모멘텀)")
        elif rsi > 70:
            tech_parts.append(f"RSI {rsi:.0f}(과매수·추세 상승)")
    ma5, ma20 = indicators.get("ma5"), indicators.get("ma20")
    if ma5 and ma20:
        if ma5 > ma20:
            tech_parts.append("단기 이평선 골든크로스")
        else:
            tech_parts.append("이평선 보합")
    if tech_parts:
        parts.append("【기술지표】 " + "; ".join(tech_parts))
    else:
        parts.append("【기술지표】 정보 부족")

    # 2. 거래량 패턴
    vp = vol_pattern.get("pattern", "")
    if vp and vp != "정보 부족":
        parts.append(f"【거래량】 {vp}")
    else:
        parts.append("【거래량】 정보 부족")

    # 3. 뉴스 감성
    if related_news:
        scores = [n.get("sentiment_score", 0) for n in related_news if n.get("sentiment_score") is not None]
        avg = sum(scores) / len(scores) if scores else 0
        if avg > 0.2:
            parts.append(f"【뉴스감성】 긍정({avg:.2f})")
        elif avg < -0.2:
            parts.append(f"【뉴스감성】 부정({avg:.2f}) - 주의")
        else:
            parts.append("【뉴스감성】 중립")
    else:
        parts.append("【뉴스감성】 관련 뉴스 없음")

    # 4. 손절 타입 (ATR 여부)
    sl_type = targets.get("stop_loss_type", "")
    if "ATR" in str(sl_type):
        parts.append("【손절】 ATR 기반 가변 손절 적용")
    else:
        parts.append("【손절】 고정 1% (정보 부족)")

    return " | ".join(parts)


def _compute_confidence(stock: dict, indicators: dict, vol_pattern: dict, related_news: list) -> int:
    """
    수익 예측 확신도 0~100
    - 기술지표 일치, 거래량 급증, 뉴스 긍정 → 가산
    - 정보 부족 → 감점
    """
    score = 50  # 기준
    if indicators.get("rsi") is not None:
        rsi = indicators["rsi"]
        if rsi < 30 or (40 <= rsi <= 60) or (55 <= rsi <= 70):
            score += 10
    else:
        score -= 5
    if indicators.get("ma5") and indicators.get("ma20"):
        if indicators["ma5"] > indicators["ma20"]:
            score += 10
    vol_ratio = vol_pattern.get("volume_ratio")
    if vol_ratio is not None and vol_ratio >= 1.5:
        score += 15
    elif vol_ratio is None:
        score -= 5
    if related_news:
        avg_sent = sum(n.get("sentiment_score", 0) for n in related_news) / len(related_news)
        if avg_sent > 0.2:
            score += 10
        elif avg_sent < -0.2:
            score -= 15
    return max(0, min(100, score))

