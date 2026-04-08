import os
import json
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

_api_key = os.environ.get("GEMINI_API_KEY")
if not _api_key:
    raise RuntimeError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

_client = genai.Client(api_key=_api_key)

_PROMPT = """아래 기사를 읽고 다음 형식의 JSON으로만 응답하세요. 설명이나 마크다운 코드블록 없이 JSON만 출력하세요.

{{
  "summary": "한 문장으로 기사의 핵심을 요약",
  "points": [
    "핵심 포인트 1",
    "핵심 포인트 2",
    "핵심 포인트 3"
  ],
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
}}

태그 작성 규칙:
- 단순 이름/명사 나열 금지 (예: "하정우", "서울" 같은 단독 고유명사 X)
- 기사의 핵심 이슈나 의미를 담은 짧은 구문 사용 (예: "AI수석영입논란", "보궐선거변수")
- SNS에서 검색할 법한 트렌디한 표현 사용
- 한국어, 붙여쓰기

기사 제목: {title}

기사 본문:
{body}
"""


def analyze_article(title: str, body: str) -> dict:
    prompt = _PROMPT.format(title=title, body=body[:4000])
    last_error: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            time.sleep(3 * attempt)
        try:
            response = _client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except genai.errors.ClientError as e:
            if e.code == 429:
                raise RuntimeError("API 요청 한도 초과. 잠시 후 다시 시도해주세요.") from e
            raise RuntimeError(f"Gemini API 오류: {e}") from e
        except genai.errors.ServerError as e:
            last_error = e
            if attempt == 2:
                raise RuntimeError("Gemini 서버 과부하 상태. 잠시 후 다시 시도해주세요.") from e
        except json.JSONDecodeError as e:
            raise RuntimeError("분석 결과 파싱 실패. 다시 시도해주세요.") from e
    raise RuntimeError("Gemini 서버 과부하 상태. 잠시 후 다시 시도해주세요.") from last_error
