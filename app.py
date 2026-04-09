import os
from flask import Flask, render_template, request, jsonify
from extractor import extract_article
from analyzer import analyze_article

app = Flask(__name__)

# 레이트 리미팅: 같은 IP에서 분당 10회 제한
_request_counts: dict = {}  # {ip: [timestamp, ...]}


def _is_rate_limited(ip: str) -> bool:
    import time
    now = time.time()
    window = 60  # 초
    limit = 10
    timestamps = [t for t in _request_counts.get(ip, []) if now - t < window]
    _request_counts[ip] = timestamps
    if len(timestamps) >= limit:
        return True
    _request_counts[ip].append(now)
    return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    ip = request.remote_addr
    if _is_rate_limited(ip):
        return jsonify({"error": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."}), 429

    data = request.get_json(silent=True)
    if not data or not data.get("url"):
        return jsonify({"error": "URL을 입력해주세요."}), 400

    try:
        url = data["url"].strip()

        # 네이버 블로그는 iframe 구조라 모바일 URL로 변환해야 본문 추출 가능
        if "blog.naver.com" in url and "m.blog.naver.com" not in url:
            url = url.replace("https://blog.naver.com", "https://m.blog.naver.com")
            url = url.replace("http://blog.naver.com", "https://m.blog.naver.com")
            print(f"[app] 네이버 블로그 → 모바일 URL 변환: {url}")

        result = extract_article(url)

        if result is None:
            return jsonify({"error": "본문을 추출할 수 없습니다. URL을 확인해주세요."}), 422

        analysis = analyze_article(result["title"], result["body"])
        return jsonify({**result, **analysis})
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"Error occurred: {error_msg}")
        traceback.print_exc()
        return jsonify({"error": f"서버 오류가 발생했습니다: {error_msg}"}), 500


@app.route("/models")
def list_models():
    """사용 가능한 모델 목록을 반환하는 진단 엔드포인트"""
    try:
        from analyzer import _client
        models = list(_client.models.list())
        names = [getattr(m, 'name', str(m)) for m in models]
        return jsonify({"models": names, "count": len(names)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug)
