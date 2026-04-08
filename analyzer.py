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
  "category": "대분류/소분류",
  "summary": "한 문장 요약",
  "points": [
    "포인트 1",
    "포인트 2",
    "포인트 3"
  ],
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
}

작성 규칙:

[category]
- 콘텐츠의 형식과 주제를 조합하여 유연하게 생성 (예: 뉴스/경제, 블로그/IT, 트위터/정치, 수필/회고)
- 나중에 맵핑 및 분류가 가능하도록 직관적인 단어 사용

[summary]
- 중립적 사실 나열에 그치지 않되, 지나치게 편향되거나 부정적인 톤은 지양
- 기사의 파장, 사회적 맥락, 혹은 독자가 놓치기 쉬운 핵심 의미를 전문적으로 해석
- 현상의 '이면'을 보되 비난조가 아닌 분석적인 시각 유지
- 독자의 궁금증을 자아내는 명확하고 설득력 있는 문장

[points]
- "무슨 일이 있었나"가 아니라 "왜 중요한가" 중심으로 작성
- 맥락·배경·파장을 포함해서 독자가 기사를 안 읽어도 상황을 이해할 수 있게
- 대화체 허용. 단정적이고 직접적인 문장 사용

[tags]
- 단순 고유명사 금지 (예: "이재명", "서울" X)
- 이슈의 본질을 담은 짧은 구문 (예: "사법리스크총선변수", "AI패권전쟁")
- SNS 트렌드 검색어처럼 붙여쓰기, 한국어

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
            result = json.loads(text)
            tags = result.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip().strip('"') for t in tags.split(",")]
            elif isinstance(tags, list) and len(tags) == 1 and "," in tags[0]:
                tags = [t.strip().strip('"') for t in tags[0].split(",")]
            result["tags"] = [t for t in tags if t]
            return result
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
    if last_error:
        raise RuntimeError("Gemini 서버 과부하 상태. 잠시 후 다시 시도해주세요.") from last_error
    raise RuntimeError("Gemini 서버 과부하 상태. 잠시 후 다시 시도해주세요.")
