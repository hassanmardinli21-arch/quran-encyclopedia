from flask import Flask, render_template, request
import json
import os
import math

app = Flask(__name__)

# ========== تحميل بيانات القرآن (إن وجدت) ==========
def load_quran_data():
    json_path = os.path.join(os.path.dirname(__file__), 'quran.json')
    if not os.path.exists(json_path):
        print("⚠️ ملف quran.json غير موجود، سيتم استخدام بيانات فارغة.")
        return []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ خطأ في قراءة ملف quran.json: {e}")
        return []

quran_data = load_quran_data()

# ========== قائمة أسماء السور (114 سورة) ==========
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

# ========== فلتر التمييز ==========
@app.template_filter('highlight')
def highlight_filter(text, keyword):
    if not keyword or not text:
        return text
    return text.replace(keyword, f'<mark>{keyword}</mark>')

# ========== الصفحة الرئيسية ==========
@app.route('/')
def home():
    # جميع المتغيرات التي يحتاجها القالب
    return render_template('index.html',
        quran=[],  # سيتم عرض البيانات عبر tafsir_data
        keyword='',
        prayer_data={
            'city': 'مكة المكرمة',
            'country': 'السعودية',
            'date': '28 أغسطس 2026',
            'hijri': '15 صفر 1448',
            'timings': {
                'Fajr': '04:30',
                'Sunrise': '06:00',
                'Dhuhr': '12:15',
                'Asr': '15:45',
                'Maghrib': '18:30',
                'Isha': '20:00'
            }
        },
        tafsir_data={
            'error': None,
            'surah_name': 'الفاتحة',
            'name': 'تفسير السعدي',
            'ayahs': []  # فارغ حالياً
        },
        surahs_names=SURAH_NAMES,
        source='quran',
        current_surah=1,
        page=1,
        total_pages=1,
        word_abjad=0
    )

# ========== صفحة البحث ==========
@app.route('/search')
def search():
    keyword = request.args.get('keyword', '').strip()
    source = request.args.get('source', 'quran')
    surah = request.args.get('surah', 'all')
    page = request.args.get('page', 1, type=int)

    # محاكاة البحث (يمكنك تطويرها لاحقاً)
    # نمرر جميع المتغيرات مع قيم افتراضية
    return render_template('index.html',
        quran=[],
        keyword=keyword,
        prayer_data={
            'city': 'مكة المكرمة',
            'country': 'السعودية',
            'date': '28 أغسطس 2026',
            'hijri': '15 صفر 1448',
            'timings': {
                'Fajr': '04:30',
                'Sunrise': '06:00',
                'Dhuhr': '12:15',
                'Asr': '15:45',
                'Maghrib': '18:30',
                'Isha': '20:00'
            }
        },
        tafsir_data={
            'error': None,
            'surah_name': 'البقرة' if surah != 'all' else 'الفاتحة',
            'name': 'تفسير السعدي',
            'ayahs': []  # يمكنك ملؤها من بيانات القرآن الحقيقية
        },
        surahs_names=SURAH_NAMES,
        source=source,
        current_surah=int(surah) if surah.isdigit() else 1,
        page=page,
        total_pages=1,
        word_abjad=0
    )

# ========== صفحات إضافية (لتجنب 404) ==========
@app.route('/read')
def read():
    return render_template('index.html', **get_default_context())

@app.route('/about')
def about():
    return render_template('index.html', **get_default_context())

@app.route('/export')
def export():
    # تصدير (يمكن تطويره)
    return "وظيفة التصدير قيد التطوير"

def get_default_context():
    return {
        'quran': [],
        'keyword': '',
        'prayer_data': {
            'city': 'مكة المكرمة',
            'country': 'السعودية',
            'date': '28 أغسطس 2026',
            'hijri': '15 صفر 1448',
            'timings': {
                'Fajr': '04:30',
                'Sunrise': '06:00',
                'Dhuhr': '12:15',
                'Asr': '15:45',
                'Maghrib': '18:30',
                'Isha': '20:00'
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
    app.run(host='0.0.0.0', port=port)