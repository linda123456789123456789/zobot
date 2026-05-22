from flask import Blueprint, jsonify, request

from app.services.button_flow import get_button_options, get_next_question, get_task_guided_prompt
from app.services.hermes_client import get_chatbot_reply
from app.services.prompt_builder import build_system_prompt


chat_bp = Blueprint("chat", __name__)

VALID_INPUT_MODES = {"button", "text"}
VALID_CONVERSATION_STYLES = {"task", "topic"}


@chat_bp.post("/chat/message")
def chat_message():
    data = request.get_json(silent=True) or {}

    input_mode = data.get("input_mode", "button")
    conversation_style = data.get("conversation_style", "task")
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if input_mode not in VALID_INPUT_MODES:
        return jsonify({"error": "Invalid input_mode"}), 400

    if conversation_style not in VALID_CONVERSATION_STYLES:
        return jsonify({"error": "Invalid conversation_style"}), 400

    if not message:
        return jsonify({"error": "Message is required"}), 400

    system_prompt = build_system_prompt(input_mode, conversation_style)
    chatbot_response = get_chatbot_reply(
        input_mode=input_mode,
        conversation_style=conversation_style,
        message=message,
        history=history,
        system_prompt=system_prompt,
    )
    next_question = get_next_question(input_mode, conversation_style, history)
    reply = chatbot_response["reply"]
    buttons = chatbot_response.get("buttons")
    response_source = chatbot_response.get("source")

    if input_mode == "button" and not chatbot_response["is_final"]:
        if conversation_style == "task":
            guided = get_task_guided_prompt(history)
            if guided:
                reply = guided["question"]
                buttons = guided["buttons"]
        elif not buttons and response_source == "mock" and next_question:
            reply = next_question
            buttons = get_button_options(
                input_mode,
                conversation_style,
                history=history,
                is_final=False,
            )
    else:
        buttons = []

    return jsonify(
        {
            "reply": reply,
            "buttons": buttons or [],
            "is_final": chatbot_response["is_final"],
            "final_output": chatbot_response["final_output"],
        }
    )
