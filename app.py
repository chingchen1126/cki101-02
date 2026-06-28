from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "我是功能一的文字"

if __name__ == '__main__':
    # Listen on all interfaces inside the container at port 5000
    app.run(host='0.0.0.0', port=5000)
