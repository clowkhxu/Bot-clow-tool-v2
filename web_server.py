from flask import Flask
from threading import Thread

app = Flask('')


@app.route('/')
def home():
    return "Bot đang hoạt động!"


def run():
    app.run(host='0.0.0.0', port=10000)


def start_server():
    t = Thread(target=run)
    t.start()
