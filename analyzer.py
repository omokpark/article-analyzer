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


def _get_available_models() -> list[str]:
    """API에서 generateContent를 지원하는 실제 모델 목록을 조회합니다."""
    try:
        all_models = list(_client.models.list())
        # 텍스트 생성 가능한 모델만 필터링
        text_models = [
            m.name for m in all_models 
            if hasattr(m, 'supported_actions')
            and 'generateContent' in (m.supported_actions or [])
        ]
        if not text_models:
            # supported_actions가 없는 경우 이름 기반 필터
            text_models = [
                m.name for m in all_models
                if 'flash' in m.name.lower() or 'pro' in m.name.lower()
            ]
        print(f"Available models: {text_models}")
        return text_models
    except Exception as e:
        print(f"Model list failed: {e}")
        return []


def analyze_article(title: str, body: str) -> dict:
    prompt = _PROMPT.format(title=title, body=body[:4000])

    # 실제 API 모델 목록 조회
    models = _get_available_models()

    # 우선순위: lite/flash 계열 (한도 여유), pro 계열 (성능)
    def priority(name: str) -> int:
        n = name.lower()
        if 'lite' in n and 'flash' in n:
            return 0
        if 'flash' in n:
            return 1
        if 'pro' in n:
            return 2
        return 3

    models = sorted(models, key=priority)

    if not models:
        raise RuntimeError("사용 가능한 모델이 없습니다. API 키 설정을 확인해주세요.")

    model_errors = []
    for model_name in models:
        try:
            print(f"Trying: {model_name}")
            response = _client.models.generate_content(
                model=model_name,
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
            if e.code in [429, 404]:
                model_errors.append(f"{model_name}({e.code})")
                continue
            raise RuntimeError(f"Gemini API 오류: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError("분석 결과 파싱 실패. 다시 시도해주세요.") from e
        except Exception as e:
            model_errors.append(f"{model_name}({type(e).__name__})")
            continue

    raise RuntimeError(f"모든 모델 사용 불가: {', '.join(model_errors)}")
