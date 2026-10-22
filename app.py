import os
import re
import json
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# تحديد المسار الأساسي للمشروع لضمان قراءة الملفات بشكل صحيح
BASE_DIR = Path(__file__).resolve().parent

# ==================== 1. تحميل القرآن والتفسير ====================
QURAN_PATH = 'quran.json'
TAFSIR_PATH = 'tafsir_saadi.json'

def load_json(filepath):
    try:
        full_path = BASE_DIR / filepath
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

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

# ==================== دالة تحميل الكتب المحسنة ====================
def load_hadith_book(book_id):
    if book_id in loaded_books_cache:
        return loaded_books_cache[book_id]

    path = BASE_DIR / f"{book_id}.json"

    if not path.is_file():
        print(f"ملف الكتاب غير موجود: {path}")
        loaded_books_cache[book_id] = []
        return []

    try:
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("hadiths")

            if not isinstance(records, list):
                for key in ("data", "results", "records"):
                    if isinstance(data.get(key), list):
                        records = data[key]
                        break

            if not isinstance(records, list):
                records = []
        else:
            records = []

        normalized = []

        for i, item in enumerate(records):
            if not isinstance(item, dict):
                continue

            arabic = (
                item.get("arabic")
                or item.get("text")
                or item.get("hadith")
                or item.get("text_ar")
                or ""
            )

            if isinstance(arabic, dict):
                arabic = arabic.get("text", "")

            if not isinstance(arabic, str) or not arabic.strip():
                continue

            entry = dict(item)
            entry["arabic"] = arabic
            entry["idInBook"] = item.get(
                "idInBook",
                item.get("id", i + 1)
            )

            if not isinstance(entry.get("english"), dict):
                entry["english"] = {}

            normalized.append(entry)

        print(f"تم تحميل {BOOKS[book_id]}: {len(normalized)} حديث")
        loaded_books_cache[book_id] = normalized
        return normalized

    except (OSError, json.JSONDecodeError) as e:
        print(f"خطأ في قراءة {path.name}: {e}")
        loaded_books_cache[book_id] = []
        return []

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
            font-size: 18px;
        }

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 20px;
            overflow-y: auto;
        }
        .modal-overlay.show { display: flex; }
        .modal-content {
            background: white;
            border-radius: 15px;
            padding: 25px;
            max-width: 700px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
            border: 3px solid var(--gold);
        }
        .modal-close {
            position: absolute;
            top: 15px;
            left: 15px;
            background: #c0392b;
            color: white;
            border: none;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 20px;
            font-weight: bold;
        }
        .modal-content h2 {
            text-align: center;
            color: var(--main-green);
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--gold);
        }
        .adv-search-input {
            width: 100%;
            padding: 12px 15px;
            font-size: 16px;
            border-radius: 8px;
            border: 2px solid #ddd;
            font-family: inherit;
            margin-bottom: 15px;
        }
        .adv-search-input:focus {
            outline: none;
            border-color: var(--main-green);
        }
        .books-selection {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        .quick-select {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .quick-select button {
            padding: 8px 14px;
            background: var(--main-green);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-family: inherit;
            font-weight: bold;
        }
        .quick-select button:hover { background: #40916c; }
        .book-checkbox {
            display: flex;
            align-items: center;
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: background 0.2s;
            background: white;
            border-radius: 6px;
            margin-bottom: 4px;
        }
        .book-checkbox:hover { background: var(--light-green); }
        .book-checkbox input {
            margin-left: 12px;
            width: 20px;
            height: 20px;
            cursor: pointer;
            flex-shrink: 0;
        }
        .book-checkbox label {
            flex: 1;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
        }
        .book-checkbox.quran-special {
            background: #fff9e6;
            font-weight: bold;
            border: 2px solid var(--gold);
            border-radius: 8px;
            margin-bottom: 8px;
        }
        .adv-search-btn {
            width: 100%;
            padding: 14px;
            background: var(--gold);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 17px;
            font-weight: bold;
            font-family: inherit;
        }
        .adv-search-btn:hover { background: #b8935a; }

        .adv-type-select {
            width: 100%;
            padding: 12px 15px;
            font-size: 15px;
            border-radius: 8px;
            border: 2px solid #ddd;
            font-family: inherit;
            margin-bottom: 15px;
            background: white;
            cursor: pointer;
        }
        .adv-type-select:focus { outline: none; border-color: var(--main-green); }

        .adv-results-section {
            margin-bottom: 25px;
        }
        .adv-book-title {
            background: var(--main-green);
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 17px;
            font-weight: bold;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }
        .adv-book-title .count {
            background: var(--gold);
            color: white;
            padding: 2px 10px;
            border-radius: 15px;
            font-size: 13px;
        }

        /* Abjad result */
        .abjad-total {
            text-align: center;
            background: linear-gradient(135deg, #1a4d2e, #2d6a4f);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }
        .abjad-total .lbl { font-size: 15px; opacity: 0.9; }
        .abjad-total .val { font-size: 48px; color: var(--gold); font-weight: bold; }
        .abjad-chars {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            justify-content: center;
        }
        .abjad-char {
            background: #f0f8f0;
            border: 1px solid #c9e6d0;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 16px;
        }
        .abjad-char .ch { font-weight: bold; color: #1a4d2e; }
        .abjad-char .nm { color: #888; font-size: 13px; }
        .abjad-legend {
            margin-top: 20px;
            padding: 12px;
            background: #fff9e6;
            border-radius: 10px;
            border-right: 4px solid var(--gold);
            font-size: 14px;
            line-height: 1.9;
        }

        @media (max-width: 600px) {
            .header h1 { font-size: 20px; }
            .hadith-text { font-size: 20px; }
            .hadith-card { padding: 15px; }
            .nav-btn { padding: 10px 20px; font-size: 14px; min-width: 90px; }
            .book-btn { font-size: 12px; padding: 6px 12px; }
            .info-time { font-size: 22px; }
            .prayer-times { gap: 8px; font-size: 12px; }
            .ayah-line { font-size: 24px; line-height: 2.2; }
            .surah-header-bar h2 { font-size: 24px; }
            .top-btn { font-size: 12px; padding: 6px 10px; }
            .search-area button { padding: 10px 12px; font-size: 13px; }
            .search-area select { min-width: 130px; font-size: 13px; }
        }

        body.dark-mode {
            --bg: #1a1a1a;
            --text-dark: #e0e0e0;
        }
        body.dark-mode .hadith-card, body.dark-mode .modal-content, body.dark-mode .quran-tools { background: #2a2a2a; border-color: #444; color: #e0e0e0; }
        body.dark-mode .hadith-text { background: #333; color: #e0e0e0; }
        body.dark-mode .hadith-jump-bar { background: #2a2a2a; }
        body.dark-mode .hadith-jump-bar input { background: #333; color: white; border-color: #555; }
        body.dark-mode .hadith-jump-bar label { color: var(--gold); }
        body.dark-mode .surah-container { background: #222; border-color: var(--gold); }
        body.dark-mode .ayah-line { color: #e0e0e0; }
        body.dark-mode .ayah-line:hover { background: #2f2f2f; }
        body.dark-mode .text-controls { background: #2a2a2a; border-color: #444; }
        body.dark-mode .text-controls .size-display { background: #333; color: white; border-color: #555; }
        body.dark-mode .narrator { background: #3a3a2a; color: #e0c060; }
        body.dark-mode .search-area input { background: #333; color: white; }
        body.dark-mode .search-area select { background: #333; color: white; }
        body.dark-mode .books-selection { background: #333; }
        body.dark-mode .book-checkbox { background: #2a2a2a; border-color: #444; color: #e0e0e0; }
        body.dark-mode .book-checkbox:hover { background: #3a3a3a; }
        body.dark-mode .tafsir-panel { background: #1e3a2f; color: #ddd; }
        body.dark-mode .adv-search-input, body.dark-mode .adv-type-select { background: #333; color: white; }
        body.dark-mode .abjad-char { background: #2f2f2f; border-color: #444; color: #e0e0e0; }
        body.dark-mode .abjad-char .ch { color: var(--gold); }
        body.dark-mode .abjad-legend { background: #3a3a2a; color: #e0e0e0; }
    </style>
</head>
<body>

<div class="header">
    <h1>🕌 الموسوعة الإسلامية الشاملة 📚</h1>

    <div class="top-actions">
        <button class="top-btn" onclick="toggleDark()">🌙 ليلي</button>
        <button class="top-btn" onclick="detectLocation()">📍 تحديد الموقع</button>
        <button class="top-btn" onclick="toggleBookmark()">🔖 علامة</button>
        <button class="top-btn" onclick="showAbjad()">🔢 حساب الجُمّل</button>
        <button class="top-btn" onclick="showAbout()">ℹ️ حول التطبيق</button>
    </div>

    <div class="search-area">
        <input type="text" id="searchInput" placeholder="ابحث في الكتاب الحالي..." onkeydown="if(event.key==='Enter') doSearch()">
        <select id="searchType">
            <option value="word">🔤 كلمة كاملة</option>
            <option value="phrase">📝 جزء من جملة</option>
            <option value="exact">🎯 مطابق تماماً (مع التشكيل)</option>
            <option value="fuzzy">🌊 بحث مرن (بدون تشكيل)</option>
            <option value="number">🔢 رقم الحديث</option>
        </select>
        <button onclick="doSearch()" title="بحث">🔍 بحث</button>
        <button class="adv-btn" onclick="showAdvancedSearch()" title="بحث متقدم">🔎 بحث متقدم</button>
    </div>
</div>

<div class="info-bar">
    <div class="info-time" id="currentTime">--:--:--</div>
    <div class="info-date">
        <div class="day-name" id="dayName">جاري التحميل...</div>
        <div class="hijri-date" id="hijriDate">--</div>
        <div class="greg-date" id="gregorianDate">--</div>
    </div>
    <div class="prayer-times">
        <div class="prayer-item"><span class="name">الفجر</span><span class="time" id="fajrTime">--:--</span></div>
        <div class="prayer-item"><span class="name">الشروق</span><span class="time" id="sunriseTime">--:--</span></div>
        <div class="prayer-item"><span class="name">الظهر</span><span class="time" id="dhuhrTime">--:--</span></div>
        <div class="prayer-item"><span class="name">العصر</span><span class="time" id="asrTime">--:--</span></div>
        <div class="prayer-item"><span class="name">المغرب</span><span class="time" id="maghribTime">--:--</span></div>
        <div class="prayer-item"><span class="name">العشاء</span><span class="time" id="ishaTime">--:--</span></div>
    </div>
    <div class="location-info" id="locationInfo">📍 جاري تحديد الموقع...</div>
</div>

<div class="text-controls">
    <button onclick="changeFontSize(1)">➕ تكبير النص</button>
    <span class="size-display" id="fontSizeDisplay">24</span>
    <button onclick="changeFontSize(-1)">➖ تصغير النص</button>
    <button onclick="resetFontSize()">↺ الافتراضي</button>
</div>

<div class="books-bar">
    <button class="book-btn" onclick="selectQuran()" id="quranBtn">📖 القرآن الكريم</button>
    {% for key, value in books.items() %}
    <button class="book-btn" data-book="{{ key }}" onclick="selectBook('{{ key }}')">{{ value }}</button>
    {% endfor %}
</div>

<div class="content-area">
    <div id="content">
        <div class="loading">اختر كتاباً من الأعلى للبدء 🕌</div>
    </div>
</div>

<!-- ============ نافذة البحث المتقدم ============ -->
<div class="modal-overlay" id="advSearchModal" onclick="if(event.target===this) hideAdvancedSearch()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAdvancedSearch()">✕</button>
        <h2>🔎 البحث المتقدم</h2>

        <input type="text" class="adv-search-input" id="advSearchInput" placeholder="اكتب كلمة أو رقم للبحث..." onkeydown="if(event.key==='Enter') doAdvancedSearch()">

        <select class="adv-type-select" id="advSearchType">
            <option value="word">🔤 كلمة كاملة</option>
            <option value="phrase">📝 جزء من جملة</option>
            <option value="exact">🎯 مطابق تماماً (مع التشكيل)</option>
            <option value="fuzzy">🌊 بحث مرن (بدون تشكيل)</option>
            <option value="number">🔢 رقم الحديث</option>
        </select>

        <div class="books-selection">
            <div class="quick-select">
                <button onclick="selectAllBooks()">✅ كل الكتب</button>
                <button onclick="deselectAllBooks()">❌ مسح الكل</button>
                <button onclick="selectOnlyQuran()">📖 القرآن فقط</button>
                <button onclick="selectOnly9Books()">📚 الكتب التسعة</button>
            </div>

            <div class="book-checkbox quran-special">
                <input type="checkbox" id="chk_quran" value="quran">
                <label for="chk_quran">📖 القرآن الكريم كاملاً</label>
            </div>

            {% for key, value in books.items() %}
            <div class="book-checkbox">
                <input type="checkbox" id="chk_{{ key }}" class="book-chk" value="{{ key }}">
                <label for="chk_{{ key }}">{{ value }}</label>
            </div>
            {% endfor %}
        </div>

        <button class="adv-search-btn" onclick="doAdvancedSearch()">🔍 ابحث الآن</button>
    </div>
</div>

<!-- ============ نافذة حساب الجُمّل ============ -->
<div class="modal-overlay" id="abjadModal" onclick="if(event.target===this) hideAbjad()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAbjad()">✕</button>
        <h2>🔢 حساب الجُمّل (أبجد هوز)</h2>

        <textarea id="abjadInput" class="adv-search-input" rows="3"
                  placeholder="اكتب كلمة أو جملة عربية..."
                  style="resize:vertical;"></textarea>

        <button class="adv-search-btn" onclick="calcAbjad()">احسب</button>

        <div id="abjadResult" style="margin-top:20px;"></div>

        <div class="abjad-legend">
            <strong>نظام أبجد هوز:</strong><br>
            ا=1، ب=2، ج=3، د=4، ه=5، و=6، ز=7، ح=8، ط=9<br>
            ي=10، ك=20، ل=30، م=40، ن=50، س=60، ع=70، ف=80، ص=90<br>
            ق=100، ر=200، ش=300، ت=400، ث=500، خ=600، ذ=700، ض=800، ظ=900، غ=1000
        </div>
    </div>
</div>

<!-- ============ نافذة حول التطبيق ============ -->
<div class="modal-overlay" id="aboutModal" onclick="if(event.target===this) hideAbout()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAbout()">✕</button>
        <h2>🕌 حول التطبيق 📚</h2>

        <div style="background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%); color:white; padding:20px; border-radius:12px; text-align:center; margin-bottom:20px;">
            <div style="font-size:24px; color:var(--gold); font-weight:bold; margin-bottom:15px;">👤 حسان مارديني</div>
            <div style="font-size:14px; opacity:0.9; margin-bottom:10px;">مطوّر وصاحب التطبيق</div>
            <div style="display:flex; flex-direction:column; gap:10px;">
                <a href="tel:+905060917640" style="display:flex; align-items:center; justify-content:center; gap:10px; background:rgba(255,255,255,0.15); color:white; padding:10px 20px; border-radius:8px; text-decoration:none;">📞 <span>+90 506 091 7640</span></a>
                <a href="mailto:hassanmardinli21@gmail.com" style="display:flex; align-items:center; justify-content:center; gap:10px; background:rgba(255,255,255,0.15); color:white; padding:10px 20px; border-radius:8px; text-decoration:none;">📧 <span>hassanmardinli21@gmail.com</span></a>
                <a href="https://wa.me/905060917640" target="_blank" style="display:flex; align-items:center; justify-content:center; gap:10px; background:rgba(255,255,255,0.15); color:white; padding:10px 20px; border-radius:8px; text-decoration:none;">💬 <span>تواصل عبر واتساب</span></a>
            </div>
        </div>

        <div style="background:#f8f9fa; padding:15px; border-radius:10px; margin-bottom:15px; border-right:4px solid var(--gold);">
            <h3 style="color:var(--main-green); margin-bottom:10px;">📖 محتوى التطبيق</h3>
            <ul style="padding-right:20px; line-height:2;">
                <li>القرآن الكريم كاملاً (114 سورة)</li>
                <li>تفسير السعدي للآيات</li>
                <li>14 كتاباً من كتب الحديث النبوي</li>
                <li>مواقيت الصلاة والتاريخ الهجري</li>
                <li>حساب الجُمّل (أبجد هوز)</li>
                <li>بحث بالكلمة والجملة ورقم الحديث</li>
            </ul>
        </div>

        <div style="text-align:center; font-size:17px; line-height:2; color:#1a4d2e; font-weight:500; padding:15px; background:#fff9e6; border-radius:10px; border-right:4px solid var(--gold); margin-bottom:12px;">
            🤲 اللَّهُمَّ اجْعَلْ هَذَا الْعَمَلَ خَالِصًا لِوَجْهِكَ الْكَرِيمِ، وَانْفَعْ بِهِ الْمُسْلِمِينَ
        </div>
        <div style="text-align:center; font-size:17px; line-height:2; color:#1a4d2e; font-weight:500; padding:15px; background:#fff9e6; border-radius:10px; border-right:4px solid var(--gold); margin-bottom:12px;">
            🤲 اللَّهُمَّ اغْفِرْ لَنَا وَلِوَالِدِينَا وَلِوَالِدِي وَالِدِينَا، وَارْحَمْهُمْ كَمَا رَبَّوْنَا صِغَارًا
        </div>
        <div style="text-align:center; font-size:17px; line-height:2; color:#1a4d2e; font-weight:500; padding:15px; background:#fff9e6; border-radius:10px; border-right:4px solid var(--gold);">
            🤲 اللَّهُمَّ اجْعَلْهُ صَدَقَةً جَارِيَةً لِوَالِدَيَّ وَلِوَالِدِي وَالِدَيَّ، وَلِجَمِيعِ الْمُسْلِمِينَ
        </div>
    </div>
</div>

<script>
    let currentBook = null;
    let currentIndex = 0;
    let currentSurah = 1;
    let currentSurahData = null;
    let fontSize = 24;
    let bookmarks = JSON.parse(localStorage.getItem('bookmarks') || '{}');
    let currentSearchQuery = '';

    const ALL_SURAHS = {{ surahs|tojson }};

    const SYRIAN_MONTHS = [
        'كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران',
        'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول'
    ];

    const ARABIC_DAYS = [
        'الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'
    ];

    const HIJRI_MONTHS = [
        'محرّم', 'صفر', 'ربيع الأول', 'ربيع الآخر', 'جمادى الأولى', 'جمادى الآخرة',
        'رجب', 'شعبان', 'رمضان', 'شوّال', 'ذو القعدة', 'ذو الحجة'
    ];

    const ABJAD_MAP = {
        'ا':1,'أ':1,'إ':1,'آ':1,'ء':1,'ؤ':1,'ئ':1,
        'ب':2,'ج':3,'د':4,'ه':5,'ة':5,'و':6,'ز':7,'ح':8,'ط':9,
        'ي':10,'ى':10,'ك':20,'ل':30,'م':40,'ن':50,'س':60,'ع':70,'ف':80,'ص':90,
        'ق':100,'ر':200,'ش':300,'ت':400,'ث':500,'خ':600,'ذ':700,'ض':800,'ظ':900,'غ':1000
    };

    function toHijri(date) {
        let day = date.getDate();
        let month = date.getMonth() + 1;
        let year = date.getFullYear();

        let m = month;
        let y = year;
        let d = day;

        if (m < 3) {
            y -= 1;
            m += 12;
        }
        let a = Math.floor(y / 100);
        let b = 2 - a + Math.floor(a / 4);

        if (y < 1583) b = 0;
        if (y === 1582) {
            if (m > 10) b = -10;
            if (m === 10) {
                b = 0;
                if (d > 4) b = -10;
            }
        }

        let jd = Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + b - 1524;

        b = 0;
        if (jd > 2299160) {
            a = Math.floor((jd - 1867216.25) / 36524.25);
            b = 1 + a - Math.floor(a / 4);
        }
        let bb = jd + b + 1524;
        let cc = Math.floor((bb - 122.1) / 365.25);
        let dd = Math.floor(365.25 * cc);
        let ee = Math.floor((bb - dd) / 30.6001);

        day = bb - dd - Math.floor(30.6001 * ee);

        if (ee < 14) {
            month = ee - 1;
        } else {
            month = ee - 13;
        }
        if (month > 2) {
            year = cc - 4716;
        } else {
            year = cc - 4715;
        }

        let jdH = Math.floor((11 * year + 3) / 30) + 354 * year + Math.floor(30 * (month - 1)) -
                  Math.floor((month - 1) / 2) + day + 1948440 - 385;

        let l = jdH - 1948440 + 10632;
        let n = Math.floor((l - 1) / 10631);
        l = l - 10631 * n + 354;
        let j = Math.floor((10985 - l) / 5316) * Math.floor((50 * l) / 17719) +
                Math.floor(l / 5670) * Math.floor((43 * l) / 15238);
        l = l - Math.floor((30 - j) / 15) * Math.floor((17719 * j) / 50) -
            Math.floor(j / 16) * Math.floor((15238 * j) / 43) + 29;
        let hMonth = Math.floor((24 * l) / 709);
        let hDay = l - Math.floor((709 * hMonth) / 24);
        let hYear = 30 * n + j - 30;

        return { day: hDay, month: hMonth, year: hYear };
    }

    function updateTime() {
        const now = new Date();
        document.getElementById('currentTime').innerText = now.toLocaleTimeString('ar-SA', {
            hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
        });

        const dayIndex = now.getDay();
        document.getElementById('dayName').innerText = '📆 ' + ARABIC_DAYS[dayIndex];

        try {
            const h = toHijri(now);
            const hMonthName = HIJRI_MONTHS[h.month - 1] || '';
            document.getElementById('hijriDate').innerText = `🌙 ${h.day} ${hMonthName} ${h.year} هـ`;
        } catch(e) {
            document.getElementById('hijriDate').innerText = '🌙 التاريخ الهجري غير متاح';
        }

        const d = now.getDate();
        const m = now.getMonth();
        const y = now.getFullYear();
        document.getElementById('gregorianDate').innerText = `📅 ${d} ${SYRIAN_MONTHS[m]} ${y} م`;
    }
    setInterval(updateTime, 1000);
    updateTime();

    // ============ الموقع ============
    function detectLocation() {
        const locEl = document.getElementById('locationInfo');
        if (!navigator.geolocation) {
            locEl.innerText = '⚠️ المتصفح لا يدعم تحديد الموقع - استخدام مكة';
            fetchPrayerTimesByCoords(21.4225, 39.8262);
            return;
        }
        locEl.innerText = '📍 جاري تحديد الموقع...';
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                fetchPrayerTimesByCoords(lat, lng);
                reverseGeocode(lat, lng);
            },
            (error) => {
                let msg = '⚠️ فشل تحديد الموقع - استخدام مكة';
                if (error.code === 1) msg = '⚠️ تم رفض الإذن - استخدام مكة';
                else if (error.code === 2) msg = '⚠️ الموقع غير متاح - استخدام مكة';
                else if (error.code === 3) msg = '⚠️ انتهت المهلة - استخدام مكة';
                locEl.innerText = msg;
                fetchPrayerTimesByCoords(21.4225, 39.8262);
            },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 300000 }
        );
    }

    async function reverseGeocode(lat, lng) {
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=ar`);
            const data = await res.json();
            const city = data.address?.city || data.address?.town || data.address?.village || data.address?.state || '';
            const country = data.address?.country || '';
            document.getElementById('locationInfo').innerText = `📍 ${city}${city && country ? '، ' : ''}${country}`;
        } catch(e) {
            document.getElementById('locationInfo').innerText = `📍 ${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E`;
        }
    }

    async function fetchPrayerTimesByCoords(lat, lng) {
        try {
            const today = new Date();
            const dateStr = `${today.getDate()}-${today.getMonth() + 1}-${today.getFullYear()}`;
            const url = `https://api.aladhan.com/v1/timings/${dateStr}?latitude=${lat}&longitude=${lng}&method=4`;
            const res = await fetch(url);
            const data = await res.json();
            if (data.code === 200 && data.data && data.data.timings) {
                const t = data.data.timings;
                const clean = (s) => s ? s.split(' ')[0] : '--:--';
                document.getElementById('fajrTime').innerText = clean(t.Fajr);
                document.getElementById('sunriseTime').innerText = clean(t.Sunrise);
                document.getElementById('dhuhrTime').innerText = clean(t.Dhuhr);
                document.getElementById('asrTime').innerText = clean(t.Asr);
                document.getElementById('maghribTime').innerText = clean(t.Maghrib);
                document.getElementById('ishaTime').innerText = clean(t.Isha);
            } else {
                fallbackPrayerTimes(lat, lng);
            }
        } catch(e) {
            console.error('fetchPrayerTimesByCoords error:', e);
            fallbackPrayerTimes(lat, lng);
        }
    }

    function fallbackPrayerTimes(lat, lng) {
        try {
            if (typeof adhan === 'undefined') return;
            const coordinates = new adhan.Coordinates(lat, lng);
            const params = adhan.CalculationMethod.MuslimWorldLeague();
            const prayerTimes = new adhan.PrayerTimes(coordinates, new Date(), params);
            const fmt = (d) => d ? d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit', hour12: true }) : '--:--';
            document.getElementById('fajrTime').innerText = fmt(prayerTimes.fajr);
            document.getElementById('sunriseTime').innerText = fmt(prayerTimes.sunrise);
            document.getElementById('dhuhrTime').innerText = fmt(prayerTimes.dhuhr);
            document.getElementById('asrTime').innerText = fmt(prayerTimes.asr);
            document.getElementById('maghribTime').innerText = fmt(prayerTimes.maghrib);
            document.getElementById('ishaTime').innerText = fmt(prayerTimes.isha);
        } catch(e) { console.error('fallback error:', e); }
    }

    window.addEventListener('load', () => {
        setTimeout(detectLocation, 500);
    });

    // ============ الخط ============
    function changeFontSize(delta) {
        fontSize = Math.max(16, Math.min(48, fontSize + delta));
        document.getElementById('fontSizeDisplay').innerText = fontSize;
        document.querySelectorAll('.hadith-text, .ayah-line').forEach(el => {
            el.style.fontSize = fontSize + 'px';
        });
    }
    function resetFontSize() {
        fontSize = 24;
        document.getElementById('fontSizeDisplay').innerText = fontSize;
        document.querySelectorAll('.hadith-text, .ayah-line').forEach(el => {
            el.style.fontSize = fontSize + 'px';
        });
    }

    // ============ الوضع الليلي ============
    function toggleDark() {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
    }
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
    }

    // ============ العلامات ============
    function toggleBookmark() {
        if (!currentBook) return;
        const key = currentBook + '_' + currentIndex;
        if (bookmarks[key]) delete bookmarks[key];
        else bookmarks[key] = { book: currentBook, index: currentIndex, time: Date.now() };
        localStorage.setItem('bookmarks', JSON.stringify(bookmarks));
        alert(bookmarks[key] ? '✅ تمت إضافة علامة' : '🗑️ تم حذف العلامة');
    }

    // ============ حول التطبيق ============
    function showAbout() { document.getElementById('aboutModal').classList.add('show'); }
    function hideAbout() { document.getElementById('aboutModal').classList.remove('show'); }

    // ============ حساب الجُمّل ============
    function showAbjad() {
        document.getElementById('abjadModal').classList.add('show');
        const inp = document.getElementById('abjadInput');
        if (currentSearchQuery) inp.value = currentSearchQuery;
        inp.focus();
    }
    function hideAbjad() {
        document.getElementById('abjadModal').classList.remove('show');
    }
    async function calcAbjad() {
        const text = document.getElementById('abjadInput').value.trim();
        const resEl = document.getElementById('abjadResult');
        if (!text) { resEl.innerHTML = ''; return; }
        try {
            const res = await fetch(`/api/abjad?text=${encodeURIComponent(text)}`);
            const data = await res.json();
            let html = `<div class="abjad-total">
                            <div class="lbl">القيمة العددية (الجُمّل)</div>
                            <div class="val">${data.value}</div>
                        </div>`;
            if (data.breakdown && data.breakdown.length) {
                html += '<div class="abjad-chars">';
                data.breakdown.forEach(item => {
                    html += `<div class="abjad-char">
                                <span class="ch">${escapeHtml(item.char)}</span>
                                <span class="nm"> = ${item.value}</span>
                            </div>`;
                });
                html += '</div>';
            }
            resEl.innerHTML = html;
        } catch(e) {
            resEl.innerHTML = '<div style="color:red;text-align:center;">حدث خطأ</div>';
        }
    }

    // ============ البحث المتقدم ============
    function showAdvancedSearch() {
        document.getElementById('advSearchModal').classList.add('show');
        document.getElementById('advSearchType').value = document.getElementById('searchType').value;
    }
    function hideAdvancedSearch() {
        document.getElementById('advSearchModal').classList.remove('show');
    }

    function selectAllBooks() {
        document.querySelectorAll('.book-chk').forEach(chk => chk.checked = true);
        document.getElementById('chk_quran').checked = true;
    }
    function deselectAllBooks() {
        document.querySelectorAll('.book-chk').forEach(chk => chk.checked = false);
        document.getElementById('chk_quran').checked = false;
    }
    function selectOnlyQuran() {
        deselectAllBooks();
        document.getElementById('chk_quran').checked = true;
    }
    function selectOnly9Books() {
        deselectAllBooks();
        const nine = ['bukhari','muslim','abudawud','tirmidhi','nasai','ibnmajah','malik','ahmed','darimi'];
        document.querySelectorAll('.book-chk').forEach(chk => {
            if (nine.includes(chk.value)) chk.checked = true;
        });
    }

    async function doAdvancedSearch() {
        const query = document.getElementById('advSearchInput').value.trim();
        const type = document.getElementById('advSearchType').value;
        if (!query) { alert('اكتب كلمة أو رقم للبحث'); return; }

        const selectedBooks = [];
        document.querySelectorAll('.book-chk:checked').forEach(chk => selectedBooks.push(chk.value));
        const includeQuran = document.getElementById('chk_quran').checked;

        if (selectedBooks.length === 0 && !includeQuran) {
            alert('اختر كتاباً واحداً على الأقل');
            return;
        }

        hideAdvancedSearch();
        currentSearchQuery = (type === 'number') ? '' : query;
        const content = document.getElementById('content');
        content.innerHTML = '<div class="loading">جاري البحث...</div>';

        try {
            let url = `/api/search_advanced?query=${encodeURIComponent(query)}&type=${type}`;
            if (selectedBooks.length > 0) {
                url += `&books=${selectedBooks.join(',')}`;
            }
            if (includeQuran) url += `&quran=1`;

            const res = await fetch(url);
            const data = await res.json();

            let totalResults = 0;
            if (data.quran) totalResults += data.quran.length;
            if (data.books) {
                for (const k in data.books) totalResults += data.books[k].results.length;
            }

            if (totalResults === 0) {
                content.innerHTML = `<div class="hadith-card" style="text-align:center;">لا توجد نتائج لـ "${escapeHtml(query)}"</div>`;
                return;
            }

            let html = `<div class="hadith-card">
                            <div class="hadith-header">
                                <span class="hadith-book-name">🔎 نتائج البحث المتقدم</span>
                                <span class="hadith-number">${totalResults} نتيجة</span>
                            </div>
                            <div style="padding:10px;color:#666;font-size:14px;">كلمة البحث: <mark>${escapeHtml(query)}</mark></div>`;

            if (data.quran && data.quran.length > 0) {
                html += `<div class="adv-results-section">
                            <div class="adv-book-title">
                                <span>📖 القرآن الكريم</span>
                                <span class="count">${data.quran.length}</span>
                            </div>`;
                data.quran.forEach(item => {
                    html += `<div class="search-result-item" onclick="hideAdvancedSearch(); showSurah(${item.surah}).then(()=>scrollToAyah(${item.ayah}))">
                                <div class="res-num">سورة ${escapeHtml(item.surah_name)} - آية ${item.ayah}
                                    <span class="res-abjad-badge">جُمّل: ${item.abjad || 0}</span>
                                </div>
                                <div class="res-text">${safeHighlight(item.text, query)}</div>
                            </div>`;
                });
                html += `</div>`;
            }

            if (data.books) {
                for (const bookId in data.books) {
                    const bookData = data.books[bookId];
                    html += `<div class="adv-results-section">
                                <div class="adv-book-title">
                                    <span>📚 ${escapeHtml(bookData.name)}</span>
                                    <span class="count">${bookData.results.length}</span>
                                </div>`;
                    bookData.results.forEach(item => {
                        const preview = item.text.length > 250 ? item.text.substring(0, 250) + '...' : item.text;
                        html += `<div class="search-result-item" onclick="hideAdvancedSearch(); currentBook='${bookId}'; setActiveBook('${bookId}'); showHadith(${item.index})">
                                    <div class="res-num">📌 حديث رقم ${item.id}
                                        <span class="res-abjad-badge">جُمّل: ${item.abjad || 0}</span>
                                    </div>
                                    ${item.narrator ? `<div style="color:#b8860b;font-size:13px;margin:5px 0;">🎙️ ${escapeHtml(item.narrator)}</div>` : ''}
                                    <div class="res-text">${safeHighlight(preview, query)}</div>
                                </div>`;
                    });
                    html += `</div>`;
                }
            }

            html += `</div>`;
            content.innerHTML = html;
        } catch(e) {
            console.error(e);
            content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ في البحث</div>';
        }
    }

    // ============ الكتب ============
    function setActiveBook(bookId) {
        document.querySelectorAll('.book-btn').forEach(b => b.classList.remove('active'));
        if (bookId === 'quran') {
            const qb = document.getElementById('quranBtn');
            if (qb) qb.classList.add('active');
        } else {
            const btn = document.querySelector(`[data-book="${bookId}"]`);
            if (btn) btn.classList.add('active');
        }
    }

    async function selectBook(bookId) {
        currentBook = bookId;
        currentIndex = 0;
        currentSearchQuery = '';
        setActiveBook(bookId);
        await showHadith(0);
    }

    async function showHadith(index) {
        const content = document.getElementById('content');
        content.innerHTML = '<div class="loading">جاري التحميل...</div>';

        try {
            const res = await fetch(`/api/hadith?book=${currentBook}&index=${index}`);
            const data = await res.json();

            if (data.error) {
                content.innerHTML = `<div class="hadith-card" style="text-align:center;color:red;">${data.error}</div>`;
                return;
            }

            currentIndex = data.index;
            const isBookmarked = bookmarks[currentBook + '_' + currentIndex];
            const abjad = data.abjad !== undefined ? data.abjad : abjadOfText(data.text);

            content.innerHTML = `
                <div class="hadith-card">
                    <div class="hadith-header">
                        <span class="hadith-book-name">📚 ${getBookName(currentBook)}</span>
                        <span class="hadith-number">حديث رقم ${data.id} / ${data.total}</span>
                    </div>
                    ${data.narrator ? `<div class="narrator">🎙️ ${escapeHtml(data.narrator)}</div>` : ''}
                    <div class="abjad-badge">🔢 قيمة الجُمّل: ${abjad}</div>
                    <div class="hadith-text" id="hadithText" style="font-size:${fontSize}px;">${safeHighlight(data.text, currentSearchQuery)}</div>
                    <div class="copy-buttons">
                        <button class="copy-btn" onclick="copyHadith()">📋 نسخ الحديث</button>
                        <button class="copy-btn" onclick="toggleBookmark()">${isBookmarked ? '🔖 إزالة العلامة' : '🔖 علامة'}</button>
                        <button class="copy-btn" onclick="showAbjadForCurrentHadith()">🔢 حساب الجُمّل</button>
                    </div>
                </div>
                <div class="hadith-jump-bar">
                    <label>🔢 اذهب إلى حديث رقم:</label>
                    <input type="number" id="hadithJumpInput" min="1" max="${data.total}" placeholder="1 - ${data.total}" onkeydown="if(event.key==='Enter') jumpToHadith()">
                    <button onclick="jumpToHadith()">اذهب</button>
                </div>
                <div class="nav-buttons">
                    <button class="nav-btn" onclick="showHadith(${data.index - 1})" ${data.index === 0 ? 'disabled' : ''}>◀ السابق</button>
                    <button class="nav-btn" onclick="showHadith(0)">🏠 الأول</button>
                    <button class="nav-btn" onclick="showHadith(${data.index + 1})" ${data.index >= data.total - 1 ? 'disabled' : ''}>التالي ▶</button>
                </div>
            `;
        } catch (e) {
            content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ</div>';
        }
    }

    function showAbjadForCurrentHadith() {
        const el = document.getElementById('hadithText');
        if (!el) return;
        document.getElementById('abjadModal').classList.add('show');
        document.getElementById('abjadInput').value = el.innerText;
        calcAbjad();
    }

    async function jumpToHadith() {
        const input = document.getElementById('hadithJumpInput');
        if (!input) return;
        const id = parseInt(input.value);
        if (!id || id < 1) {
            alert('أدخل رقم حديث صحيح');
            return;
        }

        const content = document.getElementById('content');
        content.innerHTML = '<div class="loading">جاري البحث عن الحديث رقم ' + id + '...</div>';

        try {
            const res = await fetch(`/api/hadith_by_id?book=${currentBook}&id=${id}`);
            const data = await res.json();

            if (data.error) {
                content.innerHTML = `<div class="hadith-card" style="text-align:center;color:#c0392b;">
                    ⚠️ ${data.error}
                    <br><br>
                    <button class="nav-btn" onclick="showHadith(0)">العودة للأول</button>
                </div>`;
                return;
            }

            await showHadith(data.index);
        } catch(e) {
            content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ</div>';
        }
    }

    // ============ القرآن ============
    async function selectQuran() {
        currentBook = 'quran';
        setActiveBook('quran');
        await showSurah(1);
    }

    async function showSurah(surahNum) {
        const content = document.getElementById('content');
        content.innerHTML = '<div class="loading">جاري تحميل السورة...</div>';

        try {
            const res = await fetch(`/api/surah?surah=${surahNum}`);
            const data = await res.json();
            currentSurah = surahNum;
            currentSurahData = data;
            renderFullSurah();
        } catch (e) {
            content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ</div>';
        }
    }

    function renderFullSurah() {
        const content = document.getElementById('content');
        const data = currentSurahData;

        if (!data.ayahs || data.ayahs.length === 0) {
            content.innerHTML = '<div class="hadith-card" style="text-align:center;">لا توجد آيات</div>';
            return;
        }

        const surahsArray = ALL_SURAHS;

        let surahSelectHtml = '<select id="surahSelect" onchange="showSurah(this.value)">';
        surahsArray.forEach(s => {
            surahSelectHtml += `<option value="${s.id}" ${s.id === currentSurah ? 'selected' : ''}>${s.id}. سورة ${s.name}</option>`;
        });
        surahSelectHtml += '</select>';

        let ayahSelectHtml = '<select id="ayahSelect" onchange="scrollToAyah(this.value)">';
        ayahSelectHtml += '<option value="">📌 انتقل إلى آية...</option>';
        data.ayahs.forEach(a => {
            ayahSelectHtml += `<option value="${a.ayah}">آية ${a.ayah}</option>`;
        });
        ayahSelectHtml += '</select>';

        let ayahsHtml = '';
        if (currentSurah !== 1 && currentSurah !== 9) {
            ayahsHtml += `<div class="basmala">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</div>`;
        }

        data.ayahs.forEach(a => {
            const abjadVal = a.abjad !== undefined ? a.abjad : abjadOfText(a.text);
            ayahsHtml += `
                <div class="ayah-line" id="ayah-${a.ayah}" data-ayah="${a.ayah}">
                    <span>${safeHighlight(a.text, currentSearchQuery)}</span>
                    <span class="ayah-num-badge">${a.ayah}</span>
                    <div class="ayah-actions">
                        <button class="ayah-action-btn" onclick="copyAyah(${a.ayah})">📋 نسخ</button>
                        ${a.tafsir ? `<button class="ayah-action-btn" onclick="toggleTafsir(${a.ayah})">📖 التفسير</button>` : ''}
                        <span class="ayah-abjad">🔢 جُمّل: ${abjadVal}</span>
                    </div>
                    ${a.tafsir ? `<div class="tafsir-panel" id="tafsir-${a.ayah}"><div class="tafsir-title">📖 التفسير (السعدي):</div>${safeHighlight(a.tafsir, currentSearchQuery)}</div>` : ''}
                </div>
            `;
        });

        content.innerHTML = `
            <div class="quran-tools">
                ${surahSelectHtml}
                ${ayahSelectHtml}
                <button onclick="document.querySelectorAll('.tafsir-panel').forEach(t=>t.classList.toggle('show'))">📖 إظهار/إخفاء التفسير</button>
                <button onclick="copySurah()">📋 نسخ السورة</button>
            </div>
            <div class="surah-container">
                <div class="surah-header-bar">
                    <h2>سورة ${data.name}</h2>
                    <div class="surah-info">${data.ayahs.length} آية</div>
                </div>
                ${ayahsHtml}
            </div>
            <div class="nav-buttons">
                <button class="nav-btn" onclick="showSurah(${currentSurah - 1})" ${currentSurah <= 1 ? 'disabled' : ''}>◀ السورة السابقة</button>
                <button class="nav-btn" onclick="scrollToTop()">⬆ أعلى</button>
                <button class="nav-btn" onclick="showSurah(${currentSurah + 1})" ${currentSurah >= 114 ? 'disabled' : ''}>السورة التالية ▶</button>
            </div>
        `;
    }

    function scrollToAyah(ayahNum) {
        if (!ayahNum) return;
        setTimeout(() => {
            const el = document.getElementById('ayah-' + ayahNum);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.classList.add('highlight');
                setTimeout(() => el.classList.remove('highlight'), 4000);
            }
        }, 300);
    }

    function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }
    function toggleTafsir(n) {
        const el = document.getElementById('tafsir-' + n);
        if (el) el.classList.toggle('show');
    }
    function copyAyah(n) {
        const el = document.getElementById('ayah-' + n);
        if (!el) return;
        const text = el.querySelector('span').innerText;
        navigator.clipboard.writeText(text).then(() => alert('✅ تم نسخ الآية'));
    }
    function copySurah() {
        const c = document.querySelector('.surah-container');
        if (!c) return;
        let text = c.querySelector('h2').innerText + '\n\n';
        c.querySelectorAll('.ayah-line').forEach(l => {
            text += l.querySelector('span').innerText + ' (' + l.dataset.ayah + ')\n';
        });
        navigator.clipboard.writeText(text).then(() => alert('✅ تم نسخ السورة'));
    }

    // ============ البحث العادي ============
    async function doSearch() {
        const query = document.getElementById('searchInput').value.trim();
        const type = document.getElementById('searchType').value;
        if (!query) { alert('اكتب كلمة أو رقم للبحث'); return; }
        currentSearchQuery = (type === 'number') ? '' : query;

        if (!currentBook || currentBook === 'quran') {
            currentBook = 'bukhari';
            setActiveBook('bukhari');
        }

        const content = document.getElementById('content');
        content.innerHTML = '<div class="loading">جاري البحث...</div>';

        try {
            const res = await fetch(`/api/search?book=${currentBook}&query=${encodeURIComponent(query)}&type=${type}`);
            if (!res.ok) throw new Error('فشل الاتصال');
            const data = await res.json();

            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = `<div class="hadith-card" style="text-align:center;">لا توجد نتائج لـ "${escapeHtml(query)}" في ${getBookName(currentBook)}</div>`;
                return;
            }

            let html = `<div class="hadith-card">
                            <div class="hadith-header">
                                <span class="hadith-book-name">🔍 نتائج البحث في ${getBookName(currentBook)}</span>
                                <span class="hadith-number">${data.length} نتيجة</span>
                            </div>
                            <div class="search-results">`;
            data.forEach(item => {
                const preview = item.text.length > 250 ? item.text.substring(0, 250) + '...' : item.text;
                html += `<div class="search-result-item" onclick="showHadith(${item.index})">
                            <div class="res-num">📌 حديث رقم ${item.id}
                                <span class="res-abjad-badge">جُمّل: ${item.abjad || 0}</span>
                            </div>
                            ${item.narrator ? `<div style="color:#b8860b;font-size:13px;margin:5px 0;">🎙️ ${escapeHtml(item.narrator)}</div>` : ''}
                            <div class="res-text">${safeHighlight(preview, query)}</div>
                        </div>`;
            });
            html += '</div></div>';
            content.innerHTML = html;
        } catch(e) {
            content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ في البحث</div>';
        }
    }

    // ============ أدوات ============
    function getBookName(bookId) {
        const names = {
            'quran': 'القرآن الكريم',
            {% for key, value in books.items() %}
            '{{ key }}': '{{ value }}',
            {% endfor %}
        };
        return names[bookId] || bookId;
    }

    function copyHadith() {
        const el = document.getElementById('hadithText');
        if (!el) return;
        navigator.clipboard.writeText(el.innerText).then(() => {
            const btns = document.querySelectorAll('.copy-btn');
            btns.forEach(b => {
                if (b.innerText.includes('نسخ')) {
                    const o = b.innerText;
                    b.innerText = '✅ تم النسخ';
                    setTimeout(() => b.innerText = o, 1500);
                }
            });
        });
    }

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    function safeHighlight(text, query) {
        if (!query || !text) return escapeHtml(text || '');
        try {
            const safeText = String(text);
            const safeQuery = String(query);
            const parts = safeText.split(safeQuery);
            if (parts.length === 1) return escapeHtml(safeText);
            let result = '';
            for (let i = 0; i < parts.length; i++) {
                result += escapeHtml(parts[i]);
                if (i < parts.length - 1) {
                    result += '<mark>' + escapeHtml(safeQuery) + '</mark>';
                }
            }
            return result;
        } catch(e) {
            return escapeHtml(text);
        }
    }

    function abjadOfText(text) {
        if (!text) return 0;
        const clean = String(text).replace(/[\u064B-\u0652\u0670\u0640]/g, '');
        let total = 0;
        for (const ch of clean) {
            total += (ABJAD_MAP[ch] || 0);
        }
        return total;
    }
</script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
