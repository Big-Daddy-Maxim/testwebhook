from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return 'Server running', 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        print(data)  # Вывод данных от POST
        return 'success', 200
    elif request.method == 'GET':
        return 'GET success', 200

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
