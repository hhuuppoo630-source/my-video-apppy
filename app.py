from flask import Flask, render_template, jsonify, request, session
import requests
import re
import uuid
import time
import os
from urllib.parse import unquote
from threading import Lock

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# تخزين الروابط المؤقتة لكل مستخدم
temp_links = {}
links_lock = Lock()

# رابط ميديا فاير من متغيرات البيئة
MEDIAFIRE_URL = os.environ.get('MEDIAFIRE_URL', '')

def extract_direct_link(mediafire_url):
    """استخراج رابط التحميل المباشر من رابط ميديا فاير"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(mediafire_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # البحث عن رابط التحميل
        patterns = [
            r'https?://download[0-9]+\.mediafire\.com/[^\s"\'<>]+',
            r'https?://www\.mediafire\.com/file/[^\s"\'<>]+/download',
            r'https?://[^\s"\'<>]+\.mediafire\.com/[^\s"\'<>]+\.mp4',
            r'https?://[^\s"\'<>]+\.mediafire\.com/[^\s"\'<>]+\.zip',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response.text)
            if matches:
                link = unquote(matches[0])
                return link
        
        # طريقة بديلة: البحث في الجافا سكريبت
        script_matches = re.findall(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', response.text)
        if script_matches:
            return script_matches[0]
        
        # طريقة ثالثة: البحث عن download link في البيانات
        data_match = re.search(r'data-url=["\']([^"\']+)["\']', response.text)
        if data_match:
            return data_match.group(1)
            
        return None
    except Exception as e:
        print(f"خطأ في الاستخراج: {e}")
        return None

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    session_id = str(uuid.uuid4())[:8]
    return render_template('index.html', session_id=session_id)

@app.route('/get_video_link/<session_id>')
def get_video_link(session_id):
    """إرجاع رابط التحميل للمستخدم"""
    with links_lock:
        if session_id in temp_links:
            link_info = temp_links[session_id]
            # التحقق من صلاحية الرابط (30 دقيقة)
            if time.time() - link_info['time'] < 1800:
                return jsonify({'success': True, 'link': link_info['url']})
            else:
                del temp_links[session_id]
        
        # محاولة استخراج الرابط إذا كان موجوداً
        if MEDIAFIRE_URL:
            direct_link = extract_direct_link(MEDIAFIRE_URL)
            if direct_link:
                temp_links[session_id] = {
                    'url': direct_link,
                    'time': time.time()
                }
                return jsonify({'success': True, 'link': direct_link})
        
        return jsonify({'success': False, 'message': 'جاري تحضير الرابط...'})

@app.route('/health')
def health():
    """نقطة صحة السيرفر لـ Render"""
    return jsonify({'status': 'healthy', 'time': time.time()})

# تشغيل السيرفر
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
