"""국내/해외 뉴스 수집 서비스"""
from datetime import datetime
from typing import Optional
import feedparser
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
                news_list.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "published": published,
                    "summary": summary,
                    "type": "domestic",
                })
                if len(news_list) >= limit:
                    break
        except Exception:
            continue
        if len(news_list) >= limit:
            break
    
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
                news_list.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "published": published,
                    "summary": summary,
                    "type": "international",
                })
                if len(news_list) >= limit:
                    break
        except Exception:
            continue
        if len(news_list) >= limit:
            break
    
    if not news_list:
        return _mock_international_news()
    
    return news_list[:limit]


def _mock_domestic_news() -> list:
    return [
        {"title": "[금융] KOSPI, 2,750선 회복... 반도체株 강세", "link": "#", "source": "국내", "published": "", "summary": None, "type": "domestic"},
        {"title": "미국 금리 동결 기대감에 국내 주식시장 상승", "link": "#", "source": "국내", "published": "", "summary": None, "type": "domestic"},
    ]


def _mock_international_news() -> list:
    return [
        {"title": "Fed holds rates steady, signals potential cuts in 2025", "link": "#", "source": "Reuters", "published": "", "summary": None, "type": "international"},
        {"title": "Oil prices rise amid supply concerns", "link": "#", "source": "Yahoo Finance", "published": "", "summary": None, "type": "international"},
    ]
