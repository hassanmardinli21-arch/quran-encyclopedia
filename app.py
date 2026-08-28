from flask import Flask, render_template, request
import json
import os

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
    tafsir_data = {}  # يمكنك إضافة {'error': 'لا توجد بيانات تفسير'} حسب الحاجة
    return render_template('index.html', 
                           quran=quran_data, 
                           keyword=keyword, 
                           prayer_data=prayer_data,
                           tafsir_data=tafsir_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)