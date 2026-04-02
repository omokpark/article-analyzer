# article-analyzer
싱크탱크 MVP — 기사 URL을 입력하면 본문을 추출하고 AI로 분석해주는 웹앱

## 현재 구조

```
article-analyzer/
├── app.py              # Flask 라우트 (/ , /analyze)
├── extractor.py        # 기사 본문 추출
├── analyzer.py         # Gemini 기사 분석
├── templates/
│   └── index.html      # UI (URL 입력 + 결과 표시)
├── requirements.txt
└── .env.example
```

## 기능

### 본문 추출 (extractor.py)
- 2단계 fallback 구조
  1. trafilatura — 정적 HTML 사이트
  2. Jina Reader API (`r.jina.ai`) — JS 렌더링 사이트 (MSN 등)
- 함수: `extract_article(url)` → `{"title", "body", "url"}` 또는 `None`

### 기사 분석 (analyzer.py)
- Gemini 2.0 Flash 사용
- 결과 구조:
  - `summary`: 한 문장 핵심 요약
  - `points`: 핵심 포인트 3개
  - `tags`: 태그 3개 (나중에 모아보기용)
- 함수: `analyze_article(title, body)` → dict 또는 `None`

## 실행 방법

```bash
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
# .env에 GEMINI_API_KEY 입력

python app.py
# → http://127.0.0.1:5000
```

## 다음 단계 (집에서 이어서)

- [ ] Google AI Studio에서 Gemini API 키 발급 → `.env`에 입력
- [ ] 서버 실행 후 Gemini 분석 기능 테스트
- [ ] 분석 결과 UI 확인 및 개선
- [ ] 이후 고려할 것: 기사 저장/히스토리, 태그별 모아보기
