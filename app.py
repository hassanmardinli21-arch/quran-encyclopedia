# -*- coding: utf-8 -*-
"""
المكتبة القرآنية والتفاسير - خادم Flask الكامل
"""
import json
import os
import re
import unicodedata
import zipfile
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
HADITH_DIR = DATA_DIR / 'hadith'


def find_file(filename):
    """البحث عن ملف في جميع المسارات المحتملة"""
    candidates = [
        BASE_DIR / filename,
        DATA_DIR / filename,
        HADITH_DIR / filename,
        BASE_DIR / 'data' / 'hadith' / filename,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


SURAH_NAMES = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام",
    "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد",
    "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه",
    "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء",
    "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة",
    "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر",
    "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية",
    "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات",
    "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد",
    "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون",
    "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة",
    "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة",
    "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير",
    "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق",
    "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل",
    "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة",
    "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر",
    "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون",
    "النصر", "المسد", "الإخلاص", "الفلق", "الناس"
]

ABJAD_VALUES = {
    'ا': 1, 'أ': 1, 'إ': 1, 'آ': 1, 'ٱ': 1,
    'ب': 2, 'ج': 3, 'د': 4, 'ه': 5, 'ة': 5, 'و': 6, 'ؤ': 6,
    'ز': 7, 'ح': 8, 'ط': 9,
    'ي': 10, 'ى': 10, 'ئ': 10, 'ك': 20, 'ل': 30,
    'م': 40, 'ن': 50, 'س': 60, 'ع': 70, 'ف': 80, 'ص': 90,
    'ق': 100, 'ر': 200, 'ش': 300, 'ت': 400, 'ث': 500,
    'خ': 600, 'ذ': 700, 'ض': 800, 'ظ': 900, 'غ': 1000,
}


def calculate_abjad(text):
    if not text:
        return 0
    total = 0
    for ch in str(text):
        total += ABJAD_VALUES.get(ch, 0)
    return total


def normalize_arabic(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ى": "ي", "ؤ": "و", "ئ": "ي",
        "ة": "ه", "ۃ": "ه",
        "ﷲ": "الله", "ﷻ": "الله",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("ـ", "")
    return re.sub(r"\s+", " ", text).strip()


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ غير موجود: {path}")
        return []
    except Exception as e:
        print(f"⚠️ خطأ في {path}: {e}")
        return []


def parse_hadith_item(item, index, book_name):
    if not isinstance(item, dict):
        return None
    arabic = item.get('arabic') or item.get('text') or ''
    if isinstance(arabic, dict):
        arabic = arabic.get('text') or arabic.get('arabic') or ''
    arabic = str(arabic).strip()
    if not arabic:
        return None
    try:
        number = int(item.get('idInBook') or item.get('id') or index)
    except (ValueError, TypeError):
        number = index
    chapter = item.get('chapter') or item.get('bab') or ''
    if isinstance(chapter, dict):
        chapter = chapter.get('arabic') or chapter.get('title') or ''
    return {
        'type': 'hadith',
        'number': number,
        'chapter': str(chapter).strip(),
        'book': book_name,
        'text': arabic,
        '_norm': normalize_arabic(arabic),
        '_abjad': calculate_abjad(arabic),
    }


def load_hadith_file(path, book_name):
    data = load_json(path)
    if not data:
        return []
    items = []
    if isinstance(data, dict):
        items = data.get('hadiths') or data.get('data') or []
    elif isinstance(data, list):
        items = data
    records = []
    for i, item in enumerate(items, 1):
        rec = parse_hadith_item(item, i, book_name)
        if rec:
            records.append(rec)
    return records


print("=" * 60)
print("📚 تحميل قاعدة البيانات...")

QURAN_PATH = find_file('quran.json')
QURAN_DATA = load_json(QURAN_PATH) if QURAN_PATH else []
print(f"✅ القرآن: {len(QURAN_DATA)} آية (من {QURAN_PATH})")

TAFSIR_PATH = find_file('tafsir_saadi.json')
TAFSIR_LIST = load_json(TAFSIR_PATH) if TAFSIR_PATH else []
TAFSIR_MAP = {}
for item in TAFSIR_LIST:
    if not isinstance(item, dict):
        continue
    key = (item.get('surah'), item.get('ayah'))
    TAFSIR_MAP[key] = item.get('text', '')
print(f"✅ التفسير: {len(TAFSIR_MAP)} مدخل")

HADITH_BOOKS = {}

BUKHARI_PATH = find_file('bukhari.json')
if BUKHARI_PATH:
    HADITH_BOOKS['bukhari'] = load_hadith_file(BUKHARI_PATH, 'صحيح البخاري')
    print(f"✅ البخاري: {len(HADITH_BOOKS['bukhari'])} حديث (من {BUKHARI_PATH})")

MUSLIM_PATH = find_file('muslim.json')
if MUSLIM_PATH:
    HADITH_BOOKS['muslim'] = load_hadith_file(MUSLIM_PATH, 'صحيح مسلم')
    print(f"✅ مسلم: {len(HADITH_BOOKS['muslim'])} حديث (من {MUSLIM_PATH})")

print(f"✅ إجمالي الكتب: {len(HADITH_BOOKS)}")
print("=" * 60)


DEFAULT_PRAYER = {
    'city': 'مكة المكرمة',
    'country': 'السعودية',
    'date': '',
    'hijri': '',
    'timings': {
        'Fajr': '04:30', 'Sunrise': '06:00', 'Dhuhr': '12:15',
        'Asr': '15:45', 'Maghrib': '18:30', 'Isha': '20:00'
    }
}


@app.template_filter('highlight')
def highlight_filter(text, keyword):
    if not keyword or not text:
        return text
    try:
        words = [w for w in re.split(r'\s+', keyword) if len(w) >= 2]
        if not words:
            words = [keyword]
        result = str(text)
        for w in words:
            esc = re.escape(w)
            result = re.sub(esc, f'<mark>{w}</mark>', result)
        return result
    except Exception:
        return text


def search_quran(keyword, surah_filter):
    results = []
    norm_kw = normalize_arabic(keyword)
    keywords = [w for w in norm_kw.split() if len(w) >= 2]
    for item in QURAN_DATA:
        if not isinstance(item, dict):
            continue
        s = item.get('surah')
        a = item.get('ayah')
        if surah_filter and s != surah_filter:
            continue
        text = item.get('text', '')
        norm_text = normalize_arabic(text)
        if not keywords:
            match = True
        else:
            match = all(kw in norm_text for kw in keywords)
        if match:
            surah_name = SURAH_NAMES[s - 1] if 1 <= s <= 114 else ''
            results.append({
                'type': 'ayah',
                'number': a,
                'surah_name': surah_name,
                'text': text,
                'abjad': calculate_abjad(text),
                'word_abjad': calculate_abjad(keyword),
            })
    return results


def search_tafsir(keyword, surah_filter):
    results = []
    norm_kw = normalize_arabic(keyword)
    keywords = [w for w in norm_kw.split() if len(w) >= 2]
    for (s, a), text in TAFSIR_MAP.items():
        if surah_filter and s != surah_filter:
            continue
        norm_text = normalize_arabic(text)
        if not keywords:
            match = True
        else:
            match = all(kw in norm_text for kw in keywords)
        if match:
            surah_name = SURAH_NAMES[s - 1] if 1 <= s <= 114 else ''
            results.append({
                'type': 'tafsir',
                'number': a,
                'surah_name': surah_name,
                'text': text,
                'abjad': calculate_abjad(text),
                'word_abjad': calculate_abjad(keyword),
            })
    return results


def search_hadith(book_key, keyword):
    results = []
    records = HADITH_BOOKS.get(book_key, [])
    if not records or not keyword:
        return results
    norm_kw = normalize_arabic(keyword)
    keywords = [w for w in norm_kw.split() if len(w) >= 2]
    if not keywords:
        keywords = [norm_kw]
    for rec in records:
        if all(kw in rec['_norm'] for kw in keywords):
            results.append({
                'type': 'hadith',
                'number': rec['number'],
                'chapter': rec.get('chapter', ''),
                'book': rec['book'],
                'text': rec['text'],
                'abjad': rec['_abjad'],
                'word_abjad': calculate_abjad(keyword),
            })
    return results


@app.route('/')
def home():
    context = {
        'quran': [],
        'keyword': '',
        'prayer_data': DEFAULT_PRAYER,
        'tafsir_data': {
            'error': None,
            'surah_name': 'جميع السور',
            'name': 'القرآن الكريم',
            'ayahs': [],
        },
        'surahs_names': SURAH_NAMES,
        'source': 'quran',
        'current_surah': 0,
        'page': 1,
        'total_pages': 1,
        'word_abjad': 0,
    }
    return render_template('index.html', **context)


@app.route('/search')
def search():
    keyword = request.args.get('keyword', '').strip()
    source = request.args.get('source', 'quran')
    surah = request.args.get('surah', 'all')
    page = request.args.get('page', 1, type=int)

    surah_filter = int(surah) if surah.isdigit() else None

    if source == 'quran':
        results = search_quran(keyword, surah_filter)
        surah_name = SURAH_NAMES[surah_filter - 1] if surah_filter else 'جميع السور'
        tafsir_name = 'القرآن الكريم'
    elif source == 'saadi':
        results = search_tafsir(keyword, surah_filter)
        surah_name = SURAH_NAMES[surah_filter - 1] if surah_filter else 'جميع السور'
        tafsir_name = 'تفسير السعدي'
    elif source in HADITH_BOOKS:
        results = search_hadith(source, keyword)
        book_label = {
            'bukhari': 'صحيح البخاري',
            'muslim': 'صحيح مسلم',
        }.get(source, source)
        surah_name = book_label
        tafsir_name = f'📚 {book_label}'
    else:
        results = []
        surah_name = 'غير معروف'
        tafsir_name = ''

    per_page = 25
    total = len(results)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_results = results[start:end]

    context = {
        'quran': [],
        'keyword': keyword,
        'prayer_data': DEFAULT_PRAYER,
        'tafsir_data': {
            'error': None,
            'surah_name': surah_name,
            'name': tafsir_name,
            'ayahs': page_results,
        },
        'surahs_names': SURAH_NAMES,
        'source': source,
        'current_surah': surah_filter or 0,
        'page': page,
        'total_pages': total_pages,
        'word_abjad': calculate_abjad(keyword) if keyword else 0,
    }
    return render_template('index.html', **context)


@app.route('/read')
def read():
    return home()


@app.route('/about')
def about():
    return home()


@app.route('/export')
def export():
    return "وظيفة التصدير قيد التطوير"


@app.route('/health')
def health():
    return {
        'status': 'ok',
        'quran': len(QURAN_DATA),
        'tafsir': len(TAFSIR_MAP),
        'books': {k: len(v) for k, v in HADITH_BOOKS.items()},
    }


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
