import os
import re
import json
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent

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
surahs_list = []
quran_ayahs_map = {}

if isinstance(quran_data, list):
    for surah in quran_data:
        surah_num = surah.get('id')
        surahs_list.append({'id': surah_num, 'name': surah.get('name', '')})
        for ayah in surah.get('verses', []):
            quran_ayahs_map[(surah_num, ayah.get('id'))] = ayah.get('text', '')

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

# ==================== 2. المسارات ====================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, books=BOOKS, surahs=surahs_list)

@app.route('/api/hadith')
def get_hadith():
    book_id = request.args.get('book', 'bukhari')
    index = request.args.get('index', 0, type=int)
    hadiths = load_hadith_book(book_id)
    if not hadiths or index >= len(hadiths): return jsonify({'error': 'حديث غير موجود'})
    h = hadiths[index]
    return jsonify({'index': index, 'total': len(hadiths), 'id': h.get('idInBook'), 'text': h.get('arabic'), 'narrator': h.get('english', {}).get('narrator', '')})

@app.route('/api/surah')
def get_surah():
    surah_num = request.args.get('surah', 1, type=int)
    ayahs = [{'ayah': a, 'text': t} for (s, a), t in sorted(quran_ayahs_map.items()) if s == surah_num]
    surah_name = next((s['name'] for s in surahs_list if s['id'] == surah_num), '')
    return jsonify({'surah': surah_num, 'name': surah_name, 'ayahs': ayahs})

@app.route('/api/search')
def search():
    book_id = request.args.get('book', 'bukhari')
    query = request.args.get('query', '').strip()
    if not query: return jsonify([])
    
    if book_id == 'quran':
        results = []
        for (s, a), text in quran_ayahs_map.items():
            if query in text:
                surah_name = next((x['name'] for x in surahs_list if x['id'] == s), '')
                results.append({'surah': s, 'surah_name': surah_name, 'ayah': a, 'text': text})
        return jsonify(results)
    else:
        hadiths = load_hadith_book(book_id)
        results = []
        for i, h in enumerate(hadiths):
            text = h.get('arabic', '')
            if query in text:
                results.append({'index': i, 'id': h.get('idInBook', i+1), 'text': text, 'narrator': h.get('english', {}).get('narrator', '')})
        return jsonify(results)

# ==================== 3. HTML ====================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الموسوعة الإسلامية</title>
    <script src="https://unpkg.com/adhan/lib/bundles/adhan.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root { --main-green: #1a4d2e; --light-green: #e8f5e9; --gold: #c9a961; --bg: #f0f0e8; --text-dark: #1a1a1a; }
        body { font-family: 'Amiri', 'Segoe UI', Tahoma, sans-serif; background: var(--bg); min-height: 100vh; color: var(--text-dark); }
        .hadith-text, .ayah-line, .search-result-item .res-text { font-family: 'Amiri', 'Traditional Arabic', serif; text-align: right; line-height: 2.2; word-spacing: 2px; letter-spacing: 0; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; }
        .header { background: var(--main-green); color: white; padding: 15px 20px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.2); position: sticky; top: 0; z-index: 100; }
        .header h1 { font-size: 26px; color: var(--gold); margin-bottom: 12px; }
        .top-actions { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
        .top-btn { background: #2d6a4f; color: white; border: 1px solid rgba(255,255,255,0.2); padding: 8px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; font-family: inherit; transition: all 0.2s; font-weight: bold; }
        .top-btn:hover { background: #40916c; }
        .search-area { display: flex; gap: 6px; max-width: 1000px; margin: 12px auto 0; align-items: center; flex-wrap: wrap; }
        .search-area input { flex: 1; padding: 10px 15px; border-radius: 8px; border: none; font-size: 15px; font-family: inherit; min-width: 180px; }
        .search-area select { padding: 10px 12px; border-radius: 8px; border: none; font-size: 14px; font-family: inherit; background: white; cursor: pointer; min-width: 170px; }
        .search-area button { background: var(--gold); border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold; color: white; font-family: inherit; white-space: nowrap; }
        .search-area button:hover { background: #b8935a; }
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
        .ayah-line { font-size: 28px; line-height: 2.4; text-align: right; color: #1a3d2e; padding: 12px 18px; margin: 8px 0; border-radius: 8px; }
        .ayah-num-badge { display: inline-block; background: var(--gold); color: white; font-size: 14px; font-weight: bold; padding: 2px 10px; border-radius: 15px; margin: 0 8px; vertical-align: middle; font-family: sans-serif; }
        .surah-container { background: #fdfaf3; border: 3px double var(--gold); border-radius: 15px; padding: 25px; }
        .surah-header-bar { text-align: center; padding: 20px; background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%); color: white; border-radius: 10px; margin-bottom: 20px; }
        .surah-header-bar h2 { font-size: 32px; color: var(--gold); margin-bottom: 8px; }
        .search-results { max-height: 700px; overflow-y: auto; margin-top: 15px; }
        .search-result-item { padding: 12px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; }
        .search-result-item:hover { background: var(--light-green); }
        .search-result-item .res-num { color: var(--main-green); font-weight: bold; font-size: 13px; }
        .search-result-item .res-text { font-size: 19px; line-height: 2; margin-top: 5px; }
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
        .nav-buttons { display: flex; justify-content: center; gap: 10px; margin: 20px 0; flex-wrap: wrap; }
        .nav-btn { background: var(--main-green); color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; font-family: inherit; min-width: 120px; }
        .nav-btn:hover:not(:disabled) { background: #40916c; }
        .nav-btn:disabled { background: #ccc; cursor: not-allowed; }
        .copy-btn { background: var(--gold); color: white; border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 15px; font-family: inherit; font-weight: bold; }
        .copy-btn:hover { background: #b8935a; }
        .copy-buttons { display: flex; justify-content: center; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
    </style>
</head>
<body>

<div class="header">
    <h1>🕌 الموسوعة الإسلامية الشاملة 📚</h1>
    <div class="top-actions">
        <button class="top-btn" onclick="showHistory()">📜 سجل البحث</button>
        <button class="top-btn" onclick="clearHistory()">🗑️ مسح السجل</button>
    </div>
    <div class="search-area">
        <input type="text" id="searchInput" placeholder="ابحث هنا..." onkeydown="if(event.key==='Enter') doSearch()">
        <button onclick="doSearch()">🔍 بحث</button>
    </div>
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

<script>
    let currentBook = null;
    let currentIndex = 0;
    let currentSurah = 1;
    let currentSurahData = null;
    let currentSearchQuery = '';
    let searchHistory = JSON.parse(localStorage.getItem('islamic_searchHistory') || '[]');

    function showHistory() {
        document.getElementById('historyModal').classList.add('show');
        const list = document.getElementById('historyList');
        if (searchHistory.length === 0) { list.innerHTML = '<div style="text-align:center; padding:20px; color:#888;">لا يوجد سجل بحث.</div>'; return; }
        let html = '';
        searchHistory.forEach(h => {
            html += `<div style="padding:10px; border-bottom:1px solid #eee; cursor:pointer;" onclick="hideHistory(); document.getElementById('searchInput').value='${h.query}'; doSearch()">
                <div style="color:var(--main-green); font-weight:bold; font-size:14px;">🔍 ${h.query}</div>
                <div style="color:#888; font-size:12px;">${new Date(h.time).toLocaleString('ar-SA')}</div>
            </div>`;
        });
        list.innerHTML = html;
    }
    function hideHistory() { document.getElementById('historyModal').classList.remove('show'); }
    function clearHistory() { searchHistory = []; localStorage.setItem('islamic_searchHistory', '[]'); showHistory(); }

    function addToHistory(query) {
        if (!query) return;
        searchHistory = searchHistory.filter(h => h.query !== query);
        searchHistory.unshift({ query, time: Date.now() });
        if (searchHistory.length > 20) searchHistory = searchHistory.slice(0, 20);
        localStorage.setItem('islamic_searchHistory', JSON.stringify(searchHistory));
    }

    async function doSearch() {
        const query = document.getElementById('searchInput').value.trim();
        if (!query) { alert('اكتب كلمة للبحث'); return; }
        addToHistory(query);
        currentSearchQuery = query;
        
        const content = document.getElementById('content');
        content.innerHTML = '<div class="loading">جاري البحث...</div>';
        
        try {
            const res = await fetch(`/api/search?book=${currentBook || 'quran'}&query=${encodeURIComponent(query)}`);
            const data = await res.json();
            
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = `<div class="hadith-card" style="text-align:center;">لا توجد نتائج لـ "${query}"</div>`;
                return;
            }
            
            let html = `<div class="hadith-card"><div class="hadith-header"><span class="hadith-book-name">🔍 نتائج البحث في ${getBookName(currentBook || 'quran')}</span><span class="hadith-number">${data.length} نتيجة</span></div><div class="search-results">`;
            data.forEach(item => {
                const preview = item.text.length > 250 ? item.text.substring(0, 250) + '...' : item.text;
                if (currentBook === 'quran') {
                    html += `<div class="search-result-item" onclick="selectQuran().then(()=>showSurah(${item.surah}).then(()=>scrollToAyah(${item.ayah})))"><div class="res-num">📖 سورة ${item.surah_name} - آية ${item.ayah}</div><div class="res-text">${safeHighlight(preview, query)}</div></div>`;
                } else {
                    html += `<div class="search-result-item" onclick="showHadith(${item.index})"><div class="res-num">📌 حديث رقم ${item.id}</div>${item.narrator ? `<div style="color:#b8860b;font-size:13px;margin:5px 0;">🎙️ ${item.narrator}</div>` : ''}<div class="res-text">${safeHighlight(preview, query)}</div></div>`;
                }
            });
            html += '</div></div>';
            content.innerHTML = html;
        } catch(e) { content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ في البحث</div>'; }
    }

    async function selectQuran() { currentBook = 'quran'; document.getElementById('quranBtn').classList.add('active'); await showSurah(1); }
    async function selectBook(bookId) { currentBook = bookId; document.querySelectorAll('.book-btn').forEach(b => b.classList.remove('active')); document.querySelector(`[data-book="${bookId}"]`).classList.add('active'); await showHadith(0); }

    async function showSurah(surahNum) {
        const content = document.getElementById('content'); content.innerHTML = '<div class="loading">جاري تحميل السورة...</div>';
        try {
            const res = await fetch(`/api/surah?surah=${surahNum}`); const data = await res.json();
            currentSurah = surahNum; currentSurahData = data;
            let ayahsHtml = '';
            data.ayahs.forEach(a => {
                ayahsHtml += `<div class="ayah-line" id="ayah-${a.ayah}"><span>${safeHighlight(a.text, currentSearchQuery)}</span><span class="ayah-num-badge">${a.ayah}</span></div>`;
            });
            content.innerHTML = `<div class="surah-container"><div class="surah-header-bar"><h2>سورة ${data.name}</h2></div>${ayahsHtml}</div>`;
        } catch(e) { content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ</div>'; }
    }

    async function showHadith(index) {
        const content = document.getElementById('content'); content.innerHTML = '<div class="loading">جاري التحميل...</div>';
        try {
            const res = await fetch(`/api/hadith?book=${currentBook}&index=${index}`); const data = await res.json();
            if (data.error) { content.innerHTML = `<div class="hadith-card" style="text-align:center;color:red;">${data.error}</div>`; return; }
            currentIndex = data.index;
            content.innerHTML = `
                <div class="hadith-card">
                    <div class="hadith-header"><span class="hadith-book-name">📚 ${getBookName(currentBook)}</span><span class="hadith-number">حديث رقم ${data.id} / ${data.total}</span></div>
                    ${data.narrator ? `<div class="narrator">🎙️ ${data.narrator}</div>` : ''}
                    <div class="hadith-text" style="font-size:24px;">${safeHighlight(data.text, currentSearchQuery)}</div>
                </div>
                <div class="nav-buttons"><button class="nav-btn" onclick="showHadith(${data.index - 1})" ${data.index === 0 ? 'disabled' : ''}>◀ السابق</button><button class="nav-btn" onclick="showHadith(${data.index + 1})" ${data.index >= data.total - 1 ? 'disabled' : ''}>التالي ▶</button></div>
            `;
        } catch(e) { content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ</div>'; }
    }

    function scrollToAyah(ayahNum) {
        if (!ayahNum) return;
        setTimeout(() => { const el = document.getElementById('ayah-' + ayahNum); if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.style.background = '#fff3cd'; setTimeout(() => el.style.background = '', 4000); } }, 300);
    }

    function getBookName(bookId) { return {'quran':'القرآن الكريم', 'bukhari':'صحيح البخاري', 'muslim':'صحيح مسلم', 'abudawud':'سنن أبي داود', 'tirmidhi':'جامع الترمذي'}[bookId] || bookId; }

    function escapeHtml(text) { if (text === null || text === undefined) return ''; const div = document.createElement('div'); div.textContent = String(text); return div.innerHTML; }

    function safeHighlight(text, query) {
        if (!query || !text) return escapeHtml(text || '');
        try {
            const safeText = String(text); const parts = safeText.split(query);
            if (parts.length === 1) return escapeHtml(safeText);
            let result = '';
            for (let i = 0; i < parts.length; i++) {
                result += escapeHtml(parts[i]);
                if (i < parts.length - 1) result += '<mark>' + escapeHtml(query) + '</mark>';
            }
            return result;
        } catch(e) { return escapeHtml(text); }
    }
</script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
