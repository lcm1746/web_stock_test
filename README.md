# 주식 추천 서비스

한국 상장 주식 대상 일일 리포트 서비스. 지표·차트·국내외 뉴스 기반 분석을 웹으로 제공합니다.

- **일일 단타 예상가**: 매수가, 목표매도가, 손절가, 지지/저항선 (피봇포인트 기반)
- **우량주(5만원↑) / 소형주(5만원↓)**: 구분하여 상승예측 TOP10 제시
- **30분마다 자동 갱신**: 실시간 데이터 반영
- **종목 클릭 시 근거·출처**: 기술지표, 피봇 전략, 관련 뉴스

## 기능

- **시장 현황**: KOSPI/KOSDAQ 실시간 지수 (Yahoo Finance / PyKRX)
- **추천 종목**: 거래량 상위 + 기술적 지표(RSI, 이동평균 등) 기반
- **차트**: 종목별 OHLCV 그래프
- **뉴스**: 국내(네이버 금융 등) / 해외(Reuters, Yahoo Finance) RSS

## 설치

```bash
cd /Volumes/Samsung_T5/web_stock_test
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 실행

```bash
python run.py
```

또는

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

브라우저에서 http://localhost:8000 접속

## API

| 엔드포인트 | 설명 |
|------------|------|
| `GET /` | 일일 리포트 대시보드 |
| `GET /api/reports` | 일일 리포트 JSON |
| `GET /api/stocks/index` | KOSPI/KOSDAQ 지수 |
| `GET /api/stocks/top?market=KOSPI` | 거래량 상위 종목 |
| `GET /api/stocks/{ticker}/chart` | 종목 차트 데이터 |
| `GET /api/news/domestic` | 국내 뉴스 |
| `GET /api/news/international` | 해외 뉴스 |

## 기술 스택

- **Backend**: FastAPI, PyKRX, yfinance, Pandas
- **Frontend**: Jinja2, Chart.js
- **뉴스**: feedparser (RSS)

## 주의사항

- PyKRX 데이터는 KRX/네이버 저작권 참고용
- 장 중/장 마감 후 데이터 반영 시점에 차이 있을 수 있음
- 투자 참고용이며 실제 투자 책임은 본인에게 있음
