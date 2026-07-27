from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ السيرفر يعمل! مرحباً بك في محول ميديا فاير"

@app.route('/p/<page_id>')
def player(page_id):
    return f"✅ صفحة المستخدم: {page_id} - الرابط يعمل!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
