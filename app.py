from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import re
import uuid
import time
from urllib.parse import unquote
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key')

# تخزين الروابط المؤقتة لكل صفحة
link_storage = {}

def extract_direct_link(mediafire_url):
    """استخراج رابط التحميل المباشر"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(mediafire_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # أنماط البحث عن الرابط المباشر
        patterns = [
            r'https?://download[0-9]+\.mediafire\.com/[^\s"\'<>]+',
            r'https?://www\.mediafire\.com/file/[^\s"\'<>]+/download',
            r'https?://[^\s"\'<>]+\.mediafire\.com/[^\s"\'<>]+\.mp4',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response.text)
            if matches:
                return unquote(matches[0])
        
        # طريقة بديلة: البحث في الجافا سكريبت
        script_match = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', response.text)
        if script_match:
            return script_match.group(1)
            
        return None
    except Exception as e:
        print(f"خطأ: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    """الصفحة الرئيسية - إدخال الرابط"""
    if request.method == 'POST':
        mediafire_url = request.form.get('url', '').strip()
        if not mediafire_url:
            return render_template('index.html', error='الرجاء إدخال رابط صحيح')
        
        # إنشاء معرف فريد للصفحة
        page_id = str(uuid.uuid4())[:8]
        
        # تخزين الرابط مع وقت الإنشاء
        link_storage[page_id] = {
            'url': mediafire_url,
            'time': time.time()
        }
        
        # رابط الصفحة المخصصة
        page_url = url_for('player', page_id=page_id, _external=True)
        return render_template('index.html', success=True, page_url=page_url)
    
    return render_template('index.html')

@app.route('/p/<page_id>')
def player(page_id):
    """الصفحة المخصصة لكل رابط"""
    if page_id not in link_storage:
        return "الرابط غير صحيح أو منتهي الصلاحية", 404
    
    link_info = link_storage[page_id]
    
    # التحقق من الصلاحية (30 دقيقة)
    if time.time() - link_info['time'] > 1800:
        del link_storage[page_id]
        return "انتهت صلاحية الرابط", 404
    
    # استخراج الرابط المباشر
    direct_link = extract_direct_link(link_info['url'])
    
    if direct_link:
        # تحديث الرابط المخزن
        link_storage[page_id]['direct'] = direct_link
        return render_template('player.html', direct_link=direct_link)
    else:
        return "فشل استخراج الرابط المباشر", 500

@app.route('/check/<page_id>')
def check_link(page_id):
    """API للتحقق من الرابط (للمستخدمين)"""
    if page_id not in link_storage:
        return jsonify({'status': 'error', 'message': 'الرابط غير صحيح'})
    
    link_info = link_storage[page_id]
    if 'direct' in link_info:
        return jsonify({'status': 'ready', 'url': link_info['direct']})
    else:
        return jsonify({'status': 'loading', 'message': 'جاري استخراج الرابط...'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
