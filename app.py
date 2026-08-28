from flask import Flask, render_template, request
import json
import os
import math

app = Flask(__name__)

def load_quran_data():
    json_path = os.path.join(os.path.dirname(__file__), 'quran.json')
    if not os.path.exists(json_path):
        print("⚠️ ملف quran.json غير موجود، سيتم استخدام بيانات فارغة.")
        return []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ خطأ في قراءة ملف quran.json: {e}")
        return []

quran_data = load_quran_data()

@app.template_filter('highlight')
def highlight_filter(text, keyword):
    if not keyword or not text:
        return text
    return text.replace(keyword, f'<mark>{keyword}</mark>')

@app.route('/')
def home():
    keyword = request.args.get('q', '')
    prayer_data = {'city': 'غير محدد', 'country': 'غير محدد'}
    tafsir_data = {}  # يمكنك تعبئتها لاحقاً

    # تصفية البيانات حسب الكلمة المفتاحية
    if keyword:
        filtered_data = [item for item in quran_data if keyword in item.get('text', '')]
    else:
        filtered_data = quran_data

    # حساب عدد الصفحات (إذا كانت البيانات فارغة، اجعل الصفحة = 1)
    per_page = 10
    total_items = len(filtered_data)
    total_pages = max(1, math.ceil(total_items / per_page))  # على الأقل صفحة واحدة

    # الصفحة الحالية
    page = request.args.get('page', 1, type=int)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    paginated_data = filtered_data[start:end]

    return render_template('index.html',
                           quran=paginated_data,
                           keyword=keyword,
                           prayer_data=prayer_data,
                           tafsir_data=tafsir_data,
                           total_pages=total_pages,
                           current_page=page)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)