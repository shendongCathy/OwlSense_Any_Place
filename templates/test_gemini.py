from google import genai
import os

API_KEY = os.environ.get("GEMINI_API_KEY")
print("🔑 測試用 API_KEY 前 5 碼：", API_KEY[:5], "長度：", len(API_KEY))

client = genai.Client(api_key=API_KEY)

try:
    resp = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="說一句：我有成功連到 Gemini API。"
    )
    print("✅ 呼叫成功，回覆：", resp.text)
except Exception as e:
    print("❌ 呼叫失敗，錯誤是：", repr(e))