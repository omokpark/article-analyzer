from flask import Flask, render_template, request, jsonify
from extractor import extract_article
from analyzer import analyze_article

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)
    if not data or not data.get("url"):
        return jsonify({"error": "URL을 입력해주세요."}), 400

    url = data["url"].strip()
    result = extract_article(url)

    if result is None:
        return jsonify({"error": "본문을 추출할 수 없습니다. URL을 확인해주세요."}), 422

    analysis = analyze_article(result["title"], result["body"])
    if analysis is None:
        return jsonify({"error": "기사 분석에 실패했습니다."}), 500

    return jsonify({**result, **analysis})


if __name__ == "__main__":
    app.run(debug=True)
