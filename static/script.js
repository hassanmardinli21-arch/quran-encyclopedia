// متغير عام لتخزين بيانات الكتب والأحاديث المحملة
let globalBooksData = [];

// مسار ملف الـ JSON الأساسي (قم بتعديل اسم الملف ليطابق الملف الفعلي المستخرج لدس كتب الأحاديث، مثل bukhari.json أو ما تريده)
const BOOK_FILE_PATH = 'data/extracted_books/bukhari.json'; // يمكنك تبديله بأي ملف آخر من المجلد المستخرج

async function loadEncyclomediaData() {
    const container = document.getElementById('quranContainer');
    const resultsCount = document.getElementById('resultsCount');

    try {
        container.innerHTML = '<p class="loading">جاري تحميل الموسوعة والكتب، يرجى الانتظار...</p>';
        
        // جلب ملف الـ JSON
        let response = await fetch(BOOK_FILE_PATH);
        if (!response.ok) {
            throw new Error(`تعذر تحميل الملف (حالة الاستجابة: ${response.status})`);
        }
        
        globalBooksData = await response.json();
        
        resultsCount.textContent = `تم تحميل ${globalBooksData.length} نصاً/حديثاً بنجاح.`;
        displayData(globalBooksData);

    } catch (error) {
        console.error("خطأ في جلب البيانات:", error);
        container.innerHTML = `<p class="loading" style="color: red;">عذراً، حدث خطأ أثناء تحميل البيانات. تأكد من مسار الملف أو وجوده في مجلد data/extracted_books/.</p>`;
    }
}

// دالة لعرض البيانات في الصفحة
function displayData(items) {
    const container = document.getElementById('quranContainer');
    container.innerHTML = '';

    if (items.length === 0) {
        container.innerHTML = '<p class="loading">لا توجد نتائج مطابقة للبحث.</p>';
        return;
    }

    // عرض أول 100 عنصر كمرحلة أولية لضمان سرعة التصفح وعدم ثقيل الصفحة
    const itemsToShow = items.slice(0, 100);

    itemsToShow.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'hadith-card'; // يمكنك تنسيق هذا الصندوق في ملف style.css
        
        // استخراج النص العربي بغض النظر عن اختلاف المفتاح (arabic أو text)
        let arabicText = item.arabic || item.text || item.content || "النص غير متوفر";
        let itemId = item.id || item.idInBook || (index + 1);
        let rawiName = item.rawiName ? `<strong>الراوي/العنوان:</strong> ${item.rawiName}<br>` : '';

        card.innerHTML = `
            <div class="hadith-header"><span>رقم: ${itemId}</span></div>
            <div class="hadith-body">
                <p>${rawiName}${arabicText}</p>
            </div>
        `;
        container.appendChild(card);
    });

    if (items.length > 100) {
        const info = document.createElement('p');
        info.style.textAlign = 'center';
        info.style.padding = '15px';
        info.style.color = '#666';
        info.textContent = `يتم عرض أول 100 نتيجة من أصل ${items.length}. استخدم البحث لتصفية النتائج بدقة.`;
        container.appendChild(info);
    }
}

// وظيفة البحث الحي عند الكتابة في خانة البحث
document.getElementById('searchInput').addEventListener('input', function (e) {
    const searchTerm = e.target.value.toLowerCase().trim();
    const resultsCount = document.getElementById('resultsCount');

    if (!searchTerm) {
        resultsCount.textContent = `تم تحميل ${globalBooksData.length} نصاً/حديثاً بنجاح.`;
        displayData(globalBooksData);
        return;
    }

    const filtered = globalBooksData.filter(item => {
        let text = (item.arabic || item.text || item.content || "").toLowerCase();
        let name = (item.rawiName || "").toLowerCase();
        return text.includes(searchTerm) || name.includes(searchTerm);
    });

    resultsCount.textContent = `عدد النتائج المطابقة لـ "${searchTerm}": ${filtered.length}`;
    displayData(filtered);
});

// تشغيل الدالة عند تحميل الصفحة مباشرة
window.addEventListener('DOMContentLoaded', loadEncyclomediaData);