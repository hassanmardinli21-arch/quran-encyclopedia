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
_DIACRITICS = re.compile(r'[\u064B-\u0652\u0670\u0640]')
_WORD_SPLIT = re.compile(r'[^\u0621-\u064A]+')

def strip_diacritics(text): return _DIACRITICS.sub('', text or '')
def normalize_arabic(text):
    if not text: return ''
    return strip_diacritics(text).replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ة','ه').replace('ى','ي').replace('ؤ','و').replace('ئ','ي')
def abjad_value(text): return sum(ABJAD_VALUES.get(ch, 0) for ch in strip_diacritics(text))
def abjad_breakdown(text): return [{'char': ch, 'value': ABJAD_VALUES[ch]} for ch in strip_diacritics(text) if ch in ABJAD_VALUES]
def match_text(text, query, search_type):
    if not text or not query: return False
    if search_type == 'exact': return query in text
    if search_type == 'phrase': return strip_diacritics(query) in strip_diacritics(text)
    if search_type == 'fuzzy': return normalize_arabic(query) in normalize_arabic(text)
    return strip_diacritics(query) in _WORD_SPLIT.split(strip_diacritics(text))

# ==================== 3. الكتب ====================
BOOKS = {'bukhari':'صحيح البخاري','muslim':'صحيح مسلم','abudawud':'سنن أبي داود','tirmidhi':'جامع الترمذي','nasai':'سنن النسائي','ibnmajah':'سنن ابن ماجه','malik':'موطأ مالك','ahmed':'مسند أحمد','darimi':'سنن الدارمي','riyad_assalihin':'رياض الصالحين','aladab_almufrad':'الأدب المفرد','bulugh_almaram':'بلوغ المرام','mishkat_almasabih':'مشكاة المصابيح','shamail_muhammadiyah':'الشمائل المحمدية'}
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
    book_id = request.args.get('book', 'bukhari')
    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'word')
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
    search_type = request.args.get('type', 'word')
    if not query: return jsonify({'books': {}, 'quran': []})
    result = {'books': {}, 'quran': []}
    if include_quran and search_type != 'number':
        quran_results = []
        for (s, a), text in quran_ayahs_map.items():
            if match_text(text, query, search_type):
                surah_name = next((x['name'] for x in surahs_list if x['id'] == s), '')
                quran_results.append({'surah': s, 'surah_name': surah_name, 'ayah': a, 'text': text, 'abjad': abjad_value(text)})
        result['quran'] = quran_results
    selected = []
    if books_param == 'all': selected = list(BOOKS.keys())
    elif books_param: selected = [b.strip() for b in books_param.split(',') if b.strip() in BOOKS]
    for book_id in selected:
        hadiths = load_hadith_book(book_id)
        book_results = []
        if search_type == 'number':
            try: target_id = int(query)
            except ValueError: continue
            for i, h in enumerate(hadiths):
                if h.get('idInBook') == target_id:
                    book_results.append({'index': i, 'id': h.get('idInBook', i + 1), 'text': h.get('arabic', ''), 'narrator': h.get('english', {}).get('narrator', ''), 'abjad': abjad_value(h.get('arabic', ''))})
        else:
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
        
        .hadith-jump-bar { display: flex; justify-content: center; align-items: center; gap: 10px; margin: 15px auto; padding: 12px 20px; background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); max-width: 500px; flex-wrap: wrap; }
        .hadith-jump-bar label { font-weight: bold; color: var(--main-green); font-size: 15px; }
        .hadith-jump-bar input { padding: 8px 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 15px; font-family: inherit; width: 140px; text-align: center; }
        .hadith-jump-bar input:focus { outline: none; border-color: var(--main-green); }
        .hadith-jump-bar button { background: var(--gold); color: white; border: none; padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: bold; font-family: inherit; }
        .hadith-jump-bar button:hover { background: #b8935a; }
        
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
        
        .quran-tools { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; padding: 15px; background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .quran-tools select { padding: 10px 15px; font-size: 16px; border-radius: 8px; border: 2px solid #ddd; font-family: inherit; flex: 1; min-width: 180px; cursor: pointer; }
        .quran-tools select:focus { outline: none; border-color: var(--main-green); }
        
        .nav-buttons { display: flex; justify-content: center; gap: 10px; margin: 20px 0; flex-wrap: wrap; }
        .nav-btn { background: var(--main-green); color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; font-family: inherit; min-width: 120px; transition: all 0.2s; }
        .nav-btn:hover:not(:disabled) { background: #40916c; transform: translateY(-2px); }
        .nav-btn:disabled { background: #ccc; cursor: not-allowed; }
        
        .copy-buttons { display: flex; justify-content: center; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
        .copy-btn { background: var(--gold); color: white; border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 15px; font-family: inherit; font-weight: bold; }
        .copy-btn:hover { background: #b8935a; }
        
        .search-results { max-height: 700px; overflow-y: auto; margin-top: 15px; }
        .search-result-item { padding: 12px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; }
        .search-result-item:hover { background: var(--light-green); }
        .search-result-item .res-num { color: var(--main-green); font-weight: bold; font-size: 13px; }
        .search-result-item .res-text { font-size: 19px; line-height: 2; margin-top: 5px; }
        .res-abjad-badge { background: #e8f5e9; color: #1a4d2e; padding: 2px 9px; border-radius: 10px; font-size: 12px; margin-right: 8px; font-weight: bold; }
        
        mark { background: #ffeb3b; color: #000; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
        .loading { text-align: center; padding: 40px; color: var(--main-green); font-size: 18px; }
        
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; padding: 20px; overflow-y: auto; }
        .modal-overlay.show { display: flex; }
        .modal-content { background: white; border-radius: 15px; padding: 25px; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative; border: 3px solid var(--gold); }
        .modal-close { position: absolute; top: 15px; left: 15px; background: #c0392b; color: white; border: none; width: 35px; height: 35px; border-radius: 50%; cursor: pointer; font-size: 20px; font-weight: bold; }
        .modal-content h2 { text-align: center; color: var(--main-green); font-size: 24px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid var(--gold); }
        .adv-search-input { width: 100%; padding: 12px 15px; font-size: 16px; border-radius: 8px; border: 2px solid #ddd; font-family: inherit; margin-bottom: 15px; }
        .adv-search-input:focus { outline: none; border-color: var(--main-green); }
        .adv-search-btn { width: 100%; padding: 14px; background: var(--gold); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 17px; font-weight: bold; font-family: inherit; }
        .adv-search-btn:hover { background: #b8935a; }
        
        .abjad-total { text-align: center; background: linear-gradient(135deg, #1a4d2e, #2d6a4f); color: white; padding: 20px; border-radius: 12px; margin-bottom: 15px; }
        .abjad-total .lbl { font-size: 15px; opacity: 0.9; }
        .abjad-total .val { font-size: 48px; color: var(--gold); font-weight: bold; }
        .abjad-chars { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
        .abjad-char { background: #f0f8f0; border: 1px solid #c9e6d0; border-radius: 8px; padding: 6px 10px; font-size: 16px; }
        .abjad-char .ch { font-weight: bold; color: #1a4d2e; }
        .abjad-char .nm { color: #888; font-size: 13px; }
        .abjad-legend { margin-top: 20px; padding: 12px; background: #fff9e6; border-radius: 10px; border-right: 4px solid var(--gold); font-size: 14px; line-height: 1.9; }
        
        body.dark-mode { --bg: #1a1a1a; --text-dark: #e0e0e0; }
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
        body.dark-mode .tafsir-panel { background: #1e3a2f; color: #ddd; }
        body.dark-mode .adv-search-input { background: #333; color: white; }
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
        <button class="top-btn" onclick="showBookmarks()">🔖 علاماتي</button>
        <button class="top-btn" onclick="showAbjad()">🔢 حساب الجُمّل</button>
        <button class="top-btn" onclick="showHistory()">📜 سجل البحث</button>
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

<!-- نافذة سجل البحث -->
<div class="modal-overlay" id="historyModal" onclick="if(event.target===this) hideHistory()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideHistory()">✕</button>
        <h2>📜 سجل البحث</h2>
        <div id="historyList" style="max-height: 400px; overflow-y: auto;"></div>
        <button class="adv-search-btn" style="margin-top:10px; background:#c0392b;" onclick="clearHistory()">🗑️ مسح السجل</button>
    </div>
</div>

<!-- نافذة حساب الجُمّل -->
<div class="modal-overlay" id="abjadModal" onclick="if(event.target===this) hideAbjad()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAbjad()">✕</button>
        <h2>🔢 حساب الجُمّل (أبجد هوز)</h2>
        <textarea id="abjadInput" class="adv-search-input" rows="3" placeholder="اكتب كلمة أو جملة عربية..." style="resize:vertical;"></textarea>
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

<!-- نافذة العلامات -->
<div class="modal-overlay" id="bookmarksModal" onclick="if(event.target===this) hideBookmarks()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideBookmarks()">✕</button>
        <h2>🔖 العلامات المحفوظة</h2>
        <div id="bookmarksList" style="max-height: 400px; overflow-y: auto;"></div>
    </div>
</div>

<!-- نافذة حول التطبيق -->
<div class="modal-overlay" id="aboutModal" onclick="if(event.target===this) hideAbout()">
    <div class="modal-content">
        <button class="modal-close" onclick="hideAbout()">✕</button>
        <h2>🕌 حول التطبيق 📚</h2>
        <div style="background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%); color:white; padding:20px; border-radius:12px; text-align:center; margin-bottom:20px;">
            <h3 style="color:var(--gold); margin-bottom:10px;">الموسوعة الإسلامية الشاملة</h3>
            <p>تطبيق شامل للقرآن الكريم مع تفسير السعدي، وكتب الحديث النبوي الشريف، وأوقات الصلاة، وحساب الجُمّل، وإمكانية البحث والمزامنة.</p>
        </div>
        <div style="font-size:15px; line-height:2; color:var(--text-dark);">
            <p><b>✨ المميزات الرئيسية:</b></p>
            <ul style="padding-right:20px; margin-bottom:15px;">
                <li>📖 قراءة واستعراض القرآن الكريم مع التفسير وحساب الجُمّل للآيات.</li>
                <li>📚 استعراض أمهات كتب الحديث (البخاري، مسلم، أبو داود، الترمذي، وغيرها).</li>
                <li>🕌 مواقيت الصلاة الدقيقة حسَب موقعك الجغرافي.</li>
                <li>🔍 محرك بحث شامل مع فلترة وتظليل النتائج.</li>
                <li>🔖 حفظ العلامات المرجعية والمزامنة التلقائية.</li>
                <li>🌙 دعم الوضع الليلي وتكبير/تصغير الخط.</li>
            </ul>
        </div>
    </div>
</div>

<script>
let currentBook = '';
let currentIndex = 0;
let totalHadiths = 0;
let fontSize = parseInt(localStorage.getItem('fontSize')) || 24;
let currentSurahNum = 1;
let userSyncId = localStorage.getItem('userSyncId') || (function() {
    let id = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('userSyncId', id);
    return id;
})();

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
    document.getElementById('gregorianDate').textContent = now.toLocaleDateString('ar-SA', { year: 'numeric', month: 'long', day: 'numeric' });
    try {
        const hijri = new Intl.DateTimeFormat('ar-SA-u-ca-islamic-uma', { day: 'numeric', month: 'long', year: 'numeric' }).format(now);
        document.getElementById('hijriDate').textContent = hijri;
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
    loadSurah(currentSurahNum);
}

function loadSurah(surahNum) {
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
                html += `
                    <div class="ayah-line" id="ayah-${a.ayah}">
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
            
            const selectEl = document.getElementById('surahSelect');
            if (selectEl) selectEl.value = surahNum;
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
                    <div class="copy-buttons">
                        <button class="copy-btn" onclick="copyText(\`${data.text}\`)">📋 نسخ الحديث</button>
                        <button class="copy-btn" onclick="addBookmark('${bookId}', '${bookName} - حديث ${data.id}', 'hadith_${bookId}_${data.id}')">🔖 حفظ الحديث</button>
                    </div>
                </div>
                
                <div class="hadith-jump-bar">
                    <label>الانتقال لرقم الحديث:</label>
                    <input type="number" id="jumpInput" placeholder="رقم الحديث" min="1">
                    <button onclick="jumpToHadith()">انتقال</button>
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

function jumpToHadith() {
    const val = parseInt(document.getElementById('jumpInput').value);
    if (!val) return;
    
    fetch(`/api/hadith_by_id?book=${currentBook}&id=${val}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) alert(data.error);
            else loadHadith(currentBook, data.index);
        });
}

function doSearch() {
    const query = document.getElementById('searchInput').value.trim();
    const type = document.getElementById('searchType').value;
    if (!query) return;
    
    saveToHistory(query);
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري البحث... 🔍</div>';
    
    fetch(`/api/search?book=${currentBook}&query=${encodeURIComponent(query)}&type=${type}`)
        .then(res => res.json())
        .then(results => {
            if (results.length === 0) {
                content.innerHTML = '<div class="loading">لم يتم العثور على نتائج تطابق البحث.</div>';
                return;
            }
            
            let html = `<h3>نتائج البحث (${results.length}):</h3><div class="search-results">`;
            results.forEach(res => {
                if (currentBook === 'quran') {
                    html += `
                        <div class="search-result-item" onclick="loadSurah(${res.surah}); setTimeout(() => { const el = document.getElementById('ayah-${res.ayah}'); if(el) el.scrollIntoView({behavior:'smooth'}); }, 500);">
                            <div class="res-num">سورة ${res.surah_name} - الآية ${res.ayah} <span class="res-abjad-badge">جُمّل: ${res.abjad}</span></div>
                            <div class="res-text">${highlightQuery(res.text, query)}</div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="search-result-item" onclick="loadHadith('${currentBook}', ${res.index})">
                            <div class="res-num">حديث رقم: ${res.id} <span class="res-abjad-badge">جُمّل: ${res.abjad}</span></div>
                            <div class="res-text">${highlightQuery(res.text, query)}</div>
                        </div>
                    `;
                }
            });
            html += '</div>';
            content.innerHTML = html;
            applyFontSize(fontSize);
        });
}

function highlightQuery(text, query) {
    if (!query) return text;
    const reg = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(reg, '<mark>$1</mark>');
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
function clearHistory() {
    localStorage.removeItem('searchHistory');
    showHistory();
}

function showAbjad() { document.getElementById('abjadModal').classList.add('show'); }
function hideAbjad() { document.getElementById('abjadModal').classList.remove('show'); }

function calcAbjad() {
    const text = document.getElementById('abjadInput').value.trim();
    if (!text) return;
    
    fetch(`/api/abjad?text=${encodeURIComponent(text)}`)
        .then(res => res.json())
        .then(data => {
            let html = `
                <div class="abjad-total">
                    <div class="lbl">القيمة الإجمالية بحساب الجُمّل:</div>
                    <div class="val">${data.value}</div>
                </div>
                <div class="abjad-chars">
            `;
            data.breakdown.forEach(item => {
                html += `<div class="abjad-char"><span class="ch">${item.char}</span> = <span class="nm">${item.value}</span></div>`;
            });
            html += '</div>';
            document.getElementById('abjadResult').innerHTML = html;
        });
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
        list.innerHTML = '<p style="text-align:center; padding:20px;">لا توجد علامات محفوظة.</p>';
    } else {
        list.innerHTML = bookmarks.map(b => `
            <div class="search-result-item" style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong>${b.title}</strong>
                    <br><small style="color:#888;">${b.time}</small>
                </div>
                <button onclick="removeBookmark('${b.key}')" style="background:#c0392b; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;">حذف</button>
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

function syncBookmarksServer(bookmarks) {
    fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: userSyncId, bookmarks })
    }).catch(e => console.error('Sync error:', e));
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
