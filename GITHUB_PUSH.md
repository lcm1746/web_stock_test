# GitHub 업로드 방법

## 1. GitHub에서 새 저장소 생성

1. https://github.com/new 접속
2. **Repository name**: `web_stock_test` (또는 원하는 이름)
3. **Public** 선택
4. **Create repository** 클릭 (README, .gitignore 추가하지 않기)

## 2. 원격 저장소 연결 (저장소 이름이 다를 경우)

```bash
cd /Volumes/Samsung_T5/web_stock_test

# 원격 URL 변경 (본인 GitHub 아이디로)
git remote set-url origin https://github.com/YOUR_USERNAME/web_stock_test.git
```

## 3. 푸시

```bash
git push -u origin main
```

- **HTTPS**: GitHub 아이디/비밀번호 또는 Personal Access Token 입력
- **SSH** (권장): `git remote set-url origin git@github.com:YOUR_USERNAME/web_stock_test.git` 후 푸시

## 현재 상태

- ✅ Git 초기화 완료
- ✅ 커밋 완료 (20 files)
- ✅ origin: https://github.com/lcm1746/web_stock_test.git
