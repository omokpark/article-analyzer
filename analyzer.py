import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_model = genai.GenerativeModel("gemini-2.0-flash")

_PROMPT = """아래 기사를 읽고 다음 형식의 JSON으로만 응답하세요. 설명이나 마크다운 코드블록 없이 JSON만 출력하세요.

{{
  "summary": "한 문장으로 기사의 핵심을 요약",
  "points": [
    "핵심 포인트 1",
    "핵심 포인트 2",
    "핵심 포인트 3"
  ],
  "tags": ["태그1", "태그2", "태그3"]
}}

기사 제목: {title}

기사 본문:
{body}
"""


def analyze_article(title: str, body: str) -> dict | None:
    prompt = _PROMPT.format(title=title, body=body[:4000])
    try:
        response = _model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception:
        return None
