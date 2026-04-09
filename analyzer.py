import os
import json
import re
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

_api_key = os.environ.get("GEMINI_API_KEY")
if not _api_key:
    raise RuntimeError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

_client = genai.Client(api_key=_api_key)

# 구글 Gemini API에서 실제로 지원하는 안정적인 모델명 목록
# 한도(RPD)가 많은 순서로 정렬
_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

_PROMPT = """아래 기사를 분석하여 기사의 깊이(심도)에 따라 적절한 JSON 형식으로 응답하세요.
설명이나 마크다운 코드블록 없이 JSON만 출력하세요.

[분석 단계]
1. 기사의 정보 밀도, 전문성, 길이를 바탕으로 'depth'를 결정합니다.
   - 'simple': 짧은 뉴스, 일반적인 정보 전달
   - 'deep': 기술 블로그, 전문 칼럼, 심층 분석글

2. 결정된 'depth'에 따라 다음 필드를 포함합니다.

[공통 필드]
- "depth": "simple" 또는 "deep"
- "category": "대분류/소분류" (예: 기술/AI, 뉴스/경제)
- "summary": 한 문장 핵심 요약 (전문적이고 분석적인 톤)
- "points": 주요 요약 포인트 (3~5개, "왜 중요한가" 중심)
- "tags": 이슈의 본질을 담은 태그 (한국어, 붙여쓰기)

[Deep 전용 필드 (depth가 'deep'일 때만 포함)]
- "detailed_analysis": [
    {{"section": "섹션 제목", "content": "내용 요약 및 분석"}}
  ] (기사의 논리 전개를 3~4개 섹션으로 상세히 분해)
- "insight": "기사의 기술적/사회적 맥락과 파장에 대한 전문적인 통찰"
- "mermaid": "가로 방향 마인드맵(mindmap) 또는 순서도(graph LR) 형식의 Mermaid 코드. 기사 핵심 개념 간의 관계를 시각화."

작성 규칙:
- [summary]: 독자의 궁금증을 자아내는 설득력 있는 해석 제공
- [points]: 기사를 안 읽어도 상황을 완벽히 이해할 수 있도록 배경과 파장 포함
- [mermaid]: 'mindmap'이나 'graph LR'을 사용하여 개념 구조를 명확히 시각화 (한글 사용)

기사 제목: {title}

기사 본문:
{body}
"""


def _parse_json(text: str) -> dict:
    """응답 텍스트에서 JSON을 최대한 안전하게 추출합니다."""
    text = text.strip()
    # 코드블록 제거
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.lstrip("json").strip()
            if candidate.startswith("{"):
                text = candidate
                break
    # 정규식으로 { } 블록 추출
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        text = match.group(0)
    return json.loads(text)


def analyze_article(title: str, body: str) -> dict:
    prompt = _PROMPT.format(title=title, body=body[:4000])
    model_errors = []

    for model_name in _MODELS:
        try:
            print(f"Trying model: {model_name}")
            response = _client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            result = _parse_json(response.text)

            # tags 정규화
            tags = result.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip().strip('"') for t in tags.split(",")]
            elif isinstance(tags, list) and len(tags) == 1 and "," in tags[0]:
                tags = [t.strip().strip('"') for t in tags[0].split(",")]
            result["tags"] = [t for t in tags if t]

            print(f"Success with model: {model_name}")
            return result

        except genai.errors.ClientError as e:
            code = getattr(e, 'code', 0)
            print(f"ClientError {code} for {model_name}: {e}")
            if code in [429, 404, 400]:
                model_errors.append(f"{model_name}(HTTP {code})")
                continue
            raise RuntimeError(f"Gemini API 오류: {e}") from e

        except json.JSONDecodeError as e:
            print(f"JSON parse error for {model_name}: {e}")
            model_errors.append(f"{model_name}(JSON오류)")
            continue

        except Exception as e:
            print(f"Unexpected error for {model_name}: {type(e).__name__}: {e}")
            model_errors.append(f"{model_name}({type(e).__name__})")
            continue

    error_summary = ", ".join(model_errors)
    raise RuntimeError(f"모든 모델 호출 실패 ({error_summary}). API 한도를 확인하거나 잠시 후 다시 시도해주세요.")
