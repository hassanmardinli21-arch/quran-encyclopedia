from flask import Flask, render_template, request
import json
import os
import math

app = Flask(__name__)

# ============================
# تحميل البيانات من ملفات JSON
# ============================

def load_json_file(filename):
    path = os.path.join(os.path.dirname(__file__), 'data', filename)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# تحميل القرآن
quran_data = load_json_file('quran.json') or []

# تحميل تفسير السعدي
tafsir_raw = load_json_file('tafsir_saadi.json') or {}
tafsir_ayahs = tafsir_raw.get('ayahs', [])
tafsir_name = tafsir_raw.get('name', 'تفسير السعدي')
tafsir_surah_name = tafsir_raw.get('surah_name', 'الفاتحة')

# ============================
# أسماء السور
# ============================

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

# ============================
# فلتر التمييز
# ============================

@app.template_filter('highlight')
def highlight_filter(text, keyword):
    if not keyword or not text:
        return text
    return text.replace(keyword, f'<mark>{keyword}</mark>')

# ============================
# الصفحة الرئيسية
# ============================

@app.route('/')
def home():
    # عرض أول 10 آيات من القرآن (إذا كان موجوداً) وإلا من التفسير
    sample = quran_data[:10] if quran_data else tafsir_ayahs[:10]
    
    # إضافة اسم السورة
    for item in sample:
        surah_num = item.get('surah', 1)
        if 1 <= surah_num <= len(SURAH_NAMES):
            item['surah_name'] = SURAH_NAMES[surah_num - 1]

    return render_template('index.html',
        quran=[],
        keyword='',
        prayer_data={
            'city': 'مكة المكرمة',
            'country': 'السعودية',
            'date': '31 أغسطس 2026',
            'hijri': '18 صفر 1448',
            'timings': {
                'Fajr': '04:30', 'Sunrise': '06:00', 'Dhuhr': '12:15',
                'Asr': '15:45', 'Maghrib': '18:30', 'Isha': '20:00'
            }
        },
        tafsir_data={
            'error': None,
            'surah_name': 'الفاتحة',
            'name': tafsir_name,
            'ayahs': sample
        },
        surahs_names=SURAH_NAMES,
        source='quran',
        current_surah=1,
        page=1,
        total_pages=max(1, math.ceil(len(sample) / 10)),
        word_abjad=0
    )

# ============================
# صفحة البحث
# ============================

@app.route('/search')
def search():
    keyword = request.args.get('keyword', '').strip()
    source = request.args.get('source', 'quran')
    surah = request.args.get('surah', 'all')
    page = request.args.get('page', 1, type=int)

    # اختيار مصدر البيانات
    if source == 'quran':
        filtered = quran_data
        source_name = 'القرآن الكريم'
    else:
        filtered = tafsir_ayahs
        source_name = tafsir_name

    # تصفية حسب السورة
    if surah and surah != 'all':
        try:
            surah_num = int(surah)
            filtered = [item for item in filtered if item.get('surah') == surah_num]
        except:
            pass

    # تصفية حسب الكلمة المفتاحية
    if keyword:
        filtered = [item for item in filtered if keyword in item.get('text', '')]

    # الترقيم
    per_page = 10
    total_items = len(filtered)
    total_pages = max(1, math.ceil(total_items / per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]

    # إضافة اسم السورة
    for item in paginated:
        surah_num = item.get('surah', 1)
        if 1 <= surah_num <= len(SURAH_NAMES):
            item['surah_name'] = SURAH_NAMES[surah_num - 1]

    tafsir_data = {
        'error': None,
        'surah_name': f'سورة {SURAH_NAMES[surah_num-1] if surah != "all" else "جميع السور"}',
        'name': source_name,
        'ayahs': paginated,
        'total_pages': total_pages,
        'current_page': page
    }

    return render_template('index.html',
        quran=[],
        keyword=keyword,
        prayer_data={
            'city': 'مكة المكرمة',
            'country': 'السعودية',
            'date': '31 أغسطس 2026',
            'hijri': '18 صفر 1448',
            'timings': {
                'Fajr': '04:30', 'Sunrise': '06:00', 'Dhuhr': '12:15',
                'Asr': '15:45', 'Maghrib': '18:30', 'Isha': '20:00'
            }
        },
        tafsir_data=tafsir_data,
        surahs_names=SURAH_NAMES,
        source=source,
        current_surah=int(surah) if surah.isdigit() else 1,
        page=page,
        total_pages=total_pages,
        word_abjad=0
    )

# ============================
# صفحات إضافية
# ============================

@app.route('/read')
def read():
    return render_template('index.html', **get_default_context())

@app.route('/about')
def about():
    return render_template('index.html', **get_default_context())

@app.route('/export')
def export():
    return "وظيفة التصدير قيد التطوير"

def get_default_context():
    return {
        'quran': [],
        'keyword': '',
        'prayer_data': {
            'city': 'مكة المكرمة',
            'country': 'السعودية',
            'date': '31 أغسطس 2026',
            'hijri': '18 صفر 1448',
            'timings': {
                'Fajr': '04:30', 'Sunrise': '06:00', 'Dhuhr': '12:15',
                'Asr': '15:45', 'Maghrib': '18:30', 'Isha': '20:00'
            }
        },
        'tafsir_data': {'error': None, 'surah_name': 'الفاتحة', 'name': 'تفسير السعدي', 'ayahs': []},
        'surahs_names': SURAH_NAMES,
        'source': 'quran',
        'current_surah': 1,
        'page': 1,
        'total_pages': 1,
        'word_abjad': 0
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
