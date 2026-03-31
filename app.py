from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "안녕하세요! Article Analyzer입니다."


if __name__ == "__main__":
    app.run(debug=True)
