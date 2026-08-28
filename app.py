from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

# تحميل بيانات القرآن من ملف quran.json
def load_quran_data():
    json_path = os.path.join(os.path.dirname(__file__), 'quran.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@app.route('/')
def home():
    # يمكنك تعديل هذا ليطابق الصفحة الرئيسية لتطبيقك أو عرض البيانات
    quran_data = load_quran_data()
    if quran_data:
        return render_template('index.html', quran=quran_data)
    return "مرحباً بك في موسوعة القرآن الكريم، جارٍ تحميل البيانات."

if __name__ == '__main__':
    app.run(debug=True)