"""주식 추천 서비스 - FastAPI 메인 앱"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.config import get_settings
from app.api import reports, stocks, news

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(
    title=get_settings().app_name,
    description="한국 상장 주식 일일 추천 리포트 - 지표, 차트, 뉴스 기반 분석",
    version="1.0.0",
)

# 정적 파일 및 템플릿
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# API 라우터 등록
app.include_router(reports.router, prefix="/api/reports", tags=["리포트"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["주식"])
app.include_router(news.router, prefix="/api/news", tags=["뉴스"])


@app.get("/")
async def index(request: Request):
    """일일 리포트 대시보드"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health")
async def health():
    """헬스체크"""
    return {"status": "ok"}
