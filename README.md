# ZOSS Chatbot Prototype

ZOSS Chatbot Prototype 是一個 Flask MVC 風格的本機研究原型，用來測試美髮服務諮詢情境中的 2x2 chatbot 互動條件。

目前專案提供研究人員條件選擇頁、參與者聊天頁、左側服務卡片、ZOBOT 諮詢流程，以及最終參考建議摘要。系統不包含參與者管理、登入、後台、問卷或資料庫。

## 目前功能

- 研究人員可從首頁選擇 4 種實驗條件。
- 參與者頁面不顯示條件名稱、輸入模式或對話風格標籤。
- 服務內容包含染髮、燙髮、護髮三類服務。
- 支援按鈕選項與自由輸入兩種互動模式。
- 支援任務導向與主題導向兩種對話風格。
- ZOBOT 會給出諮詢建議，但不會替參與者完成服務選擇。
- 最終服務選擇只能由參與者點擊左側服務卡片的「選擇此服務」完成。
- AI provider 可使用本機 mock 邏輯，或透過 Gemini API 產生回覆。

## 實驗條件

首頁 `GET /` 供研究人員選擇條件：

| 條件 | 輸入模式 | 對話風格 |
| --- | --- | --- |
| A | 按鈕選項 | 任務導向 |
| B | 按鈕選項 | 主題導向 |
| C | 自由輸入 | 任務導向 |
| D | 自由輸入 | 主題導向 |

選擇後會導向：

- `/chat?condition=A`
- `/chat?condition=B`
- `/chat?condition=C`
- `/chat?condition=D`

## 服務內容

參與者頁面的服務資料集中在 `app/services/service_catalog.py`。

### 染髮

- 日本資生堂染髮
- 日本哥德式染髮
- 補染
- 漂髮

### 燙髮

- 日本資生堂燙髮
- 日本哥德式燙髮
- 髮根燙
- 燙瀏海

### 護髮

- 哥德式護髮
- 哥德式可洛娜三劑式護髮
- 鉑金修護

## 安裝與啟動

1. 建立 virtual environment：

   ```bash
   python -m venv .venv
   ```

2. 啟用 virtual environment：

   ```bash
   source .venv/bin/activate
   ```

   Windows PowerShell：

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. 安裝套件：

   ```bash
   pip install -r requirements.txt
   ```

4. 複製環境變數範本：

   ```bash
   cp .env.example .env
   ```

5. 啟動 Flask app：

   ```bash
   python run.py
   ```

6. 開啟：

   ```text
   http://127.0.0.1:5000
   ```

## 環境變數

`.env` 可設定下列值：

```text
FLASK_ENV=development
SECRET_KEY=replace-this-with-a-local-secret

# mock 或 gemini
AI_PROVIDER=mock
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite

# Reserved for future Hermes Agent API integration.
HERMES_API_URL=
HERMES_API_KEY=
HERMES_AGENT_ID=
```

`AI_PROVIDER=mock` 時會使用 `app/services/hermes_client.py` 內的本機規則回覆，不需要外部 API。

`AI_PROVIDER=gemini` 時，後端會呼叫 Gemini API。若 `GEMINI_API_KEY` 未設定，系統會 fallback 到 mock 回覆。

請不要把真實 API key 放進版本控制；真實金鑰應只存在本機 `.env` 或部署環境變數中。

## 主要路由

- `GET /`：研究人員條件選擇頁。
- `GET /select-condition/<condition>`：將條件代碼導向對應聊天頁。
- `GET /chat?condition=A|B|C|D`：參與者聊天與服務選擇頁。
- `POST /chat/message`：聊天訊息 API，回傳標準化的 ZOBOT 回覆、按鈕選項與最終建議。

`POST /chat/message` request body：

```json
{
  "input_mode": "button",
  "conversation_style": "task",
  "message": "想修護受損",
  "history": [
    {
      "role": "user",
      "content": "想修護受損"
    }
  ]
}
```

標準 response：

```json
{
  "reply": "你目前的頭髮狀況比較接近哪一種？",
  "buttons": ["近期有染燙", "髮尾乾燥或毛裂"],
  "is_final": false,
  "final_output": null
}
```

最終建議 response：

```json
{
  "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
  "buttons": [],
  "is_final": true,
  "final_output": {
    "recommended_service": "哥德式護髮",
    "reason": "適合染燙後受損、乾燥或髮尾毛裂，需要深層修護的顧客。",
    "next_step": "請參考此建議，並從左側服務內容中選擇你最想預約的方案。"
  }
}
```

## 專案結構

```text
.
├── run.py
├── requirements.txt
├── README.md
├── .env.example
├── docs/
│   └── hermes-integration.md
└── app/
    ├── __init__.py
    ├── controllers/
    │   ├── page_controller.py
    │   └── chat_controller.py
    ├── services/
    │   ├── button_flow.py
    │   ├── hermes_client.py
    │   ├── prompt_builder.py
    │   └── service_catalog.py
    ├── templates/
    │   ├── condition_select.html
    │   ├── layout.html
    │   └── chat.html
    └── static/
        ├── css/
        │   └── style.css
        └── js/
            └── chat.js
```

## 程式架構

- `app/controllers/page_controller.py`：處理條件選擇頁與聊天頁。
- `app/controllers/chat_controller.py`：驗證聊天 API request，建立 prompt，呼叫 chatbot service，回傳標準化 JSON。
- `app/services/button_flow.py`：按鈕模式的固定步驟與初始問題。
- `app/services/hermes_client.py`：目前的 chatbot provider 入口，支援 mock 與 Gemini。
- `app/services/prompt_builder.py`：ZOBOT 系統提示、Gemini JSON 回覆格式與輪次限制。
- `app/services/service_catalog.py`：服務卡片資料、推薦規則與服務提示。
- `app/static/js/chat.js`：前端聊天歷史、訊息送出、按鈕渲染、最終建議與服務選擇狀態。

## Hermes Integration

Hermes Agent API 尚未接上。未來整合位置保留在：

```text
app/services/hermes_client.py
```

整合時應維持 `POST /chat/message` 的 request/response contract 不變，並將 Hermes API URL、API key、agent ID、prompt 與呼叫邏輯留在 Flask 後端，不要放到前端 JavaScript。

更多交接細節請看 `docs/hermes-integration.md`。
