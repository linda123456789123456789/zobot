# ZOSS Chatbot Prototype

A small Flask MVC-style prototype for a 2x2 salon booking chatbot experiment.

This is a local research prototype. It does not include participant management, login, admin pages, surveys, or a database. Chatbot responses are mocked so the app can run without Hermes.

The participant page includes coloring, perm, and treatment services:

- 染髮: 日本資生堂染髮, 日本哥德式染髮, 補染, 漂髮
- 燙髮: 日本資生堂燙髮, 日本哥德式燙髮, 髮根燙, 燙瀏海
- 護髮: 哥德式護髮, 哥德式可洛娜三劑式護髮, 鉑金修護

## Conditions

- `button + task-led`
- `button + topic-led`
- `free-text + task-led`
- `free-text + topic-led`

Researchers select conditions from `GET /` using neutral labels:

- Condition A: `button + task-led`
- Condition B: `button + topic-led`
- Condition C: `free-text + task-led`
- Condition D: `free-text + topic-led`

Participants are redirected to `/chat?condition=A`, `/chat?condition=B`, `/chat?condition=C`, or `/chat?condition=D`. The participant page does not display condition names, input mode labels, or conversation style labels.

## Setup

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:

   ```bash
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install requirements:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

5. Run the app:

   ```bash
   python run.py
   ```

6. Open:

   ```text
   http://127.0.0.1:5000
   ```

## Project Structure

```text
.
├── run.py
├── requirements.txt
├── README.md
├── .env.example
└── app/
    ├── __init__.py
    ├── controllers/
    │   ├── page_controller.py
    │   └── chat_controller.py
    ├── services/
    │   ├── hermes_client.py
    │   ├── prompt_builder.py
    │   └── button_flow.py
    ├── templates/
    │   ├── layout.html
    │   └── chat.html
    └── static/
        ├── css/
        │   └── style.css
        └── js/
            └── chat.js
```

## Hermes Integration

The current chatbot behavior is implemented in `app/services/hermes_client.py` as mock logic. Replace the TODO section there when the Hermes Agent API integration is ready.
