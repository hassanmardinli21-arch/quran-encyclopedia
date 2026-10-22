import os
import re
import json
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# ==================== 1. تحميل القرآن والتفسير ====================
QURAN_PATH = 'quran.json'
TAFSIR_PATH = 'tafsir_saadi.json'

def load_json(filepath):
    # دالة ذكية تبحث عن الملف في المسار الرئيسي أو مجلد data أو أي مجلد فرعي
    possible_paths = [
        filepath,
        os.path.join('data', filepath),
        os.path.join('static', filepath)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    print(f"تم تحميل {path} بنجاح")
                    return json.load(f)
            except Exception as e:
                print(f"خطأ في قراءة {path}: {e}")
                return []
    
    print(f"لم يتم العثور على الملف: {filepath}")
    return []

quran_data = load_json(QURAN_PATH)
tafsir_list = load_json(TAFSIR_PATH)

surahs_list = []
quran_ayahs_map = {}

if isinstance(quran_data, list):
    for surah in quran_data:
        surah_num = surah.get('id')
        surah_name = surah.get('name', '')
        surahs_list.append({'id': surah_num, 'name': surah_name})
        for ayah in surah.get('verses', []):
            ayah_num = ayah.get('id')
            quran_ayahs_map[(surah_num, ayah_num)] = ayah.get('text', '')

print(f"تم تحميل {len(surahs_list)} سورة و {len(quran_ayahs_map)} آية.")

tafsir_map = {}
surah_names_ar = [s['name'] for s in surahs_list]

if isinstance(tafsir_list, list) and tafsir_list and isinstance(tafsir_list[0], dict) and 'ayahs' in tafsir_list[0]:
    for surah_obj in tafsir_list:
        surah_name = surah_obj.get('surah_name', '').strip()
        surah_num = None
        for i, name in enumerate(surah_names_ar, start=1):
            if name == surah_name or surah_name in name or name in surah_name:
                surah_num = i
                break
        if not surah_num:
            continue
        for ayah in surah_obj.get('ayahs', []):
            ayah_num = ayah.get('number', 0)
            tafsir_map[(surah_num, ayah_num)] = ayah.get('text', '')

print(f"تم تحميل {len(tafsir_map)} تفسير.")

# ==================== حساب الجُمّل (أبجد هوز) ====================
ABJAD_VALUES = {
    'ا': 1, 'أ': 1, 'إ': 1, 'آ': 1, 'ء': 1, 'ؤ': 1, 'ئ': 1,
    'ب': 2, 'ج': 3, 'د': 4, 'ه': 5, 'ة': 5, 'و': 6, 'ز': 7, 'ح': 8, 'ط': 9,
    'ي': 10, 'ى': 10, 'ك': 20, 'ل': 30, 'م': 40, 'ن': 50, 'س': 60, 'ع': 70,
    'ف': 80, 'ص': 90, 'ق': 100, 'ر': 200, 'ش': 300, 'ت': 400, 'ث': 500,
    'خ': 600, 'ذ': 700, 'ض': 800, 'ظ': 900, 'غ': 1000,
}

_DIACRITICS = re.compile(r'[\u064B-\u0652\u0670\u0640]')
_WORD_SPLIT = re.compile(r'[^\u0621-\u064A]+')

def strip_diacritics(text):
    return _DIACRITICS.sub('', text or '')

def normalize_arabic(text):
    if not text:
        return ''
    text = strip_diacritics(text)
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    text = text.replace('ة', 'ه')
    text = text.replace('ى', 'ي')
    text = text.replace('ؤ', 'و').replace('ئ', 'ي')
    return text

def abjad_value(text):
    if not text:
        return 0
    text = strip_diacritics(text)
    total = 0
    for ch in text:
        total += ABJAD_VALUES.get(ch, 0)
    return total

def abjad_breakdown(text):
    if not text:
        return []
    text = strip_diacritics(text)
    result = []
    for ch in text:
        val = ABJAD_VALUES.get(ch, 0)
        if val > 0:
            result.append({'char': ch, 'value': val})
    return result

def match_text(text, query, search_type):
    if not text or not query:
        return False
    if search_type == 'exact':
        return query in text
    if search_type == 'phrase':
        return strip_diacritics(query) in strip_diacritics(text)
    if search_type == 'fuzzy':
        return normalize_arabic(query) in normalize_arabic(text)
    q = strip_diacritics(query)
    words = _WORD_SPLIT.split(strip_diacritics(text))
    return q in words

# ==================== 2. الكتب ====================
BOOKS = {
    'bukhari': 'صحيح البخاري',
    'muslim': 'صحيح مسلم',
    'abudawud': 'سنن أبي داود',
    'tirmidhi': 'جامع الترمذي',
    'nasai': 'سنن النسائي',
    'ibnmajah': 'سنن ابن ماجه',
    'malik': 'موطأ مالك',
    'ahmed': 'مسند أحمد',
    'darimi': 'سنن الدارمي',
    'riyad_assalihin': 'رياض الصالحين',
    'aladab_almufrad': 'الأدب المفرد',
    'bulugh_almaram': 'بلوغ المرام',
    'mishkat_almasabih': 'مشكاة المصابيح',
    'shamail_muhammadiyah': 'الشمائل المحمدية'
}

loaded_books_cache = {}

def load_hadith_book(book_id):
    if book_id in loaded_books_cache:
        return loaded_books_cache[book_id]

    all_hadiths = []
    # البحث في المسار الرئيسي، مجلد data، أو أي مجلد فرعي يحمل اسم الكتاب
    possible_paths = [
        f'{book_id}.json',
        os.path.join('data', f'{book_id}.json'),
        os.path.join(book_id, f'{book_id}.json')
    ]
    
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            data = load_json(path)
            if isinstance(data, dict):
                all_hadiths = data.get('hadiths', data.get('data', []))
            elif isinstance(data, list):
                all_hadiths = data
            found = True
            break
            
    # إذا لم يجد الملف، يبحث داخل مجلد باسم الكتاب
    if not found and os.path.isdir(book_id):
        folder_path = book_id
        files = os.listdir(folder_path)
        files = sorted(
            [f for f in files if f.endswith('.json')],
            key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 999
        )
        for filename in files:
            filepath = os.path.join(folder_path, filename)
            data = load_json(filepath)
            if isinstance(data, dict):
                all_hadiths.extend(data.get('hadiths', data.get('data', [])))
            elif isinstance(data, list):
                all_hadiths.extend(data)

    loaded_books_cache[book_id] = all_hadiths
    return all_hadiths

# ==================== 3. المسارات ====================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, books=BOOKS, surahs=surahs_list)

@app.route('/api/abjad')
def api_abjad():
    text = request.args.get('text', '').strip()
    if not text:
        return jsonify({'text': '', 'value': 0, 'breakdown': []})
    return jsonify({
        'text': text,
        'value': abjad_value(text),
        'breakdown': abjad_breakdown(text)
    })

@app.route('/api/hadith')
def get_hadith():
    book_id = request.args.get('book', 'bukhari')
    index = request.args.get('index', 0, type=int)

    if book_id not in BOOKS:
        return jsonify({'error': 'كتاب غير موجود'})

    hadiths = load_hadith_book(book_id)
    if not hadiths or index < 0 or index >= len(hadiths):
        return jsonify({'error': 'حديث غير موجود'})

    h = hadiths[index]
    return jsonify({
        'index': index,
        'total': len(hadiths),
        'id': h.get('idInBook', index + 1),
        'text': h.get('arabic', ''),
        'narrator': h.get('english', {}).get('narrator', ''),
        'abjad': abjad_value(h.get('arabic', ''))
    })

@app.route('/api/hadith_by_id')
def get_hadith_by_id():
    book_id = request.args.get('book', 'bukhari')
    hadith_id = request.args.get('id', 0, type=int)

    if book_id not in BOOKS:
        return jsonify({'error': 'كتاب غير موجود'})

    hadiths = load_hadith_book(book_id)
    if not hadiths:
        return jsonify({'error': 'لا توجد أحاديث'})

    for i, h in enumerate(hadiths):
        if h.get('idInBook') == hadith_id:
            return jsonify({
                'index': i,
                'total': len(hadiths),
                'id': h.get('idInBook', i + 1),
                'text': h.get('arabic', ''),
                'narrator': h.get('english', {}).get('narrator', ''),
                'abjad': abjad_value(h.get('arabic', ''))
            })

    if 0 < hadith_id <= len(hadiths):
        h = hadiths[hadith_id - 1]
        return jsonify({
            'index': hadith_id - 1,
            'total': len(hadiths),
            'id': h.get('idInBook', hadith_id),
            'text': h.get('arabic', ''),
            'narrator': h.get('english', {}).get('narrator', ''),
            'abjad': abjad_value(h.get('arabic', ''))
        })

    return jsonify({'error': f'الحديث رقم {hadith_id} غير موجود'})

@app.route('/api/surah')
def get_surah():
    surah_num = request.args.get('surah', 1, type=int)
    ayahs = []
    for (s, a), text in sorted(quran_ayahs_map.items()):
        if s == surah_num:
            ayahs.append({
                'ayah': a,
                'text': text,
                'tafsir': tafsir_map.get((s, a), ''),
                'abjad': abjad_value(text)
            })
    surah_name = next((s['name'] for s in surahs_list if s['id'] == surah_num), '')
    return jsonify({
        'surah': surah_num,
        'name': surah_name,
        'ayahs': ayahs
    })

@app.route('/api/search')
def search():
    book_id = request.args.get('book', 'bukhari')
    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'word')

    if book_id not in BOOKS:
        return jsonify([])

    hadiths = load_hadith_book(book_id)

    if search_type == 'number':
        try:
            target_id = int(query)
        except ValueError:
            return jsonify([])
        results = []
        for i, h in enumerate(hadiths):
            if h.get('idInBook') == target_id:
                results.append({
                    'index': i,
                    'id': h.get('idInBook', i + 1),
                    'text': h.get('arabic', ''),
                    'narrator': h.get('english', {}).get('narrator', ''),
                    'abjad': abjad_value(h.get('arabic', ''))
                })
        return jsonify(results)

    if not query:
        return jsonify([])

    results = []
    for i, h in enumerate(hadiths):
        arabic_text = h.get('arabic', '')
        if match_text(arabic_text, query, search_type):
            results.append({
                'index': i,
                'id': h.get('idInBook', i + 1),
                'text': arabic_text,
                'narrator': h.get('english', {}).get('narrator', ''),
                'abjad': abjad_value(arabic_text)
            })
    return jsonify(results)

@app.route('/api/search_advanced')
def search_advanced():
    query = request.args.get('query', '').strip()
    books_param = request.args.get('books', '')
    include_quran = request.args.get('quran', '0') == '1'
    search_type = request.args.get('type', 'word')

    if not query:
        return jsonify({'books': {}, 'quran': []})

    result = {'books': {}, 'quran': []}

    if include_quran and search_type != 'number':
        quran_results = []
        for (s, a), text in quran_ayahs_map.items():
            if match_text(text, query, search_type):
                surah_name = next((x['name'] for x in surahs_list if x['id'] == s), '')
                quran_results.append({
                    'surah': s,
                    'surah_name': surah_name,
                    'ayah': a,
                    'text': text,
                    'abjad': abjad_value(text)
                })
        result['quran'] = quran_results

    selected_books = []
    if books_param == 'all':
        selected_books = list(BOOKS.keys())
    elif books_param:
        selected_books = [b.strip() for b in books_param.split(',') if b.strip() in BOOKS]

    for book_id in selected_books:
        hadiths = load_hadith_book(book_id)
        book_results = []

        if search_type == 'number':
            try:
                target_id = int(query)
            except ValueError:
                continue
            for i, h in enumerate(hadiths):
                if h.get('idInBook') == target_id:
                    book_results.append({
                        'index': i,
                        'id': h.get('idInBook', i + 1),
                        'text': h.get('arabic', ''),
                        'narrator': h.get('english', {}).get('narrator', ''),
                        'abjad': abjad_value(h.get('arabic', ''))
                    })
        else:
            for i, h in enumerate(hadiths):
                arabic_text = h.get('arabic', '')
                if match_text(arabic_text, query, search_type):
                    book_results.append({
                        'index': i,
                        'id': h.get('idInBook', i + 1),
                        'text': arabic_text,
                        'narrator': h.get('english', {}).get('narrator', ''),
                        'abjad': abjad_value(arabic_text)
                    })

        if book_results:
            result['books'][book_id] = {
                'name': BOOKS[book_id],
                'results': book_results
            }

    return jsonify(result)

# ==================== 4. HTML ====================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الموسوعة الإسلامية الشاملة</title>
    <script src="https://unpkg.com/adhan/lib/bundles/adhan.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --main-green: #1a4d2e;
            --light-green: #e8f5e9;
            --gold: #c9a961;
            --bg: #f0f0e8;
            --text-dark: #1a1a1a;
        }
        body {
            font-family: 'Amiri', 'Segoe UI', Tahoma, sans-serif;
            background: var(--bg);
            min-height: 100vh;
            color: var(--text-dark);
        }

        .hadith-text, .ayah-line, .tafsir-panel, .search-result-item .res-text {
            font-family: 'Amiri', 'Traditional Arabic', serif;
            text-align: right;
            line-height: 2.2;
            word-spacing: 2px;
            letter-spacing: 0;
            white-space: normal;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .header {
            background: var(--main-green);
            color: white;
            padding: 15px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header h1 {
            font-size: 26px;
            color: var(--gold);
            margin-bottom: 12px;
        }
        .top-actions {
            display: flex;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .top-btn {
            background: #2d6a4f;
            color: white;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.2s;
            font-weight: bold;
        }
        .top-btn:hover { background: #40916c; }

        .info-bar {
            background: #2d6a4f;
            color: white;
            padding: 12px 20px;
            border-bottom: 2px solid var(--gold);
            text-align: center;
        }
        .info-time {
            font-size: 28px;
            font-weight: bold;
            color: var(--gold);
            margin-bottom: 5px;
            font-family: 'Segoe UI', sans-serif;
        }
        .info-date {
            font-size: 15px;
            margin-bottom: 10px;
            line-height: 1.9;
        }
        .info-date .hijri-date { color: var(--gold); font-weight: bold; font-size: 17px; }
        .info-date .greg-date { color: #e0f2e9; font-size: 15px; }
        .info-date .day-name { color: #ffffff; font-weight: bold; font-size: 17px; }
        .prayer-times {
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
            font-size: 14px;
        }
        .prayer-item {
            background: rgba(255,255,255,0.1);
            padding: 5px 12px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .prayer-item .name { color: var(--gold); font-weight: bold; }
        .prayer-item .time { font-weight: bold; }
        .location-info {
            font-size: 13px;
            color: #c9e6d0;
            margin-top: 5px;
        }

        .search-area {
            display: flex;
            gap: 6px;
            max-width: 1000px;
            margin: 12px auto 0;
            align-items: center;
            flex-wrap: wrap;
        }
        .search-area input {
            flex: 1;
            padding: 10px 15px;
            border-radius: 8px;
            border: none;
            font-size: 15px;
            font-family: inherit;
            min-width: 180px;
        }
        .search-area select {
            padding: 10px 12px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
            font-family: inherit;
            background: white;
            cursor: pointer;
            min-width: 170px;
        }
        .search-area button {
            background: var(--gold);
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            color: white;
            font-family: inherit;
            white-space: nowrap;
        }
        .search-area button:hover { background: #b8935a; }
        .search-area button.adv-btn { background: #27ae60; }
        .search-area button.adv-btn:hover { background: #1e8449; }

        .text-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            padding: 10px;
            background: #f5f5f0;
            border-bottom: 2px solid #ddd;
            flex-wrap: wrap;
        }
        .text-controls button {
            background: var(--main-green);
            color: white;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-family: inherit;
        }
        .text-controls .size-display {
            background: white;
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: bold;
            border: 1px solid #ccc;
            min-width: 40px;
            text-align: center;
        }

        .books-bar {
            background: var(--main-green);
            padding: 10px;
            overflow-x: auto;
            white-space: nowrap;
            scrollbar-width: thin;
        }
        .books-bar::-webkit-scrollbar { height: 8px; }
        .books-bar::-webkit-scrollbar-thumb { background: var(--gold); border-radius: 4px; }
        .book-btn {
            display: inline-block;
            background: white;
            color: var(--main-green);
            border: 2px solid white;
            padding: 8px 16px;
            margin: 0 4px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            font-family: inherit;
            transition: all 0.2s;
        }
        .book-btn:hover { background: #e8f5e9; }
        .book-btn.active {
            background: var(--gold);
            color: white;
            border-color: var(--gold);
        }

        .content-area {
            max-width: 1000px;
            margin: 20px auto;
            padding: 0 15px;
        }
        .hadith-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border: 2px solid #d4d4d0;
            margin-bottom: 20px;
        }
        .hadith-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--light-green);
            padding-bottom: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .hadith-book-name {
            color: var(--main-green);
            font-size: 18px;
            font-weight: bold;
        }
        .hadith-number {
            background: var(--main-green);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .narrator {
            color: #b8860b;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 15px;
            padding: 8px 12px;
            background: #fdf6e3;
            border-right: 4px solid var(--gold);
            border-radius: 4px;
        }
        .hadith-text {
            font-size: 24px;
            line-height: 2.2;
            color: var(--text-dark);
            padding: 15px;
            background: #fafaf5;
            border-radius: 8px;
            text-align: right;
        }
        .abjad-badge {
            display: inline-block;
            background: linear-gradient(135deg, #1a4d2e, #2d6a4f);
            color: var(--gold);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 12px;
        }

        .hadith-jump-bar {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin: 15px auto;
            padding: 12px 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            max-width: 500px;
            flex-wrap: wrap;
        }
        .hadith-jump-bar label {
            font-weight: bold;
            color: var(--main-green);
            font-size: 15px;
        }
        .hadith-jump-bar input {
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 15px;
            font-family: inherit;
            width: 140px;
            text-align: center;
        }
        .hadith-jump-bar input:focus {
            outline: none;
            border-color: var(--main-green);
        }
        .hadith-jump-bar button {
            background: var(--gold);
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
            font-weight: bold;
            font-family: inherit;
        }
        .hadith-jump-bar button:hover { background: #b8935a; }

        .surah-container {
            background: #fdfaf3;
            border: 3px double var(--gold);
            border-radius: 15px;
            padding: 25px;
        }
        .surah-header-bar {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .surah-header-bar h2 {
            font-size: 32px;
            color: var(--gold);
            margin-bottom: 8px;
        }
        .surah-header-bar .surah-info {
            font-size: 14px;
            opacity: 0.9;
        }
        .basmala {
            text-align: center;
            font-size: 28px;
            color: var(--main-green);
            font-weight: bold;
            margin: 20px 0;
            padding: 15px;
            border-top: 1px dashed var(--gold);
            border-bottom: 1px dashed var(--gold);
            font-family: 'Amiri', serif;
        }
        .ayah-line {
            font-size: 28px;
            line-height: 2.4;
            text-align: right;
            color: #1a3d2e;
            padding: 12px 18px;
            margin: 8px 0;
            border-radius: 8px;
            transition: background 0.2s;
            position: relative;
        }
        .ayah-line:hover { background: #f0f8f0; }
        .ayah-line.highlight {
            background: #fff3cd;
            box-shadow: 0 0 0 2px var(--gold);
        }
        .ayah-num-badge {
            display: inline-block;
            background: var(--gold);
            color: white;
            font-size: 14px;
            font-weight: bold;
            padding: 2px 10px;
            border-radius: 15px;
            margin: 0 8px;
            vertical-align: middle;
            font-family: sans-serif;
        }
        .ayah-actions {
            display: none;
            margin-top: 8px;
            gap: 8px;
            align-items: center;
        }
        .ayah-line:hover .ayah-actions { display: flex; }
        .ayah-action-btn {
            background: var(--main-green);
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            font-family: inherit;
        }
        .ayah-action-btn:hover { background: #40916c; }
        .ayah-abjad {
            background: #e8f5e9;
            color: var(--main-green);
            font-size: 12px;
            padding: 3px 9px;
            border-radius: 10px;
            font-weight: bold;
        }
        .tafsir-panel {
            display: none;
            background: #f0f9ff;
            border-right: 4px solid #28a745;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            font-size: 20px;
            line-height: 2.2;
            text-align: right;
        }
        .tafsir-panel.show { display: block; }
        .tafsir-title {
            color: #28a745;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 15px;
        }

        .quran-tools {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .quran-tools select {
            padding: 10px 15px;
            font-size: 16px;
            border-radius: 8px;
            border: 2px solid #ddd;
            font-family: inherit;
            flex: 1;
            min-width: 180px;
            cursor: pointer;
        }
        .quran-tools select:focus {
            outline: none;
            border-color: var(--main-green);
        }
        .quran-tools button {
            padding: 10px 20px;
            background: var(--main-green);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-family: inherit;
            font-size: 15px;
            font-weight: bold;
        }
        .quran-tools button:hover { background: #40916c; }

        .nav-buttons {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .nav-btn {
            background: var(--main-green);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            font-family: inherit;
            min-width: 120px;
            transition: all 0.2s;
        }
        .nav-btn:hover:not(:disabled) { background: #40916c; transform: translateY(-2px); }
        .nav-btn:disabled { background: #ccc; cursor: not-allowed; }

        .copy-buttons {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .copy-btn {
            background: var(--gold);
            color: white;
            border: none;
            padding: 10px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
            font-family: inherit;
            font-weight: bold;
        }
        .copy-btn:hover { background: #b8935a; }

        .search-results {
            max-height: 700px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .search-result-item {
            padding: 12px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: background 0.2s;
        }
        .search-result-item:hover { background: var(--light-green); }
        .search-result-item .res-num {
            color: var(--main-green);
            font-weight: bold;
            font-size: 13px;
        }
        .search-result-item .res-text {
            font-size: 19px;
            line-height: 2;
            margin-top: 5px;
        }
        .res-abjad-badge {
            background: #e8f5e9;
            color: #1a4d2e;
            padding: 2px 9px;
            border-radius: 10px;
            font-size: 12px;
            margin-right: 8px;
            font-weight: bold;
        }

        mark {
            background: #ffeb3b;
            color: #000;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: var(--main-green);
