from flask import Flask, render_template, request, jsonify
from google import genai
import os
from datetime import datetime

app = Flask(__name__)

# ====== API Key 檢查（支援 GEMINI_API_KEY / GOOGLE_API_KEY）======
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "❌ 沒有讀到 GEMINI_API_KEY / GOOGLE_API_KEY 環境變數。\n"
        "請在本機或 Render 的環境變數中設定其中一個。"
    )

# ✅ 明確把 api_key 傳給 Client，不再靠自動偵測
client = genai.Client(api_key=GEMINI_API_KEY)

# ====== 高風險關鍵字 & 紀錄結構（prototype：先放記憶體） ======
RISK_KEYWORDS = [
    "自殺", "自殘", "想死", "不想活", "傷害自己",
    "割腕", "跳樓", "上吊", "我活著好累",
    "被打", "被揍", "被霸凌", "被欺負", "被羞辱",
    "好想消失", "不想存在", "不想活下去"
]

# 高風險訊息的簡易暫存（正式版之後可以換成資料庫）
HIGH_RISK_LOGS = []

def build_system_instruction(nickname: str, anon_id: str, tone_mode: str) -> str:
    """
    根據語氣模式（tone_mode）產生系統指令。
    tone_mode: "short" / "warm" / "guide"
    """
    base = (
        f"你是一個叫「歐斯 OwlSense」的校園情緒陪伴機器人，"
        f"正在和一位學生聊天。這位學生的暱稱是「{nickname}」，匿名代號是「{anon_id}」。"
        "你面對的是國小中高年級學生，閱讀耐性有限。"
        "你不是心理師、醫師或輔導老師，不能提供醫療或診斷，也不能給具體自殺／自殘方法。"
        "你的任務是溫柔、簡短地陪伴學生說出感受，幫他整理心情，"
        "在偵測到『自殺、自殘、想死、不想活、被嚴重傷害』這類高風險訊號時，"
        "才適度提醒他可以找信任的大人（導師、輔導老師或家人）聊聊。"
        "不要每一則回覆都提老師或輔導老師。"
    )

    if tone_mode == "short":
        style = (
            "你現在使用「超簡短回應」模式："
            "每次回覆只用 1～2 個非常短的句子，總字數控制在 20～35 個中文字。"
            "重點是簡單標記對方的感受（例如：『聽起來你有點悶』），"
            "不需要每次都提問，也不要展開分析或給很多建議。"
            "如果學生只丟一兩個字，你可以回一句簡單的陪伴，例如："
            "『嗯，我在聽。』、『可以慢慢說，不用急。』。"
            "不要長篇大論。"
        )
    elif tone_mode == "guide":
        style = (
            "你現在使用「引導提問」模式："
            "每次回覆盡量用 2 個短句，總字數控制在 25～45 個中文字。"
            "第一句簡短回應學生的感受，第二句問一個『很小、很具體』的問題，"
            "一次只問一件事，例如：『是跟同學的事嗎？』、『是發生在學校還是家裡？』。"
            "不要連續問兩個以上的問題，不要用考試或審問的語氣。"
        )
    else:  # "warm" 溫柔陪伴（預設）
        style = (
            "你現在使用「溫柔陪伴」模式："
            "每次回覆以 1～2 個短句為主，總字數控制在 25～45 個中文字。"
            "先輕輕回應學生的感受，再給一點點溫柔的陪伴或肯定，"
            "有需要時才加上一個簡單的小問題。"
            "語氣像一個穩定、溫柔又不打擾的朋友，不下評價、不說『你想太多』、不說教。"
        )

    limit = "請嚴格遵守上述風格說明，並將每次回覆限制在 20～45 個中文字，不要寫成長段落。"

    return base + style + limit



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    學生端聊天 API：
    - 接收 message + anon_id + nickname
    - 呼叫 Gemini 回覆
    - 偵測高風險內容 → 紀錄摘要（不存全文）
    """
    data = request.get_json(force=True) or {}
    user_message = (data.get("message") or "").strip()

    # 從前端帶來的匿名代號與暱稱（若沒有則給預設值）
    anon_id = (data.get("anon_id") or "Owl#000").strip() or "Owl#000"
    nickname = (data.get("nickname") or "同學").strip() or "同學"
    
    tone_mode = (data.get("tone_mode") or "warm").strip()
    if tone_mode not in {"short", "warm", "guide"}:
        tone_mode = "warm"

    
    if not user_message:
        return jsonify({"reply": "可以多跟我說一點發生了什麼事嗎？"}), 200

    # ====== 高風險偵測：只紀錄片段，不存全文 ======
    if any(kw in user_message for kw in RISK_KEYWORDS):
        HIGH_RISK_LOGS.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "anon_id": anon_id,
            "nickname": nickname,
            "snippet": user_message[:80] + ("..." if len(user_message) > 80 else "")
        })

    # ====== 系統指示（給 model 的角色設定） ======
    # ====== 系統指示（依照語氣模式產生） ======
    system_instruction = build_system_instruction(nickname, anon_id, tone_mode)



    #====== 將系統指示 + 學生話語拼成一個 prompt（最穩格式） ======
    prompt = (
        f"{system_instruction}\n\n"
        f"以下是學生（暱稱：{nickname}，匿名代號：{anon_id}）現在跟你說的話：\n"
        f"{user_message}\n\n"
        "請用一小段溫柔、具體的口語中文回應他，直接用「你」來稱呼對方，"
        "不要重複學生原話，試著幫忙標記情緒、理解狀況，並在適合時提醒可以找信任的大人聊聊。"
    )

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        reply_text = getattr(resp, "text", None) or "歐斯這次好像沒有聽清楚，可以再說一次嗎？"

    except Exception as e:
        # 後端 log 給老師 / 開發者看
        print("❌ Gemini 錯誤：", repr(e))
        # 給學生的安全回覆
        reply_text = (
            "歐斯這次連線好像出了點狀況，可以稍後再試試看。"
            "如果你現在覺得很不舒服或有危險的想法，一定要立刻跟信任的大人說，"
            "例如導師、輔導老師或家人，好嗎？"
        )

    return jsonify({"reply": reply_text}), 200


# ====== 老師後台：僅顯示高風險摘要，不顯示全文 ======

@app.route("/teacher", methods=["GET", "POST"])
def teacher():
    """
    簡易老師後台：
    - GET：顯示登入畫面
    - POST：驗證密碼後，顯示高風險摘要列表
    """
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_pw:
        return (
            "<h3>系統尚未設定 ADMIN_PASSWORD 環境變數，"
            "請在本機或 Render 後台設定後再使用老師後台。</h3>"
        ), 500

    if request.method == "GET":
        # 簡單的登入表單
        return """
        <html lang="zh-Hant">
        <head>
            <meta charset="UTF-8">
            <title>OwlSense 老師後台登入</title>
        </head>
        <body>
            <h2>OwlSense 老師後台登入</h2>
            <p>此頁面僅供導師與輔導老師使用，用來查看「高風險訊息摘要」，不顯示學生完整對話。</p>
            <form method="post">
                <label>後台密碼：</label>
                <input type="password" name="password" />
                <button type="submit">登入</button>
            </form>
        </body>
        </html>
        """

    # POST：檢查密碼
    pwd = request.form.get("password", "")
    if pwd != admin_pw:
        return "<h3>密碼錯誤，請重新輸入。</h3>", 403

    # 組出高風險摘要表格
    rows_html = ""
    if not HIGH_RISK_LOGS:
        rows_html = """
        <tr>
          <td colspan="4">目前尚未偵測到高風險訊息。</td>
        </tr>
        """
    else:
        for log in HIGH_RISK_LOGS:
            rows_html += f"""
            <tr>
              <td>{log['time']}</td>
              <td>{log['anon_id']}</td>
              <td>{log['nickname']}</td>
              <td>{log['snippet']}</td>
            </tr>
            """

    html = f"""
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <title>OwlSense 高風險摘要（老師後台）</title>
    </head>
    <body>
        <h2>OwlSense 高風險摘要（老師後台）</h2>
        <p>
          以下僅顯示時間、匿名代號、學生暱稱與部分訊息片段，<br>
          不顯示完整對話內容，以保護學生隱私。
        </p>
        <table border="1" cellpadding="4" cellspacing="0">
            <tr>
              <th>時間</th>
              <th>匿名代號</th>
              <th>暱稱</th>
              <th>訊息片段</th>
            </tr>
            {rows_html}
        </table>
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    # 本機開發用；Render 會用 gunicorn app:app 來啟動
    app.run(debug=True)
