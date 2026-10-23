import os
import re
import json
import uuid
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
SYNC_FILE = BASE_DIR / 'user_sync.json'

# ==================== 1. تحميل البيانات ====================
def load_json_from_anywhere(filepath):
    possible_paths = [BASE_DIR / filepath, BASE_DIR / 'data' / filepath, BASE_DIR / 'static' / filepath]
    for path in possible_paths:
        if path.is_file():
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading {path}: {e}")
                return None
    print(f"File not found: {filepath}")
    return None

quran_data = load_json_from_anywhere('quran.json')
tafsir_list = load_json_from_anywhere('tafsir_saadi.json')

surahs_list = []
quran_ayahs_map = {}

if isinstance(quran_data, list):
    for surah in quran_data:
        surah_num = surah.get('id')
        surahs_list.append({'id': surah_num, 'name': surah.get('name', '')})
        for ayah in surah.get('verses', []):
            quran_ayahs_map[(surah_num, ayah.get('id'))] = ayah.get('text', '')

tafsir_map = {}
if isinstance(tafsir_list, list):
    for surah_obj in tafsir_list:
        surah_name = surah_obj.get('surah_name', '').strip()
        surah_num = next((i for i, s in enumerate(surahs_list, 1) if s['name'] == surah_name), None)
        if surah_num:
            for ayah in surah_obj.get('ayahs', []):
                tafsir_map[(surah_num, ayah.get('number', 0))] = ayah.get('text', '')

# ==================== 2. حساب الجُمّل والبحث ====================
ABJAD_VALUES = {'ا':1,'أ':1,'إ':1,'آ':1,'ء':1,'ؤ':1,'ئ':1,'ب':2,'ج':3,'د':4,'ه':5,'ة':5,'و':6,'ز':7,'ح':8,'ط':9,'ي':10,'ى':10,'ك':20,'ل':30,'م':40,'ن':50,'س':60,'ع':70,'ف':80,'ص':90,'ق':100,'ر':200,'ش':300,'ت':400,'ث':500,'خ':600,'ذ':700,'ض':800,'ظ':900,'غ':1000}
_DIACRITICS = re.compile(r'[\u064B-\u0652\u0670\u0640\u06D6-\u06ED]')
_WORD_SPLIT = re.compile(r'[^\u0621-\u064A]+')

def strip_diacritics(text): 
    return _DIACRITICS.sub('', text or '')

def normalize_arabic(text):
    if not text: return ''
    text = strip_diacritics(text)
    return text.replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ة','ه').replace('ى','ي').replace('ؤ','و').replace('ئ','ي')

def abjad_value(text): 
    return sum(ABJAD_VALUES.get(ch, 0) for ch in strip_diacritics(text))

def abjad_breakdown(text): 
    return [{'char': ch, 'value': ABJAD_VALUES[ch]} for ch in strip_diacritics(text) if ch in ABJAD_VALUES]

def match_text(text, query, search_type):
    if not text or not query: return False
    
    norm_text = normalize_arabic(text)
    norm_query = normalize_arabic(query)
    
    if search_type == 'exact': 
        return query in text
    if search_type == 'phrase' or search_type == 'word': 
        return norm_query in norm_text
    if search_type == 'fuzzy': 
        words = _WORD_SPLIT.split(norm_query)
        return all(w in norm_text for w in words if w)
        
    return norm_query in norm_text

# ==================== 3. الكتب ====================
BOOKS = {
    'bukhari':'صحيح البخاري',
    'muslim':'صحيح مسلم',
    'abudawud':'سنن أبي داود',
    'tirmidhi':'جامع الترمذي',
    'nasai':'سنن النسائي',
    'ibnmajah':'سنن ابن ماجه',
    'malik':'موطأ مالك',
    'ahmed':'مسند أحمد',
    'darimi':'سنن الدارمي',
    'riyad_assalihin':'رياض الصالحين',
    'aladab_almufrad':'الأدب المفرد',
    'bulugh_almaram':'بلوغ المرام',
    'mishkat_almasabih':'مشكاة المصابيح',
    'shamail_muhammadiyah':'الشمائل المحمدية'
}
loaded_books_cache = {}

def load_hadith_book(book_id):
    if book_id in loaded_books_cache: return loaded_books_cache[book_id]
    path = BASE_DIR / 'data' / f'{book_id}.json'
    if not path.is_file(): path = BASE_DIR / f'{book_id}.json'
    if not path.is_file(): return []
    try:
        with open(path, 'r', encoding='utf-8-sig') as f: data = json.load(f)
        records = data.get('hadiths', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        normalized = []
        for i, item in enumerate(records):
            if isinstance(item, dict):
                arabic = item.get('arabic') or item.get('text') or item.get('hadith') or ''
                if arabic.strip():
                    entry = dict(item)
                    entry['arabic'] = arabic
                    entry['idInBook'] = item.get('idInBook', item.get('id', i+1))
                    normalized.append(entry)
        loaded_books_cache[book_id] = normalized
        return normalized
    except: return []

# ==================== 4. مسارات المزامنة ====================
def get_sync_data():
    if SYNC_FILE.is_file():
        try:
            with open(SYNC_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_sync_data(data):
    with open(SYNC_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/api/sync', methods=['GET', 'POST'])
def sync():
    if request.method == 'POST':
        data = request.json
        user_id = data.get('userId')
        if not user_id: return jsonify({'error': 'No ID'}), 400
        sync_data = get_sync_data()
        sync_data[user_id] = data.get('bookmarks', [])
        save_sync_data(sync_data)
        return jsonify({'status': 'ok'})
    else:
        user_id = request.args.get('userId')
        sync_data = get_sync_data()
        return jsonify({'bookmarks': sync_data.get(user_id, [])})

# ==================== 5. المسارات الأساسية ====================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, books=BOOKS, surahs=surahs_list)

@app.route('/api/abjad')
def api_abjad():
    text = request.args.get('text', '').strip()
    return jsonify({'value': abjad_value(text), 'breakdown': abjad_breakdown(text)})

@app.route('/api/hadith')
def get_hadith():
    book_id = request.args.get('book', 'bukhari')
    index = request.args.get('index', 0, type=int)
    hadiths = load_hadith_book(book_id)
    if not hadiths or index >= len(hadiths): return jsonify({'error': 'حديث غير موجود'})
    h = hadiths[index]
    return jsonify({'index': index, 'total': len(hadiths), 'id': h.get('idInBook'), 'text': h.get('arabic'), 'narrator': h.get('english', {}).get('narrator', ''), 'abjad': abjad_value(h.get('arabic'))})

@app.route('/api/hadith_by_id')
def get_hadith_by_id():
    book_id = request.args.get('book', 'bukhari')
    hadith_id = request.args.get('id', 0, type=int)
    hadiths = load_hadith_book(book_id)
    for i, h in enumerate(hadiths):
        if h.get('idInBook') == hadith_id:
            return jsonify({'index': i, 'total': len(hadiths), 'id': hadith_id, 'text': h.get('arabic'), 'narrator': h.get('english', {}).get('narrator', ''), 'abjad': abjad_value(h.get('arabic'))})
    return jsonify({'error': 'الحديث غير موجود'})

@app.route('/api/surah')
def get_surah():
    surah_num = request.args.get('surah', 1, type=int)
    ayahs = [{'ayah': a, 'text': t, 'tafsir': tafsir_map.get((surah_num, a), ''), 'abjad': abjad_value(t)} for (s, a), t in sorted(quran_ayahs_map.items()) if s == surah_num]
    surah_name = next((s['name'] for s in surahs_list if s['id'] == surah_num), '')
    return jsonify({'surah': surah_num, 'name': surah_name, 'ayahs': ayahs})

@app.route('/api/search')
def search():
    book_id = request.args.get('book', 'quran')
    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'fuzzy')
    if not query: return jsonify([])
    
    if book_id == 'quran':
        results = []
        for (s, a), text in quran_ayahs_map.items():
            if match_text(text, query, search_type):
                surah_name = next((x['name'] for x in surahs_list if x['id'] == s), '')
                results.append({'surah': s, 'surah_name': surah_name, 'ayah': a, 'text': text, 'abjad': abjad_value(text)})
        return jsonify(results)
    
    if book_id not in BOOKS: return jsonify([])
    hadiths = load_hadith_book(book_id)
    results = []
    for i, h in enumerate(hadiths):
        arabic_text = h.get('arabic', '')
        if match_text(arabic_text, query, search_type):
            results.append({'index': i, 'id': h.get('idInBook', i + 1), 'text': arabic_text, 'narrator': h.get('english', {}).get('narrator', ''), 'abjad': abjad_value(arabic_text)})
    return jsonify(results)

@app.route('/api/search_advanced')
def search_advanced():
    query = request.args.get('query', '').strip()
    books_param = request.args.get('books', '')
    include_quran = request.args.get('quran', '0') == '1'
    search_type = request.args.get('type', 'fuzzy')
    if not query: return jsonify({'books': {}, 'quran': []})
    
    result = {'books': {}, 'quran': []}
    
    if include_quran:
        quran_results = []
        for (s, a), text in quran_ayahs_map.items():
            if match_text(text, query, search_type):
                surah_name = next((x['name'] for x in surahs_list if x['id'] == s), '')
                quran_results.append({'surah': s, 'surah_name': surah_name, 'ayah': a, 'text': text, 'abjad': abjad_value(text)})
        result['quran'] = quran_results
        
    selected = []
    if books_param == 'all': 
        selected = list(BOOKS.keys())
    elif books_param: 
        selected = [b.strip() for b in books_param.split(',') if b.strip() in BOOKS]
        
    for book_id in selected:
        hadiths = load_hadith_book(book_id)
        book_results = []
        for i, h in enumerate(hadiths):
            arabic_text = h.get('arabic', '')
            if match_text(arabic_text, query, search_type):
                book_results.append({'index': i, 'id': h.get('idInBook', i + 1), 'text': arabic_text, 'narrator': h.get('english', {}).get('narrator', ''), 'abjad': abjad_value(arabic_text)})
        if book_results:
            result['books'][book_id] = {'name': BOOKS[book_id], 'results': book_results}
            
    return jsonify(result)

# ==================== 6. HTML Template ====================
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
        :root { --main-green: #1a4d2e; --light-green: #e8f5e9; --gold: #c9a961; --bg: #f0f0e8; --text-dark: #1a1a1a; }
        body { font-family: 'Amiri', 'Segoe UI', Tahoma, sans-serif; background: var(--bg); min-height: 100vh; color: var(--text-dark); }
        .hadith-text, .ayah-line, .tafsir-panel, .search-result-item .res-text { font-family: 'Amiri', 'Traditional Arabic', serif; text-align: right; line-height: 2.2; word-spacing: 2px; letter-spacing: 0; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; }
        
        .header { background: var(--main-green); color: white; padding: 15px 20px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.2); position: sticky; top: 0; z-index: 100; }
        .header h1 { font-size: 26px; color: var(--gold); margin-bottom: 12px; }
        .top-actions { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
        .top-btn { background: #2d6a4f; color: white; border: 1px solid rgba(255,255,255,0.2); padding: 8px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; font-family: inherit; transition: all 0.2s; font-weight: bold; }
        .top-btn:hover { background: #40916c; }
        .top-btn.adv { background: #27ae60; }
        .top-btn.adv:hover { background: #219653; }
        
        .info-bar { background: #2d6a4f; color: white; padding: 12px 20px; border-bottom: 2px solid var(--gold); text-align: center; }
        .info-time { font-size: 28px; font-weight: bold; color: var(--gold); margin-bottom: 5px; font-family: 'Segoe UI', sans-serif; }
        .info-date { font-size: 15px; margin-bottom: 10px; line-height: 1.9; }
        .info-date .hijri-date { color: var(--gold); font-weight: bold; font-size: 17px; }
        .info-date .greg-date { color: #e0f2e9; font-size: 15px; }
        .info-date .day-name { color: #ffffff; font-weight: bold; font-size: 17px; }
        .prayer-times { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; font-size: 14px; }
        .prayer-item { background: rgba(255,255,255,0.1); padding: 5px 12px; border-radius: 20px; display: flex; align-items: center; gap: 5px; }
        .prayer-item .name { color: var(--gold); font-weight: bold; }
        .prayer-item .time { font-weight: bold; }
        .location-info { font-size: 13px; color: #c9e6d0; margin-top: 5px; }
        
        .search-area { display: flex; gap: 6px; max-width: 1000px; margin: 12px auto 0; align-items: center; flex-wrap: wrap; }
        .search-area input { flex: 1; padding: 10px 15px; border-radius: 8px; border: none; font-size: 15px; font-family: inherit; min-width: 180px; }
        .search-area select { padding: 10px 12px; border-radius: 8px; border: none; font-size: 14px; font-family: inherit; background: white; cursor: pointer; min-width: 170px; }
        .search-area button { background: var(--gold); border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold; color: white; font-family: inherit; white-space: nowrap; }
        .search-area button:hover { background: #b8935a; }
        
        .text-controls { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 10px; background: #f5f5f0; border-bottom: 2px solid #ddd; flex-wrap: wrap; }
        .text-controls button { background: var(--main-green); color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 14px; font-family: inherit; }
        .text-controls .size-display { background: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; border: 1px solid #ccc; min-width: 40px; text-align: center; }
        
        .books-bar { background: var(--main-green); padding: 10px; overflow-x: auto; white-space: nowrap; scrollbar-width: thin; }
        .books-bar::-webkit-scrollbar { height: 8px; }
        .books-bar::-webkit-scrollbar-thumb { background: var(--gold); border-radius: 4px; }
        .book-btn { display: inline-block; background: white; color: var(--main-green); border: 2px solid white; padding: 8px 16px; margin: 0 4px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; font-family: inherit; transition: all 0.2s; }
        .book-btn:hover { background: #e8f5e9; }
        .book-btn.active { background: var(--gold); color: white; border-color: var(--gold); }
        
        .content-area { max-width: 1000px; margin: 20px auto; padding: 0 15px; }
        .hadith-card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 2px solid #d4d4d0; margin-bottom: 20px; }
        .hadith-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--light-green); padding-bottom: 10px; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        .hadith-book-name { color: var(--main-green); font-size: 18px; font-weight: bold; }
        .hadith-number { background: var(--main-green); color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; }
        .narrator { color: #b8860b; font-size: 16px; font-weight: bold; margin-bottom: 15px; padding: 8px 12px; background: #fdf6e3; border-right: 4px solid var(--gold); border-radius: 4px; }
        .hadith-text { font-size: 24px; line-height: 2.2; color: var(--text-dark); padding: 15px; background: #fafaf5; border-radius: 8px; text-align: right; }
        .abjad-badge { display: inline-block; background: linear-gradient(135deg, #1a4d2e, #2d6a4f); color: var(--gold); padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: bold; margin-bottom: 12px; }
        
        .surah-container { background: #fdfaf3; border: 3px double var(--gold); border-radius: 15px; padding: 25px; }
        .surah-header-bar { text-align: center; padding: 20px; background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%); color: white; border-radius: 10px; margin-bottom: 20px; }
        .surah-header-bar h2 { font-size: 32px; color: var(--gold); margin-bottom: 8px; }
        .surah-header-bar .surah-info { font-size: 14px; opacity: 0.9; }
        .basmala { text-align: center; font-size: 28px; color: var(--main-green); font-weight: bold; margin: 20px 0; padding: 15px; border-top: 1px dashed var(--gold); border-bottom: 1px dashed var(--gold); font-family: 'Amiri', serif; }
        .ayah-line { font-size: 28px; line-height: 2.4; text-align: right; color: #1a3d2e; padding: 12px 18px; margin: 8px 0; border-radius: 8px; transition: background 0.2s; position: relative; }
        .ayah-line:hover { background: #f0f8f0; }
        .ayah-line.highlight { background: #fff3cd; box-shadow: 0 0 0 2px var(--gold); }
        .ayah-num-badge { display: inline-block; background: var(--gold); color: white; font-size: 14px; font-weight: bold; padding: 2px 10px; border-radius: 15px; margin: 0 8px; vertical-align: middle; font-family: sans-serif; }
        .ayah-actions { display: none; margin-top: 8px; gap: 8px; align-items: center; }
        .ayah-line:hover .ayah-actions { display: flex; }
        .ayah-action-btn { background: var(--main-green); color: white; border: none; padding: 4px 12px; border-radius: 5px; cursor: pointer; font-size: 12px; font-family: inherit; }
        .ayah-action-btn:hover { background: #40916c; }
        .ayah-abjad { background: #e8f5e9; color: var(--main-green); font-size: 12px; padding: 3px 9px; border-radius: 10px; font-weight: bold; }
        .tafsir-panel { display: none; background: #f0f9ff; border-right: 4px solid #28a745; padding: 15px; margin: 10px 0; border-radius: 8px; font-size: 20px; line-height: 2.2; text-align: right; }
        .tafsir-panel.show { display: block; }
        .tafsir-title { color: #28a745; font-weight: bold; margin-bottom: 8px; font-size: 15px; }
        
        .nav-buttons { display: flex; justify-content: center; gap: 10px; margin: 20px 0; flex-wrap: wrap; }
        .nav-btn { background: var(--main-green); color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; font-family: inherit; min-width: 120px; transition: all 0.2s; }
        .nav-btn:hover:not(:disabled) { background: #40916c; transform: translateY(-2px); }
        .nav-btn:disabled { background: #ccc; cursor: not-allowed; }
        
        .back-to-index-btn { display: none; width: 100%; background: #27ae60; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin-bottom: 15px; text-align: center; font-family: inherit; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .back-to-index-btn:hover { background: #219653; }
        
        .search-results { max-height: 700px; overflow-y: auto; margin-top: 15px; background: white; border-radius: 12px; padding: 15px; border: 2px solid #ddd; }
        .search-result-item { padding: 12px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; border-radius: 6px; }
        .search-result-item:hover { background: var(--light-green); }
        .search-result-item .res-num { color: var(--main-green); font-weight: bold; font-size: 14px; margin-bottom: 4px; }
        .search-result-item .res-text { font-size: 19px; line-height: 2; }
        .res-abjad-badge { background: #e8f5e9; color: #1a4d2e; padding: 2px 9px; border-radius: 10px; font-size: 12px; margin-right: 8px; font-weight: bold; }
        
        mark { background: #ffeb3b; color: #000; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
        .loading { text-align: center; padding: 40px; color: var(--main-green); font-size: 18px; }
        
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; padding: 20px; overflow-y: auto; }
        .modal-overlay.show { display: flex; }
        .modal-content { background: white; border-radius: 15px; padding: 25px; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative; border: 3px solid var(--gold); }
        .modal-close { position: absolute; top: 15px; left: 15px; background: #c0392b; color: white; border: none; width: 35px; height: 35px; border-radius: 50%; cursor: pointer; font-size: 20px; font-weight: bold; }
        .modal-content h2 { text-align: center; color: var(--main-green); font-size: 24px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid var(--gold); }
        
        body.dark-mode { --bg: #1a1a1a; --text-dark: #e0e0e0; }
        body.dark-mode .hadith-card, body.dark-mode .modal-content, body.dark-mode .search-results { background: #2a2a2a; border-color: #444; color: #e0e0e0; }
        body.dark-mode .hadith-text { background: #333; color: #e0e0e0; }
        body.dark-mode .surah-container { background: #222; border-color: var(--gold); }
        body.dark-mode .ayah-line { color: #e0e0e0; }
        body.dark-mode .ayah-line:hover { background: #2f2f2f; }
        body.dark-mode .search-result-item:hover { background: #333; }
    </style>
</head>
<body>

<div class="header">
    <h1>🕌 الموسوعة الإسلامية الشاملة 📚</h1>
    <div class="top-actions">
        <button class="top-btn" onclick="toggleDark()">🌙 ليلي</button>
        <button class="top-btn" onclick="detectLocation()">📍 تحديد الموقع</button>
        <button class="top-btn adv" onclick="showAdvancedSearch()">🔍 بحث متقدم</button>
        <button class="top-btn" onclick="showBookmarks()">🔖 علاماتي</button>
        <button class="top-btn" onclick="showAbjad()">🔢 حساب الجُمّل</button>
        <button class="top-btn" onclick="showHistory()">📜 سجل البحث</button>
        <button class="top-btn" onclick="showAbout()">ℹ️ حول التطبيق</button>
    </div>
    <div class="search-area">
        <input type="text" id="searchInput" placeholder="ابحث في الكتاب الحالي..." onkeydown="if(event.key==='Enter') doSearch()">
        <select id="searchType">
            <option value="fuzzy">🌊 بحث مرن (بدون تشكيل)</option>
            <option value="word">🔤 كلمة كاملة</option>
            <option value="phrase">📝 جزء من جملة</option>
            <option value="exact">🎯 مطابق تماماً (مع التشكيل)</option>
        </select>
        <button onclick="doSearch()" title="بحث">🔍 بحث</button>
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
    <button class="back-to-index-btn" id="backToIndexBtn" onclick="restoreSearchResultsIndex()">📋 العودة إلى فهرس نتائج البحث</button>
    <div id="content">
        <div class="loading">اختر كتاباً من الأعلى للبدء 🕌</div>
    </div>
</div>

<!-- نافذة البحث المتقدم الشامل -->
<div class="modal-overlay" id="advSearchModal" onclick="if(event.target===this) hideAdvancedSearch()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAdvancedSearch()">✕</button>
        <h2>🔍 البحث المتقدم في الموسوعة</h2>
        <input type="text" id="advQuery" placeholder="اكتب كلمة أو عبارة للبحث الشامل..." style="width:100%; padding:12px; border-radius:8px; border:1px solid #ccc; font-size:16px; margin-bottom:15px; font-family:inherit;">
        
        <div style="margin-bottom: 15px; background:#f9f9f5; padding:12px; border-radius:8px;">
            <label style="font-weight: bold; color: var(--main-green); display:block; margin-bottom:8px;">اختر نطاق البحث:</label>
            <div style="margin-bottom:8px;"><label><input type="checkbox" id="advIncludeQuran" checked> 📖 القرآن الكريم</label></div>
            <div style="margin-bottom:8px;"><label><input type="checkbox" id="advIncludeAllBooks" checked onchange="toggleAllBooks(this)"> 📚 تحديد/إلغاء جميع كتب الحديث</label></div>
            <div id="booksCheckboxesContainer" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap:6px; max-height:160px; overflow-y:auto; padding-top:6px; border-top:1px dashed #ddd;">
                {% for key, value in books.items() %}
                <label style="font-size:13px;"><input type="checkbox" class="book-chk" value="{{ key }}" checked> {{ value }}</label>
                {% endfor %}
            </div>
        </div>
        
        <button style="width:100%; padding:14px; background:var(--gold); color:white; border:none; border-radius:8px; cursor:pointer; font-size:17px; font-weight:bold; font-family:inherit;" onclick="executeAdvancedSearch()">بحث شامل</button>
    </div>
</div>

<!-- نافذة العلامات المرجعية -->
<div class="modal-overlay" id="bookmarksModal" onclick="if(event.target===this) hideBookmarks()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideBookmarks()">✕</button>
        <h2>🔖 العلامات المحفوظة</h2>
        <div id="bookmarksList" style="max-height: 400px; overflow-y: auto;"></div>
    </div>
</div>

<!-- نافذة سجل البحث -->
<div class="modal-overlay" id="historyModal" onclick="if(event.target===this) hideHistory()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideHistory()">✕</button>
        <h2>📜 سجل البحث</h2>
        <div id="historyList" style="max-height: 400px; overflow-y: auto;"></div>
        <button style="margin-top:10px; background:#c0392b; color:white; padding:10px; border:none; border-radius:6px; cursor:pointer; width:100%;" onclick="clearHistory()">🗑️ مسح السجل</button>
    </div>
</div>

<!-- نافذة حساب الجُمّل -->
<div class="modal-overlay" id="abjadModal" onclick="if(event.target===this) hideAbjad()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAbjad()">✕</button>
        <h2>🔢 حساب الجُمّل (أبجد هوز)</h2>
        <textarea id="abjadInput" style="width:100%; padding:10px; border-radius:8px; border:1px solid #ccc;" rows="3" placeholder="اكتب كلمة أو جملة عربية..."></textarea>
        <button style="width:100%; margin-top:10px; padding:12px; background:var(--gold); color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;" onclick="calcAbjad()">احسب</button>
        <div id="abjadResult" style="margin-top:20px;"></div>
    </div>
</div>

<!-- نافذة حول التطبيق -->
<div class="modal-overlay" id="aboutModal" onclick="if(event.target===this) hideAbout()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAbout()">✕</button>
        <h2>🕌 حول التطبيق 📚</h2>
        <div style="background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%); color:white; padding:20px; border-radius:12px; text-align:center; margin-bottom:20px;">
            <h3 style="color:var(--gold); margin-bottom:10px;">الموسوعة الإسلامية الشاملة</h3>
            <p>تطبيق شامل ومتقدم للقرآن الكريم، تفسير السعدي، أمهات كتب الحديث النبوي الشريف، أوقات الصلاة، حساب الجُمّل، والفهرس الذكي لنتائج البحث.</p>
        </div>
    </div>
</div>

<script>
let currentBook = 'quran';
let currentIndex = 0;
let totalHadiths = 0;
let fontSize = parseInt(localStorage.getItem('fontSize')) || 24;
let currentSurahNum = 1;
let lastSearchResultsHTML = '';
let userSyncId = localStorage.getItem('userSyncId') || 'user_' + Math.random().toString(36).substr(2, 9);
localStorage.setItem('userSyncId', userSyncId);

document.addEventListener('DOMContentLoaded', () => {
    applyFontSize(fontSize);
    initPrayerTimes();
    setInterval(updateClock, 1000);
    updateClock();
    selectQuran();
});

function updateClock() {
    const now = new Date();
    document.getElementById('currentTime').textContent = now.toLocaleTimeString('ar-SA');
    const days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
    document.getElementById('dayName').textContent = days[now.getDay()];
    
    document.getElementById('gregorianDate').textContent = now.toLocaleDateString('ar-SA-u-nu-latn', { year: 'numeric', month: 'long', day: 'numeric' }) + ' م';
    
    try {
        const hijriFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-islamic-umalqura-nu-latn', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        document.getElementById('hijriDate').textContent = hijriFormatter.format(now) + ' هـ';
    } catch(e) {
        document.getElementById('hijriDate').textContent = '';
    }
}

function initPrayerTimes(lat = 41.0082, lng = 28.9784, locName = 'إسطنبول، تركيا') {
    document.getElementById('locationInfo').textContent = '📍 ' + locName;
    try {
        const coordinates = new adhan.Coordinates(lat, lng);
        const params = adhan.CalculationMethod.MuslimWorldLeague();
        const date = new Date();
        const prayerTimes = new adhan.PrayerTimes(coordinates, date, params);
        const formatTime = (time) => time ? time.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit', hour12: true }) : '--:--';
        
        document.getElementById('fajrTime').textContent = formatTime(prayerTimes.fajr);
        document.getElementById('sunriseTime').textContent = formatTime(prayerTimes.sunrise);
        document.getElementById('dhuhrTime').textContent = formatTime(prayerTimes.dhuhr);
        document.getElementById('asrTime').textContent = formatTime(prayerTimes.asr);
        document.getElementById('maghribTime').textContent = formatTime(prayerTimes.maghrib);
        document.getElementById('ishaTime').textContent = formatTime(prayerTimes.isha);
    } catch (e) {
        console.error('Error calculating prayer times:', e);
    }
}

function detectLocation() {
    if (navigator.geolocation) {
        document.getElementById('locationInfo').textContent = '📍 جاري التحديد...';
        navigator.geolocation.getCurrentPosition(
            (pos) => { initPrayerTimes(pos.coords.latitude, pos.coords.longitude, 'الموقع الحالي'); },
            () => { alert('تعذر تحديد الموقع الجغرافي. تم استخدام الموقع الافتراضي.'); initPrayerTimes(); }
        );
    } else {
        alert('المتصفح لا يدعم تحديد الموقع الجغرافي.');
    }
}

function changeFontSize(delta) {
    fontSize = Math.max(16, Math.min(40, fontSize + delta * 2));
    localStorage.setItem('fontSize', fontSize);
    applyFontSize(fontSize);
}

function resetFontSize() {
    fontSize = 24;
    localStorage.setItem('fontSize', fontSize);
    applyFontSize(fontSize);
}

function applyFontSize(size) {
    document.getElementById('fontSizeDisplay').textContent = size;
    const elements = document.querySelectorAll('.hadith-text, .ayah-line, .tafsir-panel, .search-result-item .res-text');
    elements.forEach(el => el.style.fontSize = size + 'px');
}

function toggleDark() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}

function selectQuran() {
    currentBook = 'quran';
    updateActiveButton('quranBtn');
    document.getElementById('backToIndexBtn').style.display = 'none';
    loadSurah(currentSurahNum);
}

function loadSurah(surahNum, highlightAyah = null) {
    currentSurahNum = surahNum;
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري تحميل السورة... 📖</div>';
    
    fetch(`/api/surah?surah=${surahNum}`)
        .then(res => res.json())
        .then(data => {
            let html = `
                <div class="surah-container">
                    <div class="quran-tools">
                        <select id="surahSelect" onchange="loadSurah(this.value)">
                            {% for s in surahs %}
                            <option value="{{ s.id }}" ${surahNum == {{ s.id }} ? 'selected' : ''}>{{ s.id }}. {{ s.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="surah-header-bar">
                        <h2>سورة ${data.name}</h2>
                        <div class="surah-info">عدد الآيات: ${data.ayahs.length}</div>
                    </div>
                    ${surahNum !== 9 && surahNum !== 1 ? '<div class="basmala">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</div>' : ''}
                    <div class="ayahs-list">
            `;
            
            data.ayahs.forEach(a => {
                const isTarget = (highlightAyah && a.ayah == highlightAyah);
                html += `
                    <div class="ayah-line ${isTarget ? 'highlight' : ''}" id="ayah-${a.ayah}">
                        ${a.text}
                        <span class="ayah-num-badge">${a.ayah}</span>
                        <span class="ayah-abjad">جُمّل: ${a.abjad}</span>
                        <div class="ayah-actions">
                            <button class="ayah-action-btn" onclick="toggleTafsir(${a.ayah})">📖 التفسير</button>
                            <button class="ayah-action-btn" onclick="addBookmark('quran', 'سورة ${data.name} - آية ${a.ayah}', 'quran_${surahNum}_${a.ayah}')">🔖 حفظ</button>
                            <button class="ayah-action-btn" onclick="copyText(\`${a.text}\`)">📋 نسخ</button>
                        </div>
                        <div class="tafsir-panel" id="tafsir-${a.ayah}">
                            <div class="tafsir-title">تفسير السعدي:</div>
                            ${a.tafsir || 'التفسير غير متوفر لهذه الآية.'}
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                    <div class="nav-buttons">
                        <button class="nav-btn" onclick="loadSurah(${surahNum - 1})" ${surahNum <= 1 ? 'disabled' : ''}>السورة السابقة</button>
                        <button class="nav-btn" onclick="loadSurah(${surahNum + 1})" ${surahNum >= 114 ? 'disabled' : ''}>السورة التالية</button>
                    </div>
                </div>
            `;
            content.innerHTML = html;
            applyFontSize(fontSize);
            
            if (highlightAyah) {
                setTimeout(() => {
                    const targetEl = document.getElementById(`ayah-${highlightAyah}`);
                    if (targetEl) targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
            }
        });
}

function toggleTafsir(ayahNum) {
    const el = document.getElementById(`tafsir-${ayahNum}`);
    if (el) el.classList.toggle('show');
}

function selectBook(bookId) {
    currentBook = bookId;
    currentIndex = 0;
    updateActiveButton(null, bookId);
    document.getElementById('backToIndexBtn').style.display = 'none';
    loadHadith(bookId, currentIndex);
}

function updateActiveButton(btnId, bookId = null) {
    document.querySelectorAll('.book-btn').forEach(btn => btn.classList.remove('active'));
    if (btnId) {
        document.getElementById(btnId).classList.add('active');
    } else if (bookId) {
        const btn = document.querySelector(`.book-btn[data-book="${bookId}"]`);
        if (btn) btn.classList.add('active');
    }
}

function loadHadith(bookId, index) {
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري تحميل الحديث... 📚</div>';
    
    fetch(`/api/hadith?book=${bookId}&index=${index}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                content.innerHTML = `<div class="loading">${data.error}</div>`;
                return;
            }
            currentIndex = data.index;
            totalHadiths = data.total;
            const bookName = document.querySelector(`.book-btn[data-book="${bookId}"]`).textContent;
            
            let html = `
                <div class="hadith-card">
                    <div class="hadith-header">
                        <span class="hadith-book-name">${bookName}</span>
                        <span class="hadith-number">حديث رقم: ${data.id} (${currentIndex + 1} من ${totalHadiths})</span>
                    </div>
                    <div class="abjad-badge">حساب الجُمّل للحديث: ${data.abjad}</div>
                    ${data.narrator ? `<div class="narrator">👤 الراوي: ${data.narrator}</div>` : ''}
                    <div class="hadith-text">${data.text}</div>
                    <div class="copy-buttons" style="display:flex; gap:10px; justify-content:center; margin-top:15px;">
                        <button class="book-btn" onclick="copyText(\`${data.text}\`)">📋 نسخ الحديث</button>
                        <button class="book-btn" onclick="addBookmark('${bookId}', '${bookName} - حديث ${data.id}', 'hadith_${bookId}_${data.id}')">🔖 حفظ الحديث</button>
                    </div>
                </div>
                
                <div class="nav-buttons">
                    <button class="nav-btn" onclick="loadHadith('${bookId}', ${currentIndex - 1})" ${currentIndex <= 0 ? 'disabled' : ''}>الحديث السابق</button>
                    <button class="nav-btn" onclick="loadHadith('${bookId}', ${currentIndex + 1})" ${currentIndex >= totalHadiths - 1 ? 'disabled' : ''}>الحديث التالي</button>
                </div>
            `;
            content.innerHTML = html;
            applyFontSize(fontSize);
        });
}

function doSearch() {
    const query = document.getElementById('searchInput').value.trim();
    const type = document.getElementById('searchType').value;
    if (!query) return;
    
    saveToHistory(query);
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري إعداد فهرس نتائج البحث... 🔍</div>';
    
    fetch(`/api/search?book=${currentBook}&query=${encodeURIComponent(query)}&type=${type}`)
        .then(res => res.json())
        .then(results => {
            if (results.length === 0) {
                content.innerHTML = '<div class="loading">لم يتم العثور على نتائج تطابق البحث.</div>';
                document.getElementById('backToIndexBtn').style.display = 'none';
                return;
            }
            
            let bookTitle = currentBook === 'quran' ? 'القرآن الكريم' : document.querySelector(`.book-btn[data-book="${currentBook}"]`).textContent;
            
            let html = `
                <div class="search-results">
                    <h3 style="color:var(--main-green); margin-bottom:15px; border-bottom:2px solid var(--gold); padding-bottom:8px;">
                        📋 فهرس نتائج البحث عن "${query}" في (${bookTitle}) - [العدد: ${results.length}]
                    </h3>
            `;
            
            results.forEach((res, idx) => {
                if (currentBook === 'quran') {
                    html += `
                        <div class="search-result-item" onclick="openAyahResult(${res.surah}, ${res.ayah})">
                            <div class="res-num">#${idx + 1} - سورة ${res.surah_name} [الآية: ${res.ayah}] <span class="res-abjad-badge">جُمّل: ${res.abjad}</span></div>
                            <div class="res-text">${highlightQuery(res.text, query)}</div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="search-result-item" onclick="openHadithResult('${currentBook}', ${res.index})">
                            <div class="res-num">#${idx + 1} - حديث رقم: ${res.id} <span class="res-abjad-badge">جُمّل: ${res.abjad}</span></div>
                            <div class="res-text">${highlightQuery(res.text, query)}</div>
                        </div>
                    `;
                }
            });
            html += '</div>';
            
            lastSearchResultsHTML = html;
            content.innerHTML = html;
            document.getElementById('backToIndexBtn').style.display = 'none';
            applyFontSize(fontSize);
        });
}

function showAdvancedSearch() { document.getElementById('advSearchModal').classList.add('show'); }
function hideAdvancedSearch() { document.getElementById('advSearchModal').classList.remove('show'); }

function toggleAllBooks(master) {
    document.querySelectorAll('.book-chk').forEach(chk => chk.checked = master.checked);
}

function executeAdvancedSearch() {
    const query = document.getElementById('advQuery').value.trim();
    const includeQuran = document.getElementById('advIncludeQuran').checked ? '1' : '0';
    
    let selectedBooks = [];
    document.querySelectorAll('.book-chk:checked').forEach(chk => selectedBooks.push(chk.value));
    
    if (!query) {
        alert('الرجاء إدخال كلمة للبحث.');
        return;
    }
    
    hideAdvancedSearch();
    saveToHistory(query);
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري إجراء البحث المتقدم الشامل... 🔍</div>';
    
    fetch(`/api/search_advanced?query=${encodeURIComponent(query)}&quran=${includeQuran}&books=${selectedBooks.join(',')}`)
        .then(res => res.json())
        .then(data => {
            let totalCount = data.quran.length;
            Object.values(data.books).forEach(b => totalCount += b.results.length);
            
            if (totalCount === 0) {
                content.innerHTML = '<div class="loading">لم يتم العثور على نتائج مطابقة للبحث المتقدم.</div>';
                document.getElementById('backToIndexBtn').style.display = 'none';
                return;
            }
            
            let html = `
                <div class="search-results">
                    <h3 style="color:var(--main-green); margin-bottom:15px; border-bottom:2px solid var(--gold); padding-bottom:8px;">
                        📋 فهرس نتائج البحث المتقدم الشامل عن "${query}" - [إجمالي النتائج: ${totalCount}]
                    </h3>
            `;
            
            if (data.quran && data.quran.length > 0) {
                html += `<h4 style="color:var(--gold); margin:10px 0;">📖 القرآن الكريم (${data.quran.length})</h4>`;
                data.quran.forEach((res) => {
                    html += `
                        <div class="search-result-item" onclick="openAyahResult(${res.surah}, ${res.ayah})">
                            <div class="res-num">سورة ${res.surah_name} [الآية: ${res.ayah}] <span class="res-abjad-badge">جُمّل: ${res.abjad}</span></div>
                            <div class="res-text">${highlightQuery(res.text, query)}</div>
                        </div>
                    `;
                });
            }
            
            for (const [bId, bObj] of Object.entries(data.books)) {
                html += `<h4 style="color:var(--gold); margin:15px 0 10px 0;">📚 ${bObj.name} (${bObj.results.length})</h4>`;
                bObj.results.forEach((res) => {
                    html += `
                        <div class="search-result-item" onclick="openHadithResult('${bId}', ${res.index})">
                            <div class="res-num">حديث رقم: ${res.id} <span class="res-abjad-badge">جُمّل: ${res.abjad}</span></div>
                            <div class="res-text">${highlightQuery(res.text, query)}</div>
                        </div>
                    `;
                });
            }
            
            html += '</div>';
            lastSearchResultsHTML = html;
            content.innerHTML = html;
            document.getElementById('backToIndexBtn').style.display = 'none';
            applyFontSize(fontSize);
        });
}

function openAyahResult(surah, ayah) {
    document.getElementById('backToIndexBtn').style.display = 'block';
    loadSurah(surah, ayah);
}

function openHadithResult(book, index) {
    document.getElementById('backToIndexBtn').style.display = 'block';
    loadHadith(book, index);
}

function restoreSearchResultsIndex() {
    if (lastSearchResultsHTML) {
        document.getElementById('content').innerHTML = lastSearchResultsHTML;
        document.getElementById('backToIndexBtn').style.display = 'none';
        applyFontSize(fontSize);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function highlightQuery(text, query) {
    if (!query) return text;
    const cleanQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const reg = new RegExp(`(${cleanQuery})`, 'gi');
    return text.replace(reg, '<mark>$1</mark>');
}

function addBookmark(type, title, key) {
    let bookmarks = JSON.parse(localStorage.getItem('userBookmarks') || '[]');
    if (!bookmarks.some(b => b.key === key)) {
        bookmarks.push({ type, title, key, time: new Date().toLocaleDateString('ar-SA') });
        localStorage.setItem('userBookmarks', JSON.stringify(bookmarks));
        syncBookmarksServer(bookmarks);
        alert('تم حفظ العلامة المرجعية بنجاح! 🔖');
    } else {
        alert('العلامة محفوظة مسبقاً.');
    }
}

function showBookmarks() {
    let bookmarks = JSON.parse(localStorage.getItem('userBookmarks') || '[]');
    const list = document.getElementById('bookmarksList');
    if (bookmarks.length === 0) {
        list.innerHTML = '<p style="text-align:center; padding:20px;">لا توجد علامات محفوظة حالياً.</p>';
    } else {
        list.innerHTML = bookmarks.map(b => `
            <div class="search-result-item" style="display:flex; justify-content:space-between; align-items:center;">
                <div onclick="jumpToBookmark('${b.key}')" style="cursor:pointer; flex:1;">
                    <strong>${b.title}</strong>
                    <br><small style="color:#888;">${b.time}</small>
                </div>
                <button onclick="removeBookmark('${b.key}')" style="background:#c0392b; color:white; border:none; padding:5px 12px; border-radius:5px; cursor:pointer;">حذف</button>
            </div>
        `).join('');
    }
    document.getElementById('bookmarksModal').classList.add('show');
}

function hideBookmarks() { document.getElementById('bookmarksModal').classList.remove('show'); }

function removeBookmark(key) {
    let bookmarks = JSON.parse(localStorage.getItem('userBookmarks') || '[]');
    bookmarks = bookmarks.filter(b => b.key !== key);
    localStorage.setItem('userBookmarks', JSON.stringify(bookmarks));
    syncBookmarksServer(bookmarks);
    showBookmarks();
}

function jumpToBookmark(key) {
    hideBookmarks();
    if (key.startsWith('quran_')) {
        let parts = key.split('_');
        let surahNum = parseInt(parts[1]);
        let ayahNum = parseInt(parts[2]);
        selectQuran();
        setTimeout(() => loadSurah(surahNum, ayahNum), 300);
    } else if (key.startsWith('hadith_')) {
        let parts = key.split('_');
        let bookId = parts[1];
        let hadithId = parseInt(parts[2]);
        selectBook(bookId);
        fetch(`/api/hadith_by_id?book=${bookId}&id=${hadithId}`)
            .then(res => res.json())
            .then(data => {
                if (!data.error) loadHadith(bookId, data.index);
            });
    }
}

function syncBookmarksServer(bookmarks) {
    fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: userSyncId, bookmarks })
    }).catch(e => console.error('Sync error:', e));
}

function saveToHistory(query) {
    let history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    if (!history.includes(query)) {
        history.unshift(query);
        if (history.length > 20) history.pop();
        localStorage.setItem('searchHistory', JSON.stringify(history));
    }
}

function showHistory() {
    const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    const list = document.getElementById('historyList');
    if (history.length === 0) {
        list.innerHTML = '<p style="text-align:center; padding:20px;">السجل فارغ.</p>';
    } else {
        list.innerHTML = history.map(q => `
            <div class="search-result-item" onclick="document.getElementById('searchInput').value='${q}'; hideHistory(); doSearch();">
                🔍 ${q}
            </div>
        `).join('');
    }
    document.getElementById('historyModal').classList.add('show');
}

function hideHistory() { document.getElementById('historyModal').classList.remove('show'); }
function clearHistory() { localStorage.removeItem('searchHistory'); showHistory(); }

function showAbjad() { document.getElementById('abjadModal').classList.add('show'); }
function hideAbjad() { document.getElementById('abjadModal').classList.remove('show'); }

function calcAbjad() {
    const text = document.getElementById('abjadInput').value.trim();
    if (!text) return;
    fetch(`/api/abjad?text=${encodeURIComponent(text)}`)
        .then(res => res.json())
        .then(data => {
            let html = `<div style="text-align:center; background:#1a4d2e; color:white; padding:15px; border-radius:8px;"><strong>القيمة الإجمالية: ${data.value}</strong></div>`;
            document.getElementById('abjadResult').innerHTML = html;
        });
}

function showAbout() { document.getElementById('aboutModal').classList.add('show'); }
function hideAbout() { document.getElementById('aboutModal').classList.remove('show'); }

function copyText(text) {
    navigator.clipboard.writeText(text).then(() => alert('تم نسخ النص إلى الحافظة! 📋'));
}
</script>

</body>
</html>
"""

# ==================== 7. التشغيل الرئيسي ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
