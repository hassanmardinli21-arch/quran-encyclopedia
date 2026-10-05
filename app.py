from flask import Flask, render_template_string, request, jsonify
import json

app = Flask(__name__)

# ----------------- 1. تحميل الملفات -----------------
QURAN_PATH = 'data/quran.json'
TAFSIR_PATH = r'F:\تطبيقات صنعي\الموسوعة_الإسلامية\data\tafsir_saadi.json'
BUKHARI_PATH = 'data/bukhari_hadiths.json'

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"تحذير: لم يتم العثور على الملف {filepath}")
        return []
    except Exception as e:
        print(f"خطأ في قراءة {filepath}: {e}")
        return []

quran_data = load_json(QURAN_PATH)
tafsir_list = load_json(TAFSIR_PATH)
bukhari_data = load_json(BUKHARI_PATH)

tafsir_map = {}
for item in tafsir_list:
    key = (item.get('surah'), item.get('ayah'))
    tafsir_map[key] = item.get('text', 'لا يوجد نص تفسير')

# ----------------- 2. منطق البحث والربط -----------------
def get_tafsir(surah_num, ayah_num):
    if not surah_num or not ayah_num:
        return ""
    return tafsir_map.get((int(surah_num), int(ayah_num)), "لا يوجد تفسير مسجل لهذه الآية حالياً.")

# ----------------- 3. المسارات (Routes) -----------------

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/search', methods=['GET'])
def search():
    book = request.args.get('book', 'quran').lower()
    query = request.args.get('query', '').strip()
    surah = request.args.get('surah', type=int)

    results = []

    if book == 'quran':
        if surah:
            for item in quran_data:
                if item.get('surah') == surah:
                    ayah_num = item.get('ayah')
                    results.append({
                        'type': 'quran',
                        'surah': surah,
                        'ayah': ayah_num,
                        'text': item.get('text', ''),
                        'tafsir': get_tafsir(surah, ayah_num)
                    })

    elif book == 'bukhari':
        if query:
            count = 0
            for hadith in bukhari_data:
                if query in hadith.get('text', ''):
                    results.append({
                        'type': 'hadith',
                        'book': 'صحيح البخاري',
                        'text': hadith.get('text', ''),
                        'value': hadith.get('value', '')
                    })
                    count += 1
                    if count >= 10:
                        break

    return jsonify(results)

# ----------------- 4. واجهة المستخدم (HTML) -----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>المكتبة القرآنية والتفاسير</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4; text-align: center; padding: 20px; }
        .container { background: white; padding: 20px; border-radius: 8px; max-width: 800px; margin: 0 auto; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        select, input, button { padding: 10px; margin: 5px; font-size: 16px; }
        .result { border: 1px solid #ddd; margin-top: 20px; padding: 15px; text-align: right; }
        .tafsir { background-color: #f9f9f9; border-top: 2px solid #28a745; margin-top: 10px; padding: 10px; color: #333; }

        /* ====== قواعد صندوق الحديث ====== */
        .hadith-box {
            border: 1px solid #007bff;
            background: #e9f7ff;
            padding: 15px;
            margin-bottom: 10px;

            direction: rtl;
            text-align: right;

            line-height: 2;
            white-space: normal;
            word-wrap: break-word;
            overflow-wrap: anywhere;

            user-select: text;
            cursor: text;

            position: relative;
        }

        .hadith-text {
            direction: rtl;
            text-align: right;

            white-space: pre-wrap;
            word-break: normal;
            overflow-wrap: break-word;

            user-select: text;
            cursor: text;

            font-size: 18px;
            line-height: 2;
        }
    </style>
</head>
<body>
    <h1>المكتبة القرآنية والتفاسير</h1>
    <div class="container">
        <select id="book">
            <option value="quran">القرآن الكريم</option>
            <option value="bukhari">صحيح البخاري</option>
        </select>

        <select id="surah">
            <option value="1">الفائحة</option>
            <option value="2">البقرة</option>
        </select>

        <input type="text" id="query" placeholder="ابحث عن كلمة أو آية...">
        <button onclick="doSearch()">بحث</button>

        <div id="results"></div>
    </div>

    <script>
        // ✅ دالة تهريب HTML لمنع أي تفسير خاطئ للوسوم
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text || '';
            return div.innerHTML;
        }

        async function doSearch() {
            const book = document.getElementById('book').value;
            const query = document.getElementById('query').value;
            const surah = document.getElementById('surah').value;

            const response = await fetch(`/search?book=${book}&query=${encodeURIComponent(query)}&surah=${surah}`);
            const data = await response.json();

            let html = '';
            data.forEach(item => {
                if (item.type === 'quran') {
                    html += `<div class="result">
                                <strong>سورة ${item.surah} آية ${item.ayah}:</strong><br>
                                <p>${escapeHtml(item.text)}</p>
                                <div class="tafsir">
                                    <strong>التفسير:</strong><br>
                                    ${escapeHtml(item.tafsir)}
                                </div>
                             </div>`;
                } else if (item.type === 'hadith') {
                    html += `<div class="result hadith-box">
                                <strong>${escapeHtml(item.book)}</strong><br>
                                <div class="hadith-text">${escapeHtml(item.text)}</div>
                             </div>`;
                }
            });

            document.getElementById('results').innerHTML = html;
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True, port=5000)