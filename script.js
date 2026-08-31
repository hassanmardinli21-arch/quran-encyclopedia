let quranData = [];

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('quran.json');
        const data = await response.json();
        
        // استخراج كل الآيات من جميع السور
        quranData = [];
        data.forEach(surah => {
            if (surah.ayahs && Array.isArray(surah.ayahs)) {
                surah.ayahs.forEach(ayah => {
                    quranData.push({
                        surah: surah.name,
                        number: ayah.number,
                        text: ayah.text,
                        numberInSurah: ayah.numberInSurah
                    });
                });
            }
        });
        
        displayData(quranData);
    } catch (error) {
        document.getElementById('quranContainer').innerHTML = `
            <div class="error-message">
                عذراً، حدث خطأ أثناء تحميل بيانات الموسوعة.
            </div>
        `;
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
        container.innerHTML = '<div class="no-results">لا توجد نتائج مطابقة للبحث.</div>';
        countDiv.textContent = 'عدد النتائج: 0';
        return;
    }

    countDiv.textContent = `عدد النتائج: ${items.length}`;
    
    // عرض النتائج (حد أقصى 100 لتحسين الأداء)
    container.innerHTML = items.slice(0, 100).map(item => `
        <div class="quran-item">
            <p>${highlightText(item.text || '', document.getElementById('searchInput').value)}</p>
            <span class="ayah-info">${item.surah} - آية ${item.numberInSurah}</span>
        </div>
    `).join('');
}

function filterData(query) {
    if (!query) {
        displayData(quranData);
        return;
    }
    const filtered = quranData.filter(item => 
        item.text && item.text.includes(query)
    );
    displayData(filtered);
}

function highlightText(text, keyword) {
    if (!keyword) return text;
    const regex = new RegExp(`(${keyword})`, 'g');
    return text.replace(regex, '<mark>$1</mark>');
}
