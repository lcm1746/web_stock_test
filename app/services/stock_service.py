"""한국 주식 데이터 서비스 - PyKRX 기반"""
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

try:
    from pykrx import stock
except Exception:
    stock = None  # pykrx 미설치 또는 matplotlib 등 로드 실패 시 mock 사용


def get_index_overview() -> dict:
    """KOSPI, KOSDAQ 지수 현황 (yfinance 실시간 우선, pykrx 폴백)"""
    result = _get_index_via_yfinance()
    if result:
        return result
    if stock is not None:
        result = _get_index_via_pykrx()
        if result:
            return result
    return _mock_index_overview()


def _get_index_via_yfinance() -> Optional[dict]:
    """Yahoo Finance로 KOSPI(^KS11), KOSDAQ(^KQ11) 실시간 조회"""
    try:
        import yfinance as yf
        kospi = yf.Ticker("^KS11")
        kosdaq = yf.Ticker("^KQ11")
        kospi_hist = kospi.history(period="5d")
        kosdaq_hist = kosdaq.history(period="5d")
        if kospi_hist is None or kospi_hist.empty or kosdaq_hist is None or kosdaq_hist.empty:
            return None
        kospi_today = kospi_hist.iloc[-1]
        kosdaq_today = kosdaq_hist.iloc[-1]
        kospi_prev = kospi_hist.iloc[-2] if len(kospi_hist) > 1 else kospi_today
        kosdaq_prev = kosdaq_hist.iloc[-2] if len(kosdaq_hist) > 1 else kosdaq_today

        def _chg(cur, prev):
            if prev and prev != 0:
                return float((cur - prev) / prev * 100)
            return 0.0

        return {
            "kospi": {
                "value": float(kospi_today["Close"]),
                "change": float(kospi_today["Close"] - kospi_prev["Close"]),
                "change_pct": _chg(kospi_today["Close"], kospi_prev["Close"]),
            },
            "kosdaq": {
                "value": float(kosdaq_today["Close"]),
                "change": float(kosdaq_today["Close"] - kosdaq_prev["Close"]),
                "change_pct": _chg(kosdaq_today["Close"], kosdaq_prev["Close"]),
            },
            "date": datetime.now().strftime("%Y%m%d"),
        }
    except Exception:
        return None


def _get_index_via_pykrx() -> Optional[dict]:
    """PyKRX로 지수 조회"""
    today = datetime.now().strftime("%Y%m%d")
    try:
        kospi = stock.get_index_ohlcv_by_date("20200101", today, "1001")
        kosdaq = stock.get_index_ohlcv_by_date("20200101", today, "2001")
        kospi_today = kospi.iloc[-1] if len(kospi) > 0 else None
        kosdaq_today = kosdaq.iloc[-1] if len(kosdaq) > 0 else None
        kospi_prev = kospi.iloc[-2] if len(kospi) > 1 else kospi_today
        kosdaq_prev = kosdaq.iloc[-2] if len(kosdaq) > 1 else kosdaq_today
        if kospi_today is None or kosdaq_today is None:
            return None
        return {
            "kospi": {
                "value": float(kospi_today["종가"]),
                "change": float(kospi_today["종가"] - kospi_prev["종가"]),
                "change_pct": float((kospi_today["종가"] - kospi_prev["종가"]) / kospi_prev["종가"] * 100) if kospi_prev["종가"] else 0,
            },
            "kosdaq": {
                "value": float(kosdaq_today["종가"]),
                "change": float(kosdaq_today["종가"] - kosdaq_prev["종가"]),
                "change_pct": float((kosdaq_today["종가"] - kosdaq_prev["종가"]) / kosdaq_prev["종가"] * 100) if kosdaq_prev["종가"] else 0,
            },
            "date": today,
        }
    except Exception:
        return None


def get_stock_ohlcv(ticker: str, days: int = 120) -> list[dict]:
    """종목 OHLCV 차트 데이터"""
    if stock is None:
        return _mock_chart_data(ticker)
    
    end = datetime.now()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")
    
    try:
        df = stock.get_market_ohlcv_by_date(start_str, end_str, ticker)
        if df is None or df.empty:
            return _mock_chart_data(ticker)
        
        return [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(row["시가"]),
                "high": float(row["고가"]),
                "low": float(row["저가"]),
                "close": float(row["종가"]),
                "volume": int(row["거래량"]),
            }
            for idx, row in df.iterrows()
        ]
    except Exception:
        return _mock_chart_data(ticker)


def get_intraday_targets(ticker: str) -> dict:
    """
    일일 단타용 예상가 (피봇포인트 기반)
    - 매수가: 1차 지지 근처 또는 현재가
    - 목표매도가: 1차 저항 (R1) 또는 +1~2% 목표
    - 손절가: 지지선 이탈 시
    """
    chart = get_stock_ohlcv(ticker, days=10)
    if not chart or len(chart) < 2:
        return {}
    
    prev = chart[-2]  # 전일
    curr = chart[-1]  # 당일(또는 최신)
    h, l, c = prev["high"], prev["low"], prev["close"]
    
    # 피봇포인트 (표준)
    pivot = (h + l + c) / 3
    r1 = 2 * pivot - l
    r2 = pivot + (h - l)
    s1 = 2 * pivot - h
    s2 = pivot - (h - l)
    
    current_price = curr["close"]
    
    # 일일 단타: 목표 1~2% 수익, 손절 1~1.5%
    target_pct = 1.5  # 목표 상승률 %
    stop_pct = 1.0    # 손절률 %
    
    target_sell = round(current_price * (1 + target_pct / 100), -2)
    stop_loss = round(current_price * (1 - stop_pct / 100), -2)
    
    # 매수가: 현재가 또는 지지 부근 (저평가 시)
    target_buy = current_price
    
    # R1이 현재가 대비 너무 가깝거나 멀면 보정
    if r1 > current_price and r1 < current_price * 1.03:
        target_sell = round(r1, -2)
    elif r1 > current_price * 1.03:
        target_sell = round(min(r1, current_price * 1.025), -2)
    
    if s1 > 0 and s1 < current_price:
        stop_loss = round(max(s1 * 0.995, stop_loss), -2)
    
    # 예상 수익률
    expect_return = round((target_sell - target_buy) / target_buy * 100, 2)
    
    return {
        "target_buy": int(target_buy),
        "target_sell": int(target_sell),
        "stop_loss": int(stop_loss),
        "support": int(round(s1, -2)),
        "resistance": int(round(r1, -2)),
        "pivot": int(round(pivot, -2)),
        "expect_return_pct": expect_return,
        "prev_high": int(h),
        "prev_low": int(l),
    }


def get_stock_indicators(ticker: str) -> dict:
    """기술적 지표 (이동평균, RSI 등)"""
    chart = get_stock_ohlcv(ticker, days=120)
    if not chart:
        return {}
    
    df = pd.DataFrame(chart)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    
    # 이동평균
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()
    
    # RSI (14일)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))
    
    # 볼린저 밴드 (20일, 2σ)
    df["bb_mid"] = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std
    
    last = df.iloc[-1]
    return {
        "ma5": float(last["ma5"]) if pd.notna(last["ma5"]) else None,
        "ma20": float(last["ma20"]) if pd.notna(last["ma20"]) else None,
        "ma60": float(last["ma60"]) if pd.notna(last["ma60"]) else None,
        "rsi": float(last["rsi"]) if pd.notna(last["rsi"]) else None,
        "bollinger_upper": float(last["bb_upper"]) if pd.notna(last["bb_upper"]) else None,
        "bollinger_lower": float(last["bb_lower"]) if pd.notna(last["bb_lower"]) else None,
    }


def get_top_stocks(market: str = "KOSPI", limit: int = 10) -> list[dict]:
    """거래량 상위 종목 (추천 후보)"""
    if stock is None:
        return _mock_top_stocks()
    
    today = datetime.now().strftime("%Y%m%d")
    market_map = {"KOSPI": "KOSPI", "KOSDAQ": "KOSDAQ"}
    mkt = market_map.get(market, "KOSPI")
    
    try:
        tickers = stock.get_market_ticker_list(today, market=mkt)
        df = stock.get_market_ohlcv_by_ticker(today)
        if df is None or df.empty or not tickers:
            return _mock_top_stocks()
        
        df = df[df.index.isin(tickers)].nlargest(limit, "거래량")
        result = []
        for ticker, row in df.iterrows():
            name = stock.get_market_ticker_name(ticker)
            change_pct = float(row.get("등락률", 0) or 0)
            result.append({
                "ticker": ticker,
                "name": name or ticker,
                "close": float(row["종가"]),
                "change": change_pct,
                "change_pct": change_pct,
                "volume": int(row["거래량"]),
                "market": market,
            })
        return result
    except Exception:
        return _mock_top_stocks()


def _mock_index_overview() -> dict:
    return {
        "kospi": {"value": 2750.0, "change": 15.2, "change_pct": 0.56},
        "kosdaq": {"value": 850.5, "change": -3.2, "change_pct": -0.38},
        "date": datetime.now().strftime("%Y%m%d"),
    }


def _mock_chart_data(ticker: str) -> list:
    import random
    base = 50000
    data = []
    for i in range(60):
        base = base * (1 + random.uniform(-0.02, 0.02))
        data.append({
            "date": (datetime.now() - timedelta(days=60-i)).strftime("%Y-%m-%d"),
            "open": base,
            "high": base * 1.01,
            "low": base * 0.99,
            "close": base,
            "volume": random.randint(100000, 500000),
        })
    return data


def _mock_top_stocks() -> list:
    """우량주(5만↑) + 소형주(5만↓) 혼합 mock"""
    return [
        {"ticker": "005930", "name": "삼성전자", "close": 72000, "change": 1.2, "change_pct": 1.2, "volume": 15000000, "market": "KOSPI"},
        {"ticker": "000660", "name": "SK하이닉스", "close": 185000, "change": -0.5, "change_pct": -0.5, "volume": 8000000, "market": "KOSPI"},
        {"ticker": "035420", "name": "NAVER", "close": 195000, "change": 0.8, "change_pct": 0.8, "volume": 2000000, "market": "KOSPI"},
        {"ticker": "247540", "name": "에코플라스틱", "close": 12500, "change": 2.1, "change_pct": 2.1, "volume": 3500000, "market": "KOSDAQ"},
        {"ticker": "086520", "name": "에코프로", "close": 38500, "change": -1.2, "change_pct": -1.2, "volume": 2800000, "market": "KOSDAQ"},
    ]
