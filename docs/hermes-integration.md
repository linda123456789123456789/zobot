# Hermes Agent Integration Handoff

This prototype currently uses mock chatbot logic so the study can run locally without Hermes. The future Hermes integration should replace only the service layer logic while keeping the Flask route and frontend request/response contract stable.

## Current Mock Architecture

- `app/static/js/chat.js` sends participant messages to `POST /chat/message` with `fetch()`.
- `app/controllers/chat_controller.py` validates the request, builds the system prompt, calls `app/services/hermes_client.py`, and normalizes the JSON response for the frontend.
- `app/services/hermes_client.py` contains the current mock consultation logic and mock final recommendations.
- `app/services/button_flow.py` contains the mock multi-step button flow for button-based conditions.
- `app/services/prompt_builder.py` returns placeholder prompts for task-led and topic-led modes.

The controller should remain the boundary between the browser and the chatbot service. Hermes API keys, agent IDs, prompts, and service credentials must stay on the Flask backend.

## Frontend Request Format

The browser sends this JSON shape to `POST /chat/message`:

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

Allowed values:

- `input_mode`: `"button"` or `"text"`
- `conversation_style`: `"task"` or `"topic"`
- `message`: the current participant message or selected button label
- `history`: frontend-maintained chat history using `{ "role": "...", "content": "..." }`

## Backend Response Format

`POST /chat/message` returns a normalized response:

```json
{
  "reply": "你目前的頭髮狀況比較接近哪一種？",
  "buttons": ["近期有染燙", "髮尾乾燥或毛裂"],
  "is_final": false,
  "final_output": null
}
```

For text-input conditions, `buttons` is usually an empty array. For button-input conditions, `buttons` contains the next mock choices until the final consultation result is reached.

## Final Output Format

Future Hermes recommendations should be normalized to this shape before returning to the frontend:

```json
{
  "reply": "我已根據你的需求整理出一個參考建議，請查看下方摘要。",
  "buttons": [],
  "is_final": true,
  "final_output": {
    "recommended_service": "日本資生堂染髮",
    "reason": "根據你想改變髮色並重視染後質感的需求，此服務較適合。",
    "next_step": "請參考此建議，並從左側服務內容中選擇你最想預約的方案。"
  }
}
```

`final_output` is a consultation result only. It is not a booking completion and does not confirm the participant's service choice.
`recommended_service` must exactly match one service card on the left side, such as `日本資生堂染髮`, `日本哥德式染髮`, `補染`, `漂髮`, `日本資生堂燙髮`, `日本哥德式燙髮`, `髮根燙`, `燙瀏海`, `哥德式護髮`, `哥德式可洛娜三劑式護髮`, or `鉑金修護`.

## ZOBOT Role And Service Selection

ZOBOT is a consultation assistant. It gives advice, asks questions, and explains why a service may fit the participant's needs.

ZOBOT must not complete service selection. Final service selection must happen only when the participant clicks a left-side service card button (`選擇此服務`). The chatbot panel should not include buttons such as `確認此方案`, `選擇此方案`, or `確認服務`.

## Hermes Integration Location

Future Hermes Agent API integration should happen in:

```text
app/services/hermes_client.py
```

Replace the mock logic inside `get_chatbot_reply()` with Hermes API calls, then normalize the Hermes result into the existing backend response contract:

- `reply`
- `is_final`
- `final_output`

Keep `chat_controller.py` as the HTTP interface and response normalizer.

## Environment Variables

Expected future `.env` values:

```text
HERMES_API_URL=
HERMES_API_KEY=
HERMES_AGENT_ID=
```

Do not put API keys, agent IDs, system prompts, or Hermes request logic in frontend JavaScript. `app/static/js/chat.js` should only send participant input to Flask and render the normalized response.
