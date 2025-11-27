from flask import Flask, render_template, request, jsonify
from google import genai
import os

app = Flask(__name__)

raw_key = os.environ.get("GEMINI_API_KEY")
if not raw_key:
    raise RuntimeError("❌ 沒有讀到 GEMINI_API_KEY，請先在終端機 export 再啟動 Flask。")

print("🔑 GEMINI_API_KEY 前 5 碼：", raw_key[:5], "長度：", len(raw_key))

client = genai.Client(api_key=raw_key)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "可以多跟我說一點發生了什麼事嗎？"}), 200

    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_message
        )
        text = resp.text or "歐斯這次好像沒有聽清楚，可以再說一次嗎？"
        return jsonify({"reply": text}), 200

    except Exception as e:
        print("❌ Gemini 錯誤：", repr(e))
        return jsonify({
            "reply": f"後端呼叫 Gemini 失敗了：{e}"
        }), 200

if __name__ == "__main__":
    app.run(debug=True)
