from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import sqlite3

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(BASE_DIR, 'sync_bookmarks.db')


# ============ قاعدة البيانات ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks (
        sync_code TEXT PRIMARY KEY,
        surah INTEGER NOT NULL,
        ayah INTEGER NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS special_bookmarks (
        id TEXT PRIMARY KEY,
        sync_code TEXT NOT NULL,
        label TEXT NOT NULL,
        surah INTEGER NOT NULL,
        ayah INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_special_code ON special_bookmarks(sync_code)')
    conn.commit()
    conn.close()

init_db()


# ============ الصفحة الرئيسية ============
@app.route('/')
def index():
    return render_template('index.html')


# ============ خدمة ملفات JSON (يبحث في data/ ثم الجذر) ============
@app.route('/<path:filename>')
def serve_data(filename):
    if not filename.endswith('.json'):
        return jsonify({'error': 'not found'}), 404
    
    # 1) ابحث في مجلد data أولاً
    if os.path.exists(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            return send_from_directory(DATA_DIR, filename)
    
    # 2) ثم ابحث في الجذر
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(BASE_DIR, filename)
    
    return jsonify({'error': 'not found'}), 404


# ============ علامة "آخر قراءة" ============
@app.route('/api/sync_bookmark', methods=['POST'])
def save_bookmark():
    data = request.get_json(silent=True) or {}
    code = (data.get('sync_code') or '').strip().upper()
    surah = data.get('surah')
    ayah = data.get('ayah')

    if not code or len(code) < 8:
        return jsonify({'status': 'error'}), 400
    try:
        surah = int(surah)
        ayah = int(ayah)
    except (TypeError, ValueError):
        return jsonify({'status': 'error'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO bookmarks (sync_code, surah, ayah, updated_at)
                 VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                 ON CONFLICT(sync_code) DO UPDATE SET
                     surah = excluded.surah,
                     ayah = excluded.ayah,
                     updated_at = CURRENT_TIMESTAMP''', (code, surah, ayah))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/api/get_bookmark/<code>', methods=['GET'])
def get_bookmark(code):
    code = code.strip().upper()
    if len(code) < 8:
        return jsonify({'status': 'error'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT surah, ayah FROM bookmarks WHERE sync_code = ?', (code,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({'status': 'success', 'surah': row[0], 'ayah': row[1]})
    return jsonify({'status': 'empty'})


@app.route('/api/delete_bookmark', methods=['POST'])
def delete_bookmark():
    data = request.get_json(silent=True) or {}
    code = (data.get('sync_code') or '').strip().upper()
    if not code or len(code) < 8:
        return jsonify({'status': 'error'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM bookmarks WHERE sync_code = ?', (code,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


# ============ العلامات الخاصة (📌) ============
@app.route('/api/special_bookmarks/<code>', methods=['GET'])
def get_special_bookmarks(code):
    code = code.strip().upper()
    if len(code) < 8:
        return jsonify({'status': 'error'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, label, surah, ayah FROM special_bookmarks WHERE sync_code = ?', (code,))
    rows = c.fetchall()
    conn.close()
    bookmarks = [{'id': r[0], 'label': r[1], 'surah': r[2], 'ayah': r[3]} for r in rows]
    return jsonify({'status': 'success', 'bookmarks': bookmarks})


@app.route('/api/special_bookmarks', methods=['POST'])
def save_special_bookmarks():
    data = request.get_json(silent=True) or {}
    code = (data.get('sync_code') or '').strip().upper()
    bookmarks = data.get('bookmarks') or []

    if not code or len(code) < 8:
        return jsonify({'status': 'error'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM special_bookmarks WHERE sync_code = ?', (code,))
    for b in bookmarks:
        try:
            bid = str(b.get('id', '')).strip()
            label = str(b.get('label', '')).strip()[:200]
            surah = int(b.get('surah', 1))
            ayah = int(b.get('ayah', 1))
            if not bid or not label:
                continue
            c.execute('''INSERT OR REPLACE INTO special_bookmarks
                         (id, sync_code, label, surah, ayah)
                         VALUES (?, ?, ?, ?, ?)''',
                      (bid, code, label, surah, ayah))
        except (ValueError, TypeError):
            continue
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)