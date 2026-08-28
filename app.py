from flask import Flask, render_template, request
import json
import os

app = Flask(__name__)

def load_quran_data():
    json_path = os.path.join(os.path.dirname(__file__), 'quran.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
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
    # تعريف متغير افتراضي لتلافي خطأ prayer_data is undefined
    prayer_data = {'city': '', 'country': ''}
    return render_template('index.html', quran=quran_data, keyword=keyword, prayer_data=prayer_data)

if __name__ == '__main__':
    app.run(debug=True)