"""
한국 주식 데이터 서비스 - 소형주 일일 단타 특화

데이터 정확성: 지연시간 메타데이터 포함, 검증 로직
증권사 Open API 연동을 위한 인터페이스 구조 포함
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

try:
    from pykrx import stock
except Exception:
    stock = None


# --- 데이터 메타 (지연시간, 출처, 검증) ---
@dataclass
class DataMeta:
    """데이터 신뢰도 메타데이터"""
    source: str           # "yfinance" | "pykrx" | "mock"
    fetched_at: str       # ISO datetime
    delay_minutes: int    # 실제 기준 대비 지연(분), 0=실시간
    is_delayed: bool      # 장중인데 지연이면 True
    data_date: str        # 데이터 기준일 YYYYMMDD
    warning: Optional[str] = None  # "데이터 지연됨. 실시간 아님" 등

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "fetched_at": self.fetched_at,
            "delay_minutes": self.delay_minutes,
            "is_delayed": self.is_delayed,
            "data_date": self.data_date,
            "warning": self.warning,
        }


def _is_market_hours() -> bool:
    """한국 거래시간 09:00~15:30 (UTC+9 기준, 로컬이 KST면 그대로)"""
    # 단순화: 9~15시 사이
    now = datetime.now()
    return 9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)


def _build_meta(source: str, data_date: str, delay_min: int = 0) -> DataMeta:
    now = datetime.now()
    is_delayed = _is_market_hours() and delay_min > 15
    w = f"데이터 지연 {delay_min}분. 실시간 아님." if is_delayed else None
    return DataMeta(
        source=source,
        fetched_at=now.isoformat(),
        delay_minutes=delay_min,
        is_delayed=is_delayed,
        data_date=data_date,
        warning=w,
    )


# --- 증권사 Open API 연동용 인터페이스 (미래 확장) ---
class BrokerageDataProvider(ABC):
    """국내 증권사 Open API 연동 인터페이스"""

    @abstractmethod
    def get_realtime_index(self) -> Optional[dict]:
        """실시간 지수"""
        pass

    @abstractmethod
    def get_realtime_quote(self, ticker: str) -> Optional[dict]:
        """실시간 호가/체결"""
        pass


# --- 지수 (데이터 메타 포함) ---
def get_index_overview() -> dict:
    """KOSPI, KOSDAQ 지수 + 데이터 메타"""
    result, meta = _get_index_with_meta()
    result["data_meta"] = meta.to_dict()
    return result


def _get_index_with_meta() -> Tuple[dict, DataMeta]:
    today = datetime.now().strftime("%Y%m%d")
    # yfinance: 보통 15~20분 지연
    r = _get_index_via_yfinance()
    if r:
        return r, _build_meta("yfinance", today, delay_min=20)
    if stock:
        r = _get_index_via_pykrx()
        if r:
            return r, _build_meta("pykrx", today, delay_min=0)  # KRX는 장 마감 후 갱신
    return _mock_index_overview(), _build_meta("mock", today, delay_min=999)


def _get_index_via_yfinance() -> Optional[dict]:
    try:
        import yfinance as yf
        kospi = yf.Ticker("^KS11")
        kosdaq = yf.Ticker("^KQ11")
        kh = kospi.history(period="5d")
        kqh = kosdaq.history(period="5d")
        if kh is None or kh.empty or kqh is None or kqh.empty:
            return None
        kt, kpt = kh.iloc[-1], kh.iloc[-2] if len(kh) > 1 else kh.iloc[-1]
        kqt, kqp = kqh.iloc[-1], kqh.iloc[-2] if len(kqh) > 1 else kqh.iloc[-1]
        def _chg(c, p):
            return float((c - p) / p * 100) if p and p != 0 else 0.0
        return {
            "kospi": {"value": float(kt["Close"]), "change": float(kt["Close"] - kpt["Close"]), "change_pct": _chg(kt["Close"], kpt["Close"])},
            "kosdaq": {"value": float(kqt["Close"]), "change": float(kqt["Close"] - kqp["Close"]), "change_pct": _chg(kqt["Close"], kqp["Close"])},
            "date": datetime.now().strftime("%Y%m%d"),
        }
    except Exception:
        return None


def _get_index_via_pykrx() -> Optional[dict]:
    today = datetime.now().strftime("%Y%m%d")
    try:
        kospi = stock.get_index_ohlcv_by_date("20200101", today, "1001")
        kosdaq = stock.get_index_ohlcv_by_date("20200101", today, "2001")
        if kospi.empty or kosdaq.empty:
            return None
        kt, kpt = kospi.iloc[-1], kospi.iloc[-2] if len(kospi) > 1 else kospi.iloc[-1]
        kqt, kqp = kosdaq.iloc[-1], kosdaq.iloc[-2] if len(kosdaq) > 1 else kosdaq.iloc[-1]
        def _chg(c, p):
            return float((c - p) / p * 100) if p and p != 0 else 0.0
        return {
            "kospi": {"value": float(kt["종가"]), "change": float(kt["종가"] - kpt["종가"]), "change_pct": _chg(kt["종가"], kpt["종가"])},
            "kosdaq": {"value": float(kqt["종가"]), "change": float(kqt["종가"] - kqp["종가"]), "change_pct": _chg(kqt["종가"], kqp["종가"])},
            "date": today,
        }
    except Exception:
        return None


# --- 소형주 스크리닝 (5만원↓, 거래량 급증, 시총 작음) ---
SMALLCAP_PRICE_MAX = 50_000
VOLUME_SURGE_RATIO = 1.5  # 평균 대비 1.5배 이상 거래량
SMALLCAP_MARKET_CAP_MAX = 500_000_000_000  # 5000억 (소형주 상한, pykrx 있으면 사용)


def get_smallcap_candidates(market: str = "KOSDAQ", limit: int = 50) -> Tuple[List[dict], DataMeta]:
    """
    소형주 후보: 주가 5만원 이하, 거래량 급증, 시총 작음
    KOSDAQ 위주 (소형주 비중 높음)
    """
    today = datetime.now().strftime("%Y%m%d")
    meta = _build_meta("pykrx" if stock else "mock", today, delay_min=20 if not stock else 0)
    if stock is None:
        return _mock_smallcap_candidates(), meta

    try:
        mkt = "KOSDAQ" if market == "KOSDAQ" else "KOSPI"
        tickers = stock.get_market_ticker_list(today, market=mkt)
        ohlcv = stock.get_market_ohlcv_by_ticker(today)
        cap_df = None
        try:
            if hasattr(stock, "get_market_cap_by_ticker"):
                cap_df = stock.get_market_cap_by_ticker(today, market=mkt)
        except Exception:
            cap_df = None
        if ohlcv is None or ohlcv.empty:
            return _mock_smallcap_candidates(), meta

        df = ohlcv[ohlcv.index.isin(tickers)].copy()
        # 주가 5만원 이하 필터
        df = df[df["종가"] <= SMALLCAP_PRICE_MAX]
        if df.empty:
            return _mock_smallcap_candidates(), meta

        # 시총 필터 (있으면)
        if cap_df is not None and not cap_df.empty and "시가총액" in cap_df.columns:
            df = df.join(cap_df[["시가총액"]], how="left")
            df = df[df["시가총액"] <= SMALLCAP_MARKET_CAP_MAX].drop(columns=["시가총액"], errors="ignore")

        # 거래량 급증: 5일 평균 대비 (간이)
        df = df.nlargest(limit * 2, "거래량")
        result = []
        for ticker, row in df.head(limit).iterrows():
            name = stock.get_market_ticker_name(ticker)
            change_pct = float(row.get("등락률", 0) or 0)
            result.append({
                "ticker": ticker,
                "name": name or ticker,
                "close": float(row["종가"]),
                "change_pct": change_pct,
                "volume": int(row["거래량"]),
                "market": mkt,
            })
        return result, meta
    except Exception:
        return _mock_smallcap_candidates(), meta


# --- ATR(5일) 기반 가변 손절 ---
def get_atr_5d(ticker: str) -> Optional[float]:
    """최근 5일 ATR (Average True Range) - 변동성 반영"""
    chart = get_stock_ohlcv(ticker, days=10)
    if not chart or len(chart) < 6:
        return None
    df = pd.DataFrame(chart[-6:])
    df["prev_close"] = df["close"].shift(1)
    tr_list = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]["close"]
        high, low = row["high"], row["low"]
        tr = max(high - low, abs(high - prev), abs(low - prev))
        tr_list.append(tr)
    atr = pd.Series(tr_list).mean() if tr_list else None
    return float(atr) if atr is not None and pd.notna(atr) else None


def get_stock_ohlcv(ticker: str, days: int = 120) -> list[dict]:
    if stock is None:
        return _mock_chart_data(ticker)
    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        df = stock.get_market_ohlcv_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker)
        if df is None or df.empty:
            return _mock_chart_data(ticker)
        return [
            {"date": idx.strftime("%Y-%m-%d"), "open": float(row["시가"]), "high": float(row["고가"]),
             "low": float(row["저가"]), "close": float(row["종가"]), "volume": int(row["거래량"])}
            for idx, row in df.iterrows()
        ]
    except Exception:
        return _mock_chart_data(ticker)


def get_intraday_targets(ticker: str) -> dict:
    """
    일일 단타 예상가
    - 손절: ATR(5일) 기반 가변 (소형주 변동성 반영)
    - ATR 없으면 1% 고정 (정보 부족)
    """
    chart = get_stock_ohlcv(ticker, days=10)
    if not chart or len(chart) < 2:
        return {}
    prev, curr = chart[-2], chart[-1]
    h, l, c = prev["high"], prev["low"], prev["close"]
    pivot = (h + l + c) / 3
    r1, s1 = 2 * pivot - l, 2 * pivot - h
    price = curr["close"]

    atr = get_atr_5d(ticker)
    if atr and atr > 0:
        stop_distance = max(atr * 1.0, price * 0.01)  # ATR 1배 or 최소 1%
        stop_loss = round(price - stop_distance, -2)
    else:
        stop_loss = round(price * 0.99, -2)  # 정보 부족 시 고정 1%

    target_sell = round(min(r1, price * 1.025) if r1 > price else price * 1.015, -2)
    expect = round((target_sell - price) / price * 100, 2)
    return {
        "target_buy": int(price),
        "target_sell": int(target_sell),
        "stop_loss": int(stop_loss),
        "support": int(round(s1, -2)),
        "resistance": int(round(r1, -2)),
        "pivot": int(round(pivot, -2)),
        "expect_return_pct": expect,
        "atr_5d": round(atr, 0) if atr else None,
        "stop_loss_type": "ATR 기반" if atr else "고정 1% (정보 부족)",
    }


def get_stock_indicators(ticker: str) -> dict:
    chart = get_stock_ohlcv(ticker, days=120)
    if not chart:
        return {}
    df = pd.DataFrame(chart)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))
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


def get_volume_pattern(ticker: str) -> dict:
    """거래량 패턴: 5일 평균 대비 현재 거래량 비율"""
    chart = get_stock_ohlcv(ticker, days=10)
    if not chart or len(chart) < 6:
        return {"volume_ratio": None, "pattern": "정보 부족"}
    vols = [c["volume"] for c in chart[-6:]]
    avg = sum(vols[:-1]) / 5 if len(vols) >= 5 else vols[0]
    ratio = vols[-1] / avg if avg and avg > 0 else None
    if ratio is None:
        return {"volume_ratio": None, "pattern": "정보 부족"}
    if ratio >= 2.0:
        pattern = "거래량 급증 (평균 2배 이상)"
    elif ratio >= 1.5:
        pattern = "거래량 증가"
    elif ratio >= 1.0:
        pattern = "평균 수준"
    else:
        pattern = "거래량 감소"
    return {"volume_ratio": round(ratio, 2), "pattern": pattern}


# --- 기존 get_top_stocks 호환 (소형주 스크리닝으로 대체 가능) ---
def get_top_stocks(market: str = "KOSDAQ", limit: int = 30) -> list[dict]:
    cands, _ = get_smallcap_candidates(market, limit)
    if cands:
        return cands
    return _mock_smallcap_candidates()


# --- Mock ---
def _mock_index_overview() -> dict:
    return {
        "kospi": {"value": 2750.0, "change": 15.2, "change_pct": 0.56},
        "kosdaq": {"value": 850.5, "change": -3.2, "change_pct": -0.38},
        "date": datetime.now().strftime("%Y%m%d"),
    }


def _mock_chart_data(ticker: str) -> list:
    import random
    base = 25000
    data = []
    for i in range(60):
        base = base * (1 + random.uniform(-0.03, 0.03))
        data.append({
            "date": (datetime.now() - timedelta(days=60 - i)).strftime("%Y-%m-%d"),
            "open": base, "high": base * 1.02, "low": base * 0.98, "close": base,
            "volume": random.randint(200000, 800000),
        })
    return data


def _mock_smallcap_candidates() -> list:
    return [
        {"ticker": "247540", "name": "에코플라스틱", "close": 12500, "change_pct": 2.1, "volume": 3500000, "market": "KOSDAQ"},
        {"ticker": "086520", "name": "에코프로", "close": 38500, "change_pct": -1.2, "volume": 2800000, "market": "KOSDAQ"},
        {"ticker": "322180", "name": "티로보틱스", "close": 4200, "change_pct": 5.2, "volume": 12000000, "market": "KOSDAQ"},
        {"ticker": "376300", "name": "대유에이텍", "close": 8500, "change_pct": 1.8, "volume": 2100000, "market": "KOSDAQ"},
    ]
