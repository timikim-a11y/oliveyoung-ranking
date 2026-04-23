# 🫒 올리브영 랭킹 트래커

올리브영 베스트 랭킹을 자동으로 수집하여 GitHub에 저장합니다.

## 📁 파일 구조

```
oliveyoung-ranking/
├── .github/
│   └── workflows/
│       └── scrape.yml          ← 자동 실행 설정 (하루 3회)
├── data/
│   ├── 2025-04-23_0900.json    ← 날짜별 수집 데이터
│   ├── 2025-04-23_1500.json
│   └── latest.json             ← 가장 최근 데이터
├── oliveyoung_scraper.py       ← 크롤링 코드
└── README.md                   ← 이 파일
```

## ✅ 설치 방법 (한 번만 하면 끝)

아래 10단계를 따라하면 매일 자동으로 데이터가 쌓입니다.
