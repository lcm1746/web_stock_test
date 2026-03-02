"""일일 리포트 API"""
from fastapi import APIRouter
from app.services.report_service import generate_daily_report

router = APIRouter()


@router.get("")
async def get_daily_report():
    """일일 추천 리포트 조회"""
    return generate_daily_report()
