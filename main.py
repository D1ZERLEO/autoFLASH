from flask import Flask
import os

from app import i_love_taylor_swift

app = Flask(__name__)


@app.route('/')
def run_task():
    i_love_taylor_swift()  # Запуск задачи
    return "Задача выполнена!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
