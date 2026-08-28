let quranData = [];

// جلب بيانات ملف quran.json عند فتح الصفحة
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('quran.json');
        quranData = await response.json();
        displayData(quranData);
    } catch (error) {
        document.getElementById('quranContainer').innerHTML = '<p style="color:red; text-align:center;">عذراً، حدث خطأ أثناء تحميل بيانات الموسوعة.</p>';
        console.error('Error loading JSON:', error);
    }

    // تفعيل البحث الفوري
    document.getElementById('searchInput').addEventListener('input', (e) => {
        const query = e.target.value.trim();
        filterData(query);
    });
});

function displayData(items) {
    const container = document.getElementById('quranContainer');
    const countDiv = document.getElementById('resultsCount');
    
    if (items.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#777;">لا توجد نتائج مطابقة للبحث.</p>';
        countDiv.textContent = 'عدد النتائج: 0';
        return;
    }

    countDiv.textContent = `عدد النتائج: ${items.length}`;
    
    // عرض عينة أو النتائج (يمكن تحديد عدد العرض إذا كانت البيانات ضخمة جداً لتحسين الأداء)
    container.innerHTML = items.slice(0, 100).map(item => `
        <div class="quran-item">
            <p>${highlightText(item.text || '', document.getElementById('searchInput').value)}</p>
        </div>
    `).join('');
}

function filterData(query) {
    if (!query) {
        displayData(quranData);
        return;
    }
    const filtered = quranData.filter(item => item.text && item.text.includes(query));
    displayData(filtered);
}

function highlightText(text, keyword) {
    if (!keyword) return text;
    const regex = new RegExp(`(${keyword})`, 'g');
    return text.replace(regex, '<mark>$1</mark>');
}