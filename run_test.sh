#!/bin/bash
# 주식 추천 서비스 테스트 실행
cd "$(dirname "$0")"
export VIRTUAL_ENV=
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"
export PYTHONPATH="$(pwd)/packages:$(pwd)"
export MPLCONFIGDIR="/tmp/mpl_$$"

/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
