import os

from dotenv import load_dotenv
from flask import Flask

from app.controllers.chat_controller import chat_bp
from app.controllers.page_controller import page_bp


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "local-dev-secret")

    app.register_blueprint(page_bp)
    app.register_blueprint(chat_bp)

    return app
