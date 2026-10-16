// ============================================================
// الموسوعة الإسلامية الشاملة - JavaScript Edition
// ============================================================

const BOOKS = {
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
    'shamail_muhammadiyah': 'الشمائل المحمدية',
    'nawawi40': 'الأربعون النووية',
    'qudsi40': 'الأحاديث القدسية',
    'shahwaliullah40': 'أربعون شاه ولي الله'
};

const DATA_PATH = 'data';
const HADITH_PATH = DATA_PATH + '/extracted_books';

let quranData = null;
let currentBook = null;
let currentBookData = null;
let currentIndex = 0;
let currentSurah = 1;
let fontSize = 24;
let bookmarks = JSON.parse(localStorage.getItem('bookmarks') || '{}');
let currentSearchQuery = '';

async function loadQuranData() {
    try {
        console.log('📖 جاري تحميل القرآن...');
        const res = await fetch(DATA_PATH + '/quran.json');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        quranData = await res.json();
        console.log('✅ تم تحميل القرآن:', quranData.length, 'سورة');
        return true;
    } catch (e) {
        console.error('❌ خطأ في تحميل القرآن:', e);
        return false;
    }
}

async function loadBook(bookId) {
    if (currentBookData && currentBook === bookId) return currentBookData;
    try {
        console.log('📚 جاري تحميل ' + BOOKS[bookId] + '...');
        const res = await fetch(HADITH_PATH + '/' + bookId + '.json');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        let hadiths = [];
        if (Array.isArray(data)) hadiths = data;
        else if (data.hadiths) hadiths = data.hadiths;
        currentBookData = hadiths;
        console.log('✅ تم تحميل ' + hadiths.length + ' حديث');
        return hadiths;
    } catch (e) {
        console.error('❌ خطأ في تحميل ' + bookId + ':', e);
        return [];
    }
}

async function selectBook(bookId) {
    currentBook = bookId;
    currentIndex = 0;
    currentSearchQuery = '';
    currentBookData = null;
    setActiveBook(bookId);
    await showHadith(0);
}

function setActiveBook(bookId) {
    document.querySelectorAll('.book-btn').forEach(b => b.classList.remove('active'));
    const sel = bookId === 'quran' ? document.getElementById('quranBtn') : document.querySelector('[data-book="' + bookId + '"]');
    if (sel) sel.classList.add('active');
}

async function showHadith(index) {
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري التحميل...</div>';
    
    const hadiths = await loadBook(currentBook);
    if (!hadiths || hadiths.length === 0) {
        content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">لا توجد أحاديث في ' + BOOKS[currentBook] + '</div>';
        return;
    }
    if (index < 0) index = 0;
    if (index >= hadiths.length) index = hadiths.length - 1;
    
    currentIndex = index;
    const h = hadiths[index];
    const isBookmarked = bookmarks[currentBook + '_' + index];
    const arabicText = h.arabic || h.text || '';
    const narrator = (h.english && h.english.narrator) || '';
    const hadithNum = h.idInBook || h.id || (index + 1);
    
    content.innerHTML = 
        '<div class="hadith-card">' +
            '<div class="hadith-header">' +
                '<span class="hadith-book-name">📚 ' + BOOKS[currentBook] + '</span>' +
                '<span class="hadith-number">حديث رقم ' + hadithNum + ' / ' + hadiths.length + '</span>' +
            '</div>' +
            (narrator ? '<div class="narrator">🎙️ ' + escapeHtml(narrator) + '</div>' : '') +
            '<div class="hadith-text" id="hadithText" style="font-size:' + fontSize + 'px;">' + safeHighlight(arabicText, currentSearchQuery) + '</div>' +
            '<div class="copy-buttons">' +
                '<button class="copy-btn" onclick="copyHadith()">📋 نسخ الحديث</button>' +
                '<button class="copy-btn" onclick="toggleBookmark()">' + (isBookmarked ? '🔖 إزالة العلامة' : '🔖 علامة') + '</button>' +
            '</div>' +
        '</div>' +
        '<div class="hadith-jump-bar">' +
            '<label>🔢 اذهب إلى حديث رقم:</label>' +
            '<input type="number" id="hadithJumpInput" min="1" max="' + hadiths.length + '" placeholder="1 - ' + hadiths.length + '" onkeydown="if(event.key===\'Enter\') jumpToHadith()">' +
            '<button onclick="jumpToHadith()">اذهب</button>' +
        '</div>' +
        '<div class="nav-buttons">' +
            '<button class="nav-btn" onclick="showHadith(' + (index - 1) + ')" ' + (index === 0 ? 'disabled' : '') + '>◀ السابق</button>' +
            '<button class="nav-btn" onclick="showHadith(0)">🏠 الأول</button>' +
            '<button class="nav-btn" onclick="showHadith(' + (index + 1) + ')" ' + (index >= hadiths.length - 1 ? 'disabled' : '') + '>التالي ▶</button>' +
        '</div>';
}

function jumpToHadith() {
    const input = document.getElementById('hadithJumpInput');
    if (!input) return;
    const id = parseInt(input.value);
    if (!id || id < 1) { alert('أدخل رقم حديث صحيح'); return; }
    const idx = currentBookData.findIndex(h => (h.idInBook || h.id) === id);
    if (idx !== -1) showHadith(idx);
    else if (id <= currentBookData.length) showHadith(id - 1);
    else alert('الحديث رقم ' + id + ' غير موجود');
}

async function selectQuran() {
    currentBook = 'quran';
    setActiveBook('quran');
    await showSurah(1);
}

async function showSurah(surahNum) {
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري تحميل السورة...</div>';
    
    if (!quranData) {
        content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">لم يتم تحميل القرآن</div>';
        return;
    }
    
    const surah = quranData.find(s => s.id === surahNum);
    if (!surah) {
        content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">السورة غير موجودة</div>';
        return;
    }
    
    currentSurah = surahNum;
    const verses = surah.verses || [];
    
    let surahSelectHtml = '<select id="surahSelect" onchange="showSurah(parseInt(this.value))">';
    quranData.forEach(s => {
        surahSelectHtml += '<option value="' + s.id + '"' + (s.id === surahNum ? ' selected' : '') + '>' + s.id + '. سورة ' + s.name + '</option>';
    });
    surahSelectHtml += '</select>';
    
    let ayahSelectHtml = '<select id="ayahSelect" onchange="scrollToAyah(parseInt(this.value))">';
    ayahSelectHtml += '<option value="">📌 انتقل إلى آية...</option>';
    verses.forEach(a => {
        ayahSelectHtml += '<option value="' + a.id + '">آية ' + a.id + '</option>';
    });
    ayahSelectHtml += '</select>';
    
    let ayahsHtml = '';
    if (surahNum !== 1 && surahNum !== 9) {
        ayahsHtml += '<div class="basmala">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</div>';
    }
    
    verses.forEach(a => {
        ayahsHtml += 
            '<div class="ayah-line" id="ayah-' + a.id + '" data-ayah="' + a.id + '">' +
                '<span>' + safeHighlight(a.text, currentSearchQuery) + '</span>' +
                '<span class="ayah-num-badge">' + a.id + '</span>' +
                '<div class="ayah-actions">' +
                    '<button class="ayah-action-btn" onclick="copyAyah(' + a.id + ')">📋 نسخ</button>' +
                '</div>' +
            '</div>';
    });
    
    content.innerHTML = 
        '<div class="quran-tools">' +
            surahSelectHtml +
            ayahSelectHtml +
            '<button onclick="copySurah()">📋 نسخ السورة</button>' +
        '</div>' +
        '<div class="surah-container">' +
            '<div class="surah-header-bar">' +
                '<h2>سورة ' + surah.name + '</h2>' +
                '<div class="surah-info">' + verses.length + ' آية</div>' +
            '</div>' +
            ayahsHtml +
        '</div>' +
        '<div class="nav-buttons">' +
            '<button class="nav-btn" onclick="showSurah(' + (surahNum - 1) + ')" ' + (surahNum <= 1 ? 'disabled' : '') + '>◀ السورة السابقة</button>' +
            '<button class="nav-btn" onclick="scrollToTop()">⬆ أعلى</button>' +
            '<button class="nav-btn" onclick="showSurah(' + (surahNum + 1) + ')" ' + (surahNum >= 114 ? 'disabled' : '') + '>السورة التالية ▶</button>' +
        '</div>';
}

function scrollToAyah(ayahNum) {
    if (!ayahNum) return;
    setTimeout(function() {
        const el = document.getElementById('ayah-' + ayahNum);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('highlight');
            setTimeout(function() { el.classList.remove('highlight'); }, 4000);
        }
    }, 300);
}

function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }

function copyAyah(n) {
    const el = document.getElementById('ayah-' + n);
    if (!el) return;
    const text = el.querySelector('span').innerText;
    navigator.clipboard.writeText(text).then(function() { alert('✅ تم نسخ الآية'); });
}

function copySurah() {
    const c = document.querySelector('.surah-container');
    if (!c) return;
    let text = c.querySelector('h2').innerText + '\n\n';
    c.querySelectorAll('.ayah-line').forEach(function(l) {
        text += l.querySelector('span').innerText + ' (' + l.dataset.ayah + ')\n';
    });
    navigator.clipboard.writeText(text).then(function() { alert('✅ تم نسخ السورة'); });
}

async function doSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) { alert('اكتب كلمة للبحث'); return; }
    currentSearchQuery = query;
    
    if (!currentBook || currentBook === 'quran') {
        currentBook = 'bukhari';
        setActiveBook('bukhari');
    }
    
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري البحث...</div>';
    
    const hadiths = await loadBook(currentBook);
    const results = [];
    
    for (let i = 0; i < hadiths.length; i++) {
        const text = hadiths[i].arabic || '';
        if (text.includes(query)) {
            results.push({
                index: i,
                id: hadiths[i].idInBook || i + 1,
                text: text,
                narrator: (hadiths[i].english && hadiths[i].english.narrator) || ''
            });
            if (results.length >= 500) break;
        }
    }
    
    if (results.length === 0) {
        content.innerHTML = '<div class="hadith-card" style="text-align:center;">لا توجد نتائج لـ "' + escapeHtml(query) + '" في ' + BOOKS[currentBook] + '</div>';
        return;
    }
    
    let html = '<div class="hadith-card">' +
        '<div class="hadith-header">' +
            '<span class="hadith-book-name">🔍 نتائج البحث في ' + BOOKS[currentBook] + '</span>' +
            '<span class="hadith-number">' + results.length + ' نتيجة</span>' +
        '</div>' +
        '<div class="search-results">';
    
    results.forEach(function(item) {
        const preview = item.text.length > 250 ? item.text.substring(0, 250) + '...' : item.text;
        html += '<div class="search-result-item" onclick="showHadith(' + item.index + ')">' +
            '<div class="res-num">📌 حديث رقم ' + item.id + '</div>' +
            (item.narrator ? '<div style="color:#b8860b;font-size:13px;margin:5px 0;">🎙️ ' + escapeHtml(item.narrator) + '</div>' : '') +
            '<div class="res-text">' + safeHighlight(preview, query) + '</div>' +
        '</div>';
    });
    
    html += '</div></div>';
    content.innerHTML = html;
}

function showAdvancedSearch() { document.getElementById('advSearchModal').classList.add('show'); }
function hideAdvancedSearch() { document.getElementById('advSearchModal').classList.remove('show'); }

function selectAllBooks() {
    document.querySelectorAll('.book-chk').forEach(function(chk) { chk.checked = true; });
    document.getElementById('chk_quran').checked = true;
}
function deselectAllBooks() {
    document.querySelectorAll('.book-chk').forEach(function(chk) { chk.checked = false; });
    document.getElementById('chk_quran').checked = false;
}
function selectOnlyQuran() {
    deselectAllBooks();
    document.getElementById('chk_quran').checked = true;
}

async function doAdvancedSearch() {
    const query = document.getElementById('advSearchInput').value.trim();
    if (!query) { alert('اكتب كلمة للبحث'); return; }
    
    const selectedBooks = [];
    document.querySelectorAll('.book-chk:checked').forEach(function(chk) { selectedBooks.push(chk.value); });
    const includeQuran = document.getElementById('chk_quran').checked;
    
    if (selectedBooks.length === 0 && !includeQuran) {
        alert('اختر كتاباً واحداً على الأقل');
        return;
    }
    
    hideAdvancedSearch();
    currentSearchQuery = query;
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">جاري البحث في عدة كتب...</div>';
    
    const result = { quran: [], books: {} };
    
    if (includeQuran && quranData) {
        quranData.forEach(function(surah) {
            (surah.verses || []).forEach(function(a) {
                if (a.text && a.text.includes(query)) {
                    result.quran.push({
                        surah: surah.id,
                        surah_name: surah.name,
                        ayah: a.id,
                        text: a.text
                    });
                }
            });
        });
    }
    
    for (let b = 0; b < selectedBooks.length; b++) {
        const bookId = selectedBooks[b];
        const hadiths = await loadBook(bookId);
        const bookResults = [];
        for (let i = 0; i < hadiths.length; i++) {
            const text = hadiths[i].arabic || '';
            if (text.includes(query)) {
                bookResults.push({
                    index: i,
                    id: hadiths[i].idInBook || i + 1,
                    text: text,
                    narrator: (hadiths[i].english && hadiths[i].english.narrator) || ''
                });
                if (bookResults.length >= 200) break;
            }
        }
        if (bookResults.length > 0) {
            result.books[bookId] = { name: BOOKS[bookId], results: bookResults };
        }
    }
    
    let totalResults = result.quran.length;
    Object.values(result.books).forEach(function(b) { totalResults += b.results.length; });
    
    if (totalResults === 0) {
        content.innerHTML = '<div class="hadith-card" style="text-align:center;">لا توجد نتائج لـ "' + escapeHtml(query) + '"</div>';
        return;
    }
    
    let html = '<div class="hadith-card">' +
        '<div class="hadith-header">' +
            '<span class="hadith-book-name">🔎 نتائج البحث المتقدم</span>' +
            '<span class="hadith-number">' + totalResults + ' نتيجة</span>' +
        '</div>';
    
    if (result.quran.length > 0) {
        html += '<div class="adv-results-section">' +
            '<div class="adv-book-title"><span>📖 القرآن الكريم</span><span class="count">' + result.quran.length + '</span></div>';
        result.quran.forEach(function(item) {
            html += '<div class="search-result-item" onclick="hideAdvancedSearch(); selectQuran().then(function(){scrollToAyah(' + item.ayah + ')})">' +
                '<div class="res-num">سورة ' + escapeHtml(item.surah_name) + ' - آية ' + item.ayah + '</div>' +
                '<div class="res-text">' + safeHighlight(item.text, query) + '</div>' +
            '</div>';
        });
        html += '</div>';
    }
    
    for (const bookId in result.books) {
        const bookData = result.books[bookId];
        html += '<div class="adv-results-section">' +
            '<div class="adv-book-title"><span>📚 ' + escapeHtml(bookData.name) + '</span><span class="count">' + bookData.results.length + '</span></div>';
        bookData.results.forEach(function(item) {
            const preview = item.text.length > 250 ? item.text.substring(0, 250) + '...' : item.text;
            html += '<div class="search-result-item" onclick="hideAdvancedSearch(); selectBook(\'' + bookId + '\').then(function(){showHadith(' + item.index + ')})">' +
                '<div class="res-num">📌 حديث رقم ' + item.id + '</div>' +
                (item.narrator ? '<div style="color:#b8860b;font-size:13px;margin:5px 0;">🎙️ ' + escapeHtml(item.narrator) + '</div>' : '') +
                '<div class="res-text">' + safeHighlight(preview, query) + '</div>' +
            '</div>';
        });
        html += '</div>';
    }
    
    html += '</div>';
    content.innerHTML = html;
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
        const parts = String(text).split(String(query));
        if (parts.length === 1) return escapeHtml(text);
        let result = '';
        for (let i = 0; i < parts.length; i++) {
            result += escapeHtml(parts[i]);
            if (i < parts.length - 1) result += '<mark>' + escapeHtml(query) + '</mark>';
        }
        return result;
    } catch(e) {
        return escapeHtml(text);
    }
}

function copyHadith() {
    const el = document.getElementById('hadithText');
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(function() { alert('✅ تم النسخ'); });
}

function toggleBookmark() {
    if (!currentBook) return;
    const key = currentBook + '_' + currentIndex;
    if (bookmarks[key]) delete bookmarks[key];
    else bookmarks[key] = { book: currentBook, index: currentIndex, time: Date.now() };
    localStorage.setItem('bookmarks', JSON.stringify(bookmarks));
    alert(bookmarks[key] ? '✅ تمت إضافة علامة' : '🗑️ تم حذف العلامة');
    if (currentBook !== 'quran') showHadith(currentIndex);
}

function changeFontSize(delta) {
    fontSize = Math.max(16, Math.min(48, fontSize + delta));
    document.getElementById('fontSizeDisplay').innerText = fontSize;
    document.querySelectorAll('.hadith-text, .ayah-line').forEach(function(el) {
        el.style.fontSize = fontSize + 'px';
    });
}

function resetFontSize() {
    fontSize = 24;
    document.getElementById('fontSizeDisplay').innerText = fontSize;
    document.querySelectorAll('.hadith-text, .ayah-line').forEach(function(el) {
        el.style.fontSize = fontSize + 'px';
    });
}

function toggleDark() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

function detectLocation() {
    const locEl = document.getElementById('locationInfo');
    if (!navigator.geolocation) {
        locEl.innerText = '⚠️ المتصفح لا يدعم تحديد الموقع';
        fetchPrayerTimes(21.4225, 39.8262);
        return;
    }
    locEl.innerText = '📍 جاري تحديد الموقع...';
    navigator.geolocation.getCurrentPosition(
        function(pos) {
            fetchPrayerTimes(pos.coords.latitude, pos.coords.longitude);
            reverseGeocode(pos.coords.latitude, pos.coords.longitude);
        },
        function() {
            locEl.innerText = '⚠️ تعذر الموقع — استخدام مكة';
            fetchPrayerTimes(21.4225, 39.8262);
        },
        { enableHighAccuracy: true, timeout: 15000 }
    );
}

async function fetchPrayerTimes(lat, lng) {
    try {
        const today = new Date();
        const dateStr = today.getDate() + '-' + (today.getMonth() + 1) + '-' + today.getFullYear();
        const url = 'https://api.aladhan.com/v1/timings/' + dateStr + '?latitude=' + lat + '&longitude=' + lng + '&method=4';
        const res = await fetch(url);
        const data = await res.json();
        if (data.code === 200 && data.data) {
            const t = data.data.timings;
            const clean = function(s) { return s ? s.split(' ')[0] : '--:--'; };
            document.getElementById('fajrTime').innerText = clean(t.Fajr);
            document.getElementById('sunriseTime').innerText = clean(t.Sunrise);
            document.getElementById('dhuhrTime').innerText = clean(t.Dhuhr);
            document.getElementById('asrTime').innerText = clean(t.Asr);
            document.getElementById('maghribTime').innerText = clean(t.Maghrib);
            document.getElementById('ishaTime').innerText = clean(t.Isha);
        }
    } catch(e) {
        console.error('فشل تحميل مواقيت الصلاة:', e);
    }
}

async function reverseGeocode(lat, lng) {
    try {
        const res = await fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat=' + lat + '&lon=' + lng + '&accept-language=ar');
        const data = await res.json();
        const addr = data.address || {};
        const city = addr.city || addr.town || addr.village || addr.state || '';
        const country = addr.country || '';
        document.getElementById('locationInfo').innerText = '📍 ' + city + (city && country ? '، ' : '') + country;
    } catch(e) {
        document.getElementById('locationInfo').innerText = '📍 ' + lat.toFixed(2) + '°N, ' + lng.toFixed(2) + '°E';
    }
}

const SYRIAN_MONTHS = ['كانون الثاني','شباط','آذار','نيسان','أيار','حزيران','تموز','آب','أيلول','تشرين الأول','تشرين الثاني','كانون الأول'];
const ARABIC_DAYS = ['الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت'];
const HIJRI_MONTHS = ['محرّم','صفر','ربيع الأول','ربيع الآخر','جمادى الأولى','جمادى الآخرة','رجب','شعبان','رمضان','شوّال','ذو القعدة','ذو الحجة'];

function toHijri(date) {
    let d = date.getDate(), m = date.getMonth() + 1, y = date.getFullYear();
    if (m < 3) { y -= 1; m += 12; }
    let a = Math.floor(y / 100), b = 2 - a + Math.floor(a / 4);
    if (y < 1583) b = 0;
    let jd = Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + b - 1524;
    b = 0;
    if (jd > 2299160) { a = Math.floor((jd - 1867216.25) / 36524.25); b = 1 + a - Math.floor(a / 4); }
    let bb = jd + b + 1524, cc = Math.floor((bb - 122.1) / 365.25), dd = Math.floor(365.25 * cc);
    let ee = Math.floor((bb - dd) / 30.6001);
    d = bb - dd - Math.floor(30.6001 * ee);
    m = ee < 14 ? ee - 1 : ee - 13;
    y = m > 2 ? cc - 4716 : cc - 4715;
    let jdH = Math.floor((11 * y + 3) / 30) + 354 * y + Math.floor(30 * (m - 1)) - Math.floor((m - 1) / 2) + d + 1948440 - 385;
    let l = jdH - 1948440 + 10632, n = Math.floor((l - 1) / 10631);
    l = l - 10631 * n + 354;
    let j = Math.floor((10985 - l) / 5316) * Math.floor((50 * l) / 17719) + Math.floor(l / 5670) * Math.floor((43 * l) / 15238);
    l = l - Math.floor((30 - j) / 15) * Math.floor((17719 * j) / 50) - Math.floor(j / 16) * Math.floor((15238 * j) / 43) + 29;
    return { day: l - Math.floor((709 * Math.floor((24 * l) / 709)) / 24), month: Math.floor((24 * l) / 709), year: 30 * n + j - 30 };
}

function updateTime() {
    const now = new Date();
    document.getElementById('currentTime').innerText = now.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
    document.getElementById('dayName').innerText = '📆 ' + ARABIC_DAYS[now.getDay()];
    try {
        const h = toHijri(now);
        document.getElementById('hijriDate').innerText = '🌙 ' + h.day + ' ' + HIJRI_MONTHS[h.month - 1] + ' ' + h.year + ' هـ';
    } catch(e) {}
    document.getElementById('gregorianDate').innerText = '📅 ' + now.getDate() + ' ' + SYRIAN_MONTHS[now.getMonth()] + ' ' + now.getFullYear() + ' م';
}

function showAbout() { document.getElementById('aboutModal').classList.add('show'); }
function hideAbout() { document.getElementById('aboutModal').classList.remove('show'); }

document.addEventListener('DOMContentLoaded', async function() {
    const booksBar = document.getElementById('booksBar');
    if (booksBar) {
        Object.keys(BOOKS).forEach(function(key) {
            const btn = document.createElement('button');
            btn.className = 'book-btn';
            btn.dataset.book = key;
            btn.textContent = BOOKS[key];
            btn.onclick = function() { selectBook(key); };
            booksBar.appendChild(btn);
        });
    }
    
    const booksCheckboxes = document.getElementById('booksCheckboxes');
    if (booksCheckboxes) {
        Object.keys(BOOKS).forEach(function(key) {
            const div = document.createElement('div');
            div.className = 'book-checkbox';
            div.innerHTML = '<input type="checkbox" id="chk_' + key + '" class="book-chk" value="' + key + '"><label for="chk_' + key + '">' + BOOKS[key] + '</label>';
            booksCheckboxes.appendChild(div);
        });
    }
    
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
    }
    
    updateTime();
    setInterval(updateTime, 1000);
    
    await loadQuranData();
    setTimeout(detectLocation, 500);
});
