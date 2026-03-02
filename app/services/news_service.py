"""국내/해외 뉴스 수집 서비스 (최신순 정렬, 감성 분석)"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import feedparser
from time import mktime

# 긍정/부정 키워드 (주식·경제 맥락, 한국어 위주)
POSITIVE_KEYWORDS = [
    "상승", "호재", "강세", "반등", "급등", "신고가",
    "수익", "개선", "성장", "흑자", "증가", "확대", "긍정",
    "돌파", "회복", "뚫고", "강력", "호황",
]
NEGATIVE_KEYWORDS = [
    "하락", "악재", "약세", "급락", "폭락", "신저가", "적자", "감소",
    "위험", "우려", "혼조", "부진", "악화", "축소", "부정",
]


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    제목/요약 텍스트 감성 분석 (키워드 기반)
    Returns: {"sentiment": "positive"|"negative"|"neutral", "score": -1~1}
    """
    if not text or not isinstance(text, str):
        return {"sentiment": "neutral", "score": 0.0}
    t = text.replace(" ", "")
    pos_cnt = sum(1 for k in POSITIVE_KEYWORDS if k in t)
    neg_cnt = sum(1 for k in NEGATIVE_KEYWORDS if k in t)
    total = pos_cnt + neg_cnt
    if total == 0:
        return {"sentiment": "neutral", "score": 0.0}
    score = (pos_cnt - neg_cnt) / max(total, 1)
    score = max(-1.0, min(1.0, score))
    sentiment = "positive" if score > 0.15 else ("negative" if score < -0.15 else "neutral")
    return {"sentiment": sentiment, "score": round(score, 2)}
import requests
from bs4 import BeautifulSoup

def get_domestic_news(limit: int = 10) -> list[dict]:
    """국내 경제/주식 뉴스 (RSS)"""
    sources = [
        ("https://news.google.com/rss/search?q=한국+주식+경제&hl=ko&gl=KR&ceid=KR:ko", "구글 뉴스"),
        ("https://finance.naver.com/news/news_rss.php?mode=main", "네이버 금융"),
    ]
    
    news_list = []
    seen_titles = set()
    
    for url, source_name in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                link = entry.get("link", "")
                published = entry.get("published", "")
                summary = entry.get("summary", "")[:200] if entry.get("summary") else None
                ts = 0
                try:
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        ts = mktime(entry.published_parsed)
                except Exception:
                    pass
                sent = analyze_sentiment(title + " " + (summary or ""))
                news_list.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "published": published,
                    "published_ts": ts,
                    "summary": summary,
                    "type": "domestic",
                    "sentiment": sent["sentiment"],
                    "sentiment_score": sent["score"],
                })
                if len(news_list) >= limit * 2:
                    break
        except Exception:
            continue
    news_list.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    if not news_list:
        return _mock_domestic_news()
    return news_list[:limit]


def get_international_news(limit: int = 10) -> list[dict]:
    """해외 경제/주식 뉴스"""
    sources = [
        ("https://feeds.reuters.com/reuters/businessNews", "Reuters"),
        ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=yhoo&region=US&lang=en-US", "Yahoo Finance"),
    ]
    
    news_list = []
    seen_titles = set()
    
    for url, source_name in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                link = entry.get("link", "")
                published = entry.get("published", "")
                summary = entry.get("summary", "")[:300] if entry.get("summary") else None
                ts = 0
                try:
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        ts = mktime(entry.published_parsed)
                except Exception:
                    pass
                sent = analyze_sentiment(title + " " + (summary or ""))
                news_list.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "published": published,
                    "published_ts": ts,
                    "summary": summary,
                    "type": "international",
                    "sentiment": sent["sentiment"],
                    "sentiment_score": sent["score"],
                })
                if len(news_list) >= limit * 2:
                    break
        except Exception:
            continue
    news_list.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    if not news_list:
        return _mock_international_news()
    return news_list[:limit]


def _mock_domestic_news() -> list:
    items = [
        {"title": "[금융] KOSPI, 2,750선 회복... 반도체株 강세", "link": "#", "source": "국내", "published": "", "summary": None, "type": "domestic"},
        {"title": "미국 금리 동결 기대감에 국내 주식시장 상승", "link": "#", "source": "국내", "published": "", "summary": None, "type": "domestic"},
    ]
    for n in items:
        n["sentiment"] = analyze_sentiment(n["title"]).get("sentiment", "neutral")
        n["sentiment_score"] = analyze_sentiment(n["title"]).get("score", 0)
    return items


def _mock_international_news() -> list:
    items = [
        {"title": "Fed holds rates steady, signals potential cuts in 2025", "link": "#", "source": "Reuters", "published": "", "summary": None, "type": "international"},
        {"title": "Oil prices rise amid supply concerns", "link": "#", "source": "Yahoo Finance", "published": "", "summary": None, "type": "international"},
    ]
    for n in items:
        n["sentiment"] = "neutral"
        n["sentiment_score"] = 0
    return items
