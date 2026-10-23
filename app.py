                }
                
                let html = `<div class="hadith-card">
                    <div class="hadith-header">
                        <span class="hadith-book-name">🔍 نتائج البحث في القرآن الكريم</span>
                        <span class="hadith-number">${quranResults.length} نتيجة</span>
                    </div>
                    <div class="search-results">`;
                quranResults.forEach((item, idx) => {
                    const preview = item.text.length > 250 ? item.text.substring(0, 250) + '...' : item.text;
                    html += `<div class="search-result-item" onclick="selectQuran().then(()=>showSurah(${item.surah}).then(()=>scrollToAyah(${item.ayah})))">
                        <div class="res-num">#${idx + 1} — 📖 سورة ${escapeHtml(item.surah_name)} - آية ${item.ayah}
                            <span class="res-abjad-badge">جُمّل: ${item.abjad || 0}</span>
                        </div>
                        <div class="res-text">${safeHighlight(preview, query)}</div>
                    </div>`;
                });
                html += '</div></div>';
                content.innerHTML = html;
                return;
            } catch(e) {
                content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ في البحث في القرآن</div>';
                return;
            }
        }
        
        if (!currentBook) { currentBook = 'bukhari'; setActiveBook('bukhari'); }
        
        try {
            const res = await fetch(`/api/search?book=${currentBook}&query=${encodeURIComponent(query)}&type=${type}`);
            if (!res.ok) throw new Error('فشل الاتصال');
            const data = await res.json();
            
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = `<div class="hadith-card" style="text-align:center;">لا توجد نتائج لـ "${escapeHtml(query)}" في ${getBookName(currentBook)}</div>`;
                return;
            }
            
            let html = `<div class="hadith-card">
                <div class="hadith-header">
                    <span class="hadith-book-name">🔍 نتائج البحث في ${getBookName(currentBook)}</span>
                    <span class="hadith-number">${data.length} نتيجة</span>
                </div>
                <div class="search-results">`;
            data.forEach(item => {
                const preview = item.text.length > 250 ? item.text.substring(0, 250) + '...' : item.text;
                html += `<div class="search-result-item" onclick="showHadith(${item.index})">
                    <div class="res-num">📌 حديث رقم ${item.id}
                        <span class="res-abjad-badge">جُمّل: ${item.abjad || 0}</span>
                    </div>
                    ${item.narrator ? `<div style="color:#b8860b;font-size:13px;margin:5px 0;">🎙️ ${escapeHtml(item.narrator)}</div>` : ''}
                    <div class="res-text">${safeHighlight(preview, query)}</div>
                </div>`;
            });
            html += '</div></div>';
            content.innerHTML = html;
        } catch(e) {
            content.innerHTML = '<div class="hadith-card" style="text-align:center;color:red;">حدث خطأ في البحث</div>';
        }
    }

    function getBookName(bookId) {
        const names = {'quran': 'القرآن الكريم', {% for key, value in books.items() %}'{{ key }}': '{{ value }}',{% endfor %}};
        return names[bookId] || bookId;
    }
    function copyHadith() {
        const el = document.getElementById('hadithText'); if (!el) return;
        navigator.clipboard.writeText(el.innerText).then(() => {
            const btns = document.querySelectorAll('.copy-btn');
            btns.forEach(b => { if (b.innerText.includes('نسخ')) { const o = b.innerText; b.innerText = '✅ تم النسخ'; setTimeout(() => b.innerText = o, 1500); } });
        });
    }
    function escapeHtml(text) { if (text === null || text === undefined) return ''; const div = document.createElement('div'); div.textContent = String(text); return div.innerHTML; }
    function safeHighlight(text, query) {
        if (!query || !text) return escapeHtml(text || '');
        try {
            const safeText = String(text);
            const safeQuery = String(query);
            let parts = safeText.split(safeQuery);
            if (parts.length > 1) {
                let result = '';
                for (let i = 0; i < parts.length; i++) {
                    result += escapeHtml(parts[i]);
                    if (i < parts.length - 1) result += '<mark>' + escapeHtml(safeQuery) + '</mark>';
                }
                return result;
            }
            const cleanText = strip_diacritics(safeText);
            const cleanQuery = strip_diacritics(safeQuery);
            if (cleanText.includes(cleanQuery)) {
                const regex = new RegExp(cleanQuery.split('').map(ch => ch + '[\\u064B-\\u0652]*').join(''), 'gi');
                let result = '';
                let lastIndex = 0;
                let match;
                while ((match = regex.exec(cleanText)) !== null) {
                    const originalIndex = safeText.indexOf(match[0]);
                    if (originalIndex !== -1) {
                        result += escapeHtml(safeText.substring(lastIndex, originalIndex));
                        result += '<mark>' + escapeHtml(match[0]) + '</mark>';
                        lastIndex = originalIndex + match[0].length;
                    }
                }
                if (result) { result += escapeHtml(safeText.substring(lastIndex)); return result; }
            }
            return escapeHtml(safeText);
        } catch(e) { return escapeHtml(text); }
    }
    function strip_diacritics(text) { return String(text).replace(/[\u064B-\u0652\u0670\u0640]/g, ''); }
    function abjadOfText(text) { if (!text) return 0; const clean = String(text).replace(/[\u064B-\u0652\u0670\u0640]/g, ''); let total = 0; for (const ch of clean) { total += (ABJAD_MAP[ch] || 0); } return total; }
</script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
