"""애플리케이션 설정"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """앱 설정"""
    app_name: str = "주식 추천 서비스"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


def get_settings() -> Settings:
    return Settings()
