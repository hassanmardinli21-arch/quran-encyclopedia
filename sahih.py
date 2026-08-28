import tkinter as tk
from tkinter import messagebox, Toplevel
import webbrowser
import urllib.parse
import os
import json
import zipfile
import re
import unicodedata
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
import threading


class CompleteHadithApp:
    """الموسوعة الإسلامية الشاملة"""

    BOOK_SPECS = [
        ("صحيح البخاري", "the_9_books/bukhari.json"),
        ("صحيح مسلم", "the_9_books/muslim.json"),
        ("سنن أبي داود", "the_9_books/abudawud.json"),
        ("جامع الترمذي", "the_9_books/tirmidhi.json"),
        ("سنن النسائي", "the_9_books/nasai.json"),
        ("سنن ابن ماجه", "the_9_books/ibnmajah.json"),
        ("موطأ مالك", "the_9_books/malik.json"),
        ("مسند أحمد", "the_9_books/ahmed.json"),
        ("سنن الدارمي", "the_9_books/darimi.json"),
        ("رياض الصالحين", "other_books/riyad_assalihin.json"),
        ("الشمائل المحمدية", "other_books/shamail_muhammadiyah.json"),
        ("بلوغ المرام", "other_books/bulugh_almaram.json"),
        ("الأدب المفرد", "other_books/aladab_almufrad.json"),
        ("مشكاة المصابيح", "other_books/mishkat_almasabih.json"),
        ("الأربعون النووية", "forties/nawawi40.json"),
        ("الأربعون القدسية", "forties/qudsi40.json"),
        ("أربعون الشاه ولي الله", "forties/shahwaliullah40.json"),

        # الكتب الإضافية
        (
            "الأحاديث الضعيفة للألباني",
            r"C:\Users\me\3D Objects\Desktop\albani\الألباني_الموحد.json"
        ),
        (
            "الفتن لابن حماد",
            r"C:\Users\me\3D Objects\Desktop\albani\الفتن ابن حماد.json"
        ),
        (
            "المجروحين من المحدثين",
            r"C:\Users\me\3D Objects\Desktop\albani\الرواة\المجروحين_من_المحدثين.json"
        ),
        (
            "تهذيب التهذيب",
            r"C:\Users\me\3D Objects\Desktop\albani\الرواة\تهذيب_التهذيب.json"
        ),
        (
            "تهذيب الكمال في أسماء الرجال",
            r"C:\Users\me\3D Objects\Desktop\albani\الرواة\تهذيب_الكمال_في_أسماء_الرجال.json"
        ),
    ]

    ARABIC_DIGITS = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789"
    )

    def __init__(self, root):
        self.root = root
        self.root.title("الموسوعة الإسلامية الشاملة")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        window_w = min(1180, max(900, screen_w - 40))
        window_h = min(720, max(600, screen_h - 90))

        self.root.geometry(f"{window_w}x{window_h}")
        self.root.minsize(850, 560)

        self.primary_color = "#1b4332"
        self.secondary_color = "#2d6a4f"
        self.bg_color = "#d8f3dc"

        self.root.configure(bg=self.bg_color)

        # -----------------------------
        # حالة قاعدة البيانات
        # -----------------------------
        self.library_books = {}
        self.hadith_records = []
        self.data_ready = False

        self.current_book_title = ""
        self.current_page_index = 0

        # -----------------------------
        # الخطوط
        # -----------------------------
        self.hadith_font_size = 13
        self.hadith_min_font_size = 10
        self.hadith_max_font_size = 32

        self.index_font_size = 10
        self.index_min_font_size = 7
        self.index_max_font_size = 18

        # ---- حجم خط قائمة الفهرس في نافذة الفهرس ----
        self.listbox_font_size = 10
        self.listbox_min_font_size = 7
        self.listbox_max_font_size = 18

        # -----------------------------
        # مراجع الواجهة
        # -----------------------------
        self.status_bar = None
        self.text_area = None
        self.page_label = None
        self.prev_btn = None
        self.next_btn = None

        self.buttons_container = None
        self.book_buttons = []

        self.index_font_label = None
        self.font_size_label = None

        self.canvas = None
        self.scrollbar = None

        self.is_selecting = False

        # -----------------------------
        # بناء الواجهة
        # -----------------------------
        self.build_header()
        self.build_top_control_bar()

        self.container = tk.Frame(
            self.root,
            bg=self.bg_color
        )
        self.container.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        self.build_hadith_section()
        self.build_prayer_section()
        self.build_notes_section()

        # -----------------------------
        # شريط الحالة
        # -----------------------------
        self.status_frame = tk.Frame(
            self.root,
            bg="#2c3e50",
            height=34
        )
        self.status_frame.pack(
            side=tk.BOTTOM,
            fill=tk.X
        )
        self.status_frame.pack_propagate(False)

        self.status_bar = tk.Label(
            self.status_frame,
            text="⏳ جاري فتح الكتب...",
            bg="#2c3e50",
            fg="white",
            font=("Arial", 10),
            anchor=tk.W,
            padx=10
        )
        self.status_bar.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        self.show_hadith_section()

        self.root.after(
            50,
            self.load_local_hadith_database
        )

    # =========================================================
    # الشريط العلوي
    # =========================================================

    def build_header(self):
        header_frame = tk.Frame(
            self.root,
            bg=self.primary_color,
            height=175
        )
        header_frame.pack(
            fill=tk.X,
            side=tk.TOP
        )
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="🕌 الموسوعة الإسلامية الشاملة",
            font=("Arial", 18, "bold"),
            bg=self.primary_color,
            fg="white"
        ).pack(pady=5)

        row1 = tk.Frame(
            header_frame,
            bg=self.primary_color
        )
        row1.pack(pady=2)

        self.make_button(
            row1,
            "📖 المكتبة",
            self.secondary_color,
            self.show_hadith_section
        )

        self.make_button(
            row1,
            "🕌 الصلاة",
            self.secondary_color,
            self.show_prayer_section
        )

        self.make_button(
            row1,
            "📝 الملاحظات",
            self.secondary_color,
            self.show_notes_section
        )

        self.make_button(
            row1,
            "ℹ️ عن",
            "#52b788",
            self.show_about_dialog
        )

        self.make_button(
            row1,
            "📤 مشاركة",
            "#f39c12",
            self.share_app
        )

        self.make_button(
            row1,
            "🖥️ سطح المكتب",
            "#8e44ad",
            self.create_desktop_shortcut
        )

        row2 = tk.Frame(
            header_frame,
            bg=self.primary_color
        )
        row2.pack(pady=5)

        tk.Label(
            row2,
            text="🔍:",
            font=("Arial", 11, "bold"),
            bg=self.primary_color,
            fg="white"
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        self.search_entry = tk.Entry(
            row2,
            font=("Arial", 11),
            width=28
        )
        self.search_entry.pack(
            side=tk.LEFT,
            padx=5
        )

        self.search_entry.insert(
            0,
            "اكتب كلمة للبحث..."
        )

        self.search_entry.bind(
            "<FocusIn>",
            lambda e: self.clear_search_placeholder()
        )

        self.search_entry.bind(
            "<KeyRelease>",
            self.highlight_text
        )

        self.search_entry.bind(
            "<Return>",
            lambda e: self.search_all_books()
        )

        self.make_button(
            row2,
            "📋 نسخ",
            "#2980b9",
            self.copy_search_text,
            small=True
        )

        self.make_button(
            row2,
            "📋 لصق",
            "#27ae60",
            self.paste_search_text,
            small=True
        )

        self.make_button(
            row2,
            "🗑 مسح",
            "#c0392b",
            self.clear_search_box_and_highlight,
            small=True
        )

        self.make_button(
            row2,
            "👤 ترجمة الراوي",
            "#8e44ad",
            self.search_narrator
        )

        self.make_button(
            row2,
            "📜 ترجمة المحدث",
            "#c0392b",
            self.search_muhaddith
        )

        self.make_button(
            row2,
            "🔢 رقم الحديث",
            "#e67e22",
            self.search_by_hadith_number,
            small=True
        )

        self.make_button(
            row2,
            "🔍 بحث عام",
            "#2a9d8f",
            self.search_all_books,
            small=True
        )

        self.make_button(
            row2,
            "🌐 نت",
            "#1d3557",
            self.search_on_web,
            small=True
        )

    def build_top_control_bar(self):
        """شريط أسود ثابت لأزرار تكبير وتصغير النص"""
        self.top_control_bar = tk.Frame(
            self.root,
            bg="#111111",
            height=42
        )
        self.top_control_bar.pack(
            fill=tk.X,
            side=tk.TOP
        )
        self.top_control_bar.pack_propagate(False)

        tk.Label(
            self.top_control_bar,
            text="🔤 حجم النص:",
            font=("Arial", 10, "bold"),
            bg="#111111",
            fg="white"
        ).pack(
            side=tk.RIGHT,
            padx=(8, 3),
            pady=5
        )

        tk.Button(
            self.top_control_bar,
            text="🔎 تصغير النص",
            font=("Arial", 10, "bold"),
            bg="#7f8c8d",
            fg="white",
            activebackground="#95a5a6",
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=3,
            command=self.decrease_hadith_font
        ).pack(
            side=tk.RIGHT,
            padx=3,
            pady=5
        )

        tk.Button(
            self.top_control_bar,
            text="🔍 تكبير النص",
            font=("Arial", 10, "bold"),
            bg="#8e44ad",
            fg="white",
            activebackground="#9b59b6",
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=3,
            command=self.increase_hadith_font
        ).pack(
            side=tk.RIGHT,
            padx=3,
            pady=5
        )

        self.font_size_label = tk.Label(
            self.top_control_bar,
            text="13",
            font=("Arial", 10, "bold"),
            bg="#111111",
            fg="white",
            width=4
        )
        self.font_size_label.pack(
            side=tk.RIGHT,
            padx=4,
            pady=5
        )

        # اختصارات لوحة المفاتيح
        self.root.bind(
            "<Control-plus>",
            lambda e: self.increase_hadith_font()
        )
        self.root.bind(
            "<Control-KP_Add>",
            lambda e: self.increase_hadith_font()
        )
        self.root.bind(
            "<Control-minus>",
            lambda e: self.decrease_hadith_font()
        )
        self.root.bind(
            "<Control-KP_Subtract>",
            lambda e: self.decrease_hadith_font()
        )

    def make_button(self, parent, text, bg, command, small=False):
        tk.Button(
            parent,
            text=text,
            font=("Arial", 9 if small else 10, "bold"),
            bg=bg,
            fg="white",
            padx=8 if small else 10,
            pady=2 if small else 3,
            command=command
        ).pack(
            side=tk.LEFT,
            padx=2 if small else 4
        )

    # =========================================================
    # البحث
    # =========================================================

    def clear_search_placeholder(self):
        if self.search_entry.get() == "اكتب كلمة للبحث...":
            self.search_entry.delete(0, tk.END)

    def normalize_arabic(self, text):
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", str(text))
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

        replacements = {
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",
            "ٱ": "ا",
            "ى": "ي",
            "ؤ": "و",
            "ئ": "ي",
            "ة": "ه",
            "ۃ": "ه",
            "ﷲ": "الله",
            "ﷻ": "الله",
            "لآ": "لا"
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        text = text.replace("ـ", "")
        return re.sub(r"\s+", " ", text).strip().lower()

    def extract_number_from_query(self, query):
        match = re.search(
            r"(?:رقم\s*الحديث|الحديث\s*رقم|رقم)\s*[:：\-]?\s*([0-9٠-٩]+)",
            query,
            re.IGNORECASE
        )
        if not match:
            return None
        try:
            return int(match.group(1).translate(self.ARABIC_DIGITS))
        except ValueError:
            return None

    def extract_book_from_query(self, query):
        normalized = self.normalize_arabic(query)
        for book in self.library_books:
            if self.normalize_arabic(book) in normalized:
                return book
        return None

    def clean_pasted_query(self, query):
        for symbol in ["📖", "❌", "🔢", "👤", "🔹", "📝", "⭐", "📌"]:
            query = query.replace(symbol, " ")
        return re.sub(r"\s+", " ", query).strip()

    # =========================================================
    # قاعدة البيانات
    # =========================================================

    def database_zip_candidates(self):
        app_dir = Path(__file__).resolve().parent
        return [
            app_dir / "data" / "hadith-json-1.2.0.zip",
            app_dir / "hadith-json-1.2.0.zip"
        ]

    def load_local_hadith_database(self):
        try:
            zip_path = next(
                (p for p in self.database_zip_candidates() if p.is_file()),
                None
            )

            loaded_books = {}
            all_records = []

            # الكتب الموجودة داخل ZIP
            if zip_path:
                self.status_bar.config(text="⏳ جاري فتح الكتب الأساسية...")
                self.root.update_idletasks()

                with zipfile.ZipFile(zip_path, "r") as zf:
                    archive_names = set(zf.namelist())

                    for book_name, relative_path in self.BOOK_SPECS:
                        if (
                            relative_path.startswith("C:")
                            or relative_path.startswith("F:")
                            or relative_path.startswith("http")
                        ):
                            continue

                        archive_path = "hadith-json-1.2.0/db/by_book/" + relative_path

                        if archive_path not in archive_names:
                            continue

                        try:
                            data = json.loads(zf.read(archive_path).decode("utf-8"))
                            records = self.parse_json_book(data, book_name)

                            if records:
                                loaded_books[book_name] = records
                                all_records.extend(records)
                                print(f"✅ تم تحميل {len(records)} من {book_name}")

                        except Exception as e:
                            print(f"⚠️ خطأ في تحميل {book_name}: {e}")

            # الكتب الإضافية
            self.status_bar.config(text="⏳ جاري فتح الكتب الإضافية...")
            self.root.update_idletasks()

            for book_name, file_path in self.BOOK_SPECS:
                if file_path.startswith("C:") or file_path.startswith("F:"):
                    json_path = Path(file_path)

                    if not json_path.exists():
                        print(f"⚠️ الملف غير موجود: {json_path}")
                        continue

                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        records = self.parse_json_book(data, book_name)

                        if records:
                            loaded_books[book_name] = records
                            all_records.extend(records)
                            print(f"✅ تم تحميل {len(records)} من {book_name}")

                    except Exception as e:
                        print(f"⚠️ خطأ في تحميل {book_name}: {e}")

            if not loaded_books:
                raise RuntimeError("لم يتم العثور على كتب قابلة للقراءة.")

            self.library_books = loaded_books
            self.hadith_records = all_records
            self.data_ready = True

            self.current_book_title = next(iter(self.library_books))
            self.current_page_index = 0

            self.root.after(100, self.refresh_book_index)
            self.root.after(200, self.load_current_page)

            self.status_bar.config(
                text=(
                    f"✅ تم فتح {len(self.library_books)} كتابًا — "
                    f"{len(self.hadith_records):,} حديث"
                )
            )

        except Exception as exc:
            self.data_ready = False
            self.status_bar.config(text=f"❌ تعذر فتح الكتب: {exc}")

            if self.text_area is not None:
                self.text_area.delete("1.0", tk.END)
                # نضيف \u200F في البداية لتوجيه النص
                self.text_area.insert(
                    tk.END,
                    "\u200F📚 لم يتم فتح قاعدة الكتب.\n\n"
                    f"الخطأ: {exc}\n\n"
                    "تأكد من وجود ملف hadith-json-1.2.0.zip في مجلد data/"
                )

            import traceback
            traceback.print_exc()

    def parse_json_book(self, data, book_name):
        records = []
        items = []

        if isinstance(data, dict) and isinstance(data.get("hadiths"), list):
            items = data["hadiths"]
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict) and isinstance(data.get("data"), list):
            items = data["data"]

        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue

            arabic = item.get("arabic") or item.get("text") or ""
            if isinstance(arabic, dict):
                arabic = arabic.get("text") or arabic.get("arabic") or ""

            if not arabic:
                continue

            try:
                number = int(item.get("idInBook") or item.get("id") or index)
            except (ValueError, TypeError):
                number = index

            english = item.get("english")
            narrator = ""

            if isinstance(english, dict):
                narrator = str(english.get("narrator") or "").strip()
            elif isinstance(english, str):
                narrator_match = re.search(
                    r'narrator["\']?\s*[:：]\s*["\']?([^"\']+)',
                    english,
                    re.IGNORECASE
                )
                if narrator_match:
                    narrator = narrator_match.group(1).strip()

            records.append({
                "book": book_name,
                "number": number,
                "arabic": str(arabic).strip(),
                "narrator": narrator,
                "details": ""
            })

        records.sort(key=lambda r: r["number"])
        return records

    # =========================================================
    # دوال تبديل الأقسام
    # =========================================================

    def hide_all_sections(self):
        for attr in ("hadith_frame", "prayer_frame", "notes_frame"):
            frame = getattr(self, attr, None)
            if frame is not None:
                frame.pack_forget()

    def show_hadith_section(self):
        self.hide_all_sections()
        self.hadith_frame.pack(fill=tk.BOTH, expand=True)
        self.highlight_text()

    def show_prayer_section(self):
        self.hide_all_sections()
        self.prayer_frame.pack(fill=tk.BOTH, expand=True)

    def show_notes_section(self):
        self.hide_all_sections()
        self.notes_frame.pack(fill=tk.BOTH, expand=True)

    # =========================================================
    # بناء قسم الحديث
    # =========================================================

    def build_hadith_section(self):
        self.hadith_frame = tk.Frame(self.container, bg=self.bg_color)
        main_content = tk.Frame(self.hadith_frame, bg=self.bg_color)
        main_content.pack(fill=tk.BOTH, expand=True, pady=5)

        # ---- فهرس الكتب ----
        index_frame = tk.LabelFrame(
            main_content,
            text=" فهرس الكتب ",
            font=("Arial", 11, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        )
        index_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # أزرار التحكم بحجم الفهرس
        index_control_frame = tk.Frame(index_frame, bg=self.bg_color)
        index_control_frame.pack(fill=tk.X, padx=5, pady=2)

        tk.Label(
            index_control_frame,
            text="📏 حجم خط الفهرس:",
            font=("Arial", 9),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(
            index_control_frame,
            text="🔎 تصغير",
            font=("Arial", 8, "bold"),
            bg="#e74c3c",
            fg="white",
            padx=8,
            pady=2,
            command=self.decrease_index_font,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=2)

        tk.Button(
            index_control_frame,
            text="🔍 تكبير",
            font=("Arial", 8, "bold"),
            bg="#27ae60",
            fg="white",
            padx=8,
            pady=2,
            command=self.increase_index_font,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=2)

        self.index_font_label = tk.Label(
            index_control_frame,
            text=str(self.index_font_size),
            font=("Arial", 9, "bold"),
            bg=self.bg_color,
            fg=self.secondary_color,
            width=4
        )
        self.index_font_label.pack(side=tk.RIGHT, padx=5)

        # إطار أزرار الكتب
        book_buttons_frame = tk.Frame(index_frame, bg=self.bg_color)
        book_buttons_frame.pack(fill=tk.X, padx=5, pady=2)

        self.canvas = tk.Canvas(book_buttons_frame, bg="#ffffff", height=80, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(book_buttons_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)

        self.buttons_container = tk.Frame(self.canvas, bg="#ffffff")

        self.buttons_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.buttons_container, anchor="nw")
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.book_buttons = []

        # ---- منطقة عرض النص ----
        reader_frame = tk.Frame(main_content, bg=self.bg_color)
        reader_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5)

        # إنشاء Text بدون justify (الافتراضي left)
        self.text_area = tk.Text(
            reader_frame,
            font=("Arial", self.hadith_font_size),
            wrap=tk.WORD,
            bg="#ffffff",
            padx=12,
            pady=12
        )

        scrollbar_vertical = tk.Scrollbar(
            reader_frame,
            orient=tk.VERTICAL,
            command=self.text_area.yview
        )

        self.text_area.configure(yscrollcommand=scrollbar_vertical.set)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_vertical.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area.tag_configure("highlight", background="yellow", foreground="black")

        # ---- شريط التنقل ----
        nav_frame = tk.Frame(reader_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=5)

        self.page_label = tk.Label(
            nav_frame,
            text="قاعدة البيانات",
            font=("Arial", 10),
            bg=self.bg_color,
            fg=self.secondary_color
        )
        self.page_label.pack(side=tk.TOP, pady=2)

        btn_frame = tk.Frame(nav_frame, bg=self.bg_color)
        btn_frame.pack()

        tk.Button(
            btn_frame,
            text="📋 نسخ الحديث",
            font=("Arial", 10, "bold"),
            bg="#2980b9",
            fg="white",
            padx=10,
            pady=3,
            command=self.copy_hadith_text
        ).pack(side=tk.LEFT, padx=4)

        self.prev_btn = tk.Button(
            btn_frame,
            text="▶ السابق",
            font=("Arial", 10, "bold"),
            bg=self.secondary_color,
            fg="white",
            command=self.prev_page,
            width=12
        )
        self.prev_btn.pack(side=tk.RIGHT, padx=4)

        self.next_btn = tk.Button(
            btn_frame,
            text="التالي ◀",
            font=("Arial", 10, "bold"),
            bg=self.primary_color,
            fg="white",
            command=self.next_page,
            width=12
        )
        self.next_btn.pack(side=tk.LEFT, padx=4)

        # النص الأولي مع \u200F
        self.text_area.insert(
            tk.END,
            "\u200F⏳ جاري فتح الكتب...\n\nسيتم عرض الكتب هنا تلقائياً."
        )

    # =========================================================
    # دوال الفهرس
    # =========================================================

    def increase_index_font(self):
        if self.index_font_size < self.index_max_font_size:
            self.index_font_size += 1
            self.update_index_display()
            self.refresh_book_index()
            self.status_bar.config(text=f"🔍 تم تكبير خط الفهرس إلى {self.index_font_size}")

    def decrease_index_font(self):
        if self.index_font_size > self.index_min_font_size:
            self.index_font_size -= 1
            self.update_index_display()
            self.refresh_book_index()
            self.status_bar.config(text=f"🔎 تم تصغير خط الفهرس إلى {self.index_font_size}")

    def update_index_display(self):
        if self.index_font_label:
            self.index_font_label.config(text=str(self.index_font_size))

    def refresh_book_index(self):
        if not hasattr(self, 'buttons_container') or self.buttons_container is None:
            return

        for btn in self.book_buttons:
            btn.destroy()
        self.book_buttons.clear()

        for i, (book_name, records) in enumerate(self.library_books.items()):
            btn = tk.Button(
                self.buttons_container,
                text=f"{book_name}\n({len(records):,})",
                font=("Arial", self.index_font_size),
                bg=self.secondary_color if i == 0 else "#f0f0f0",
                fg="white" if i == 0 else self.primary_color,
                relief=tk.RAISED,
                padx=10,
                pady=5,
                command=lambda idx=i: self.on_book_button_click(idx),
                wraplength=100,
                cursor="hand2",
                justify=tk.CENTER
            )
            btn.pack(side=tk.LEFT, padx=3, pady=3)
            self.book_buttons.append(btn)

        if hasattr(self, 'canvas'):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_book_button_click(self, index):
        books = list(self.library_books.keys())
        if index < len(books):
            for i, btn in enumerate(self.book_buttons):
                if i == index:
                    btn.config(bg=self.secondary_color, fg="white")
                else:
                    btn.config(bg="#f0f0f0", fg=self.primary_color)

            self.current_book_title = books[index]
            self.current_page_index = 0
            self.load_current_page()
            self.show_book_index(index)
            self.status_bar.config(text=f"✅ تم فتح كتاب: {self.current_book_title}")

    # =========================================================
    # نافذة فهرس الكتاب (مع إمكانية تكبير/تصغير الخط)
    # =========================================================

    def show_book_index(self, index):
        books = list(self.library_books.keys())
        if index >= len(books):
            return

        book_name = books[index]
        records = self.library_books[book_name]

        win = Toplevel(self.root)
        win.title(f"📑 فهرس كتاب: {book_name}")
        win.geometry("700x680")
        win.config(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()

        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (700 // 2)
        y = (win.winfo_screenheight() // 2) - (680 // 2)
        win.geometry(f"700x680+{x}+{y}")

        # العنوان
        tk.Label(
            win,
            text=f"📑 فهرس كتاب: {book_name}",
            font=("Arial", 14, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(pady=10)

        tk.Label(
            win,
            text=f"عدد الأحاديث: {len(records):,}",
            font=("Arial", 11),
            bg=self.bg_color,
            fg=self.secondary_color
        ).pack(pady=5)

        # ---- شريط التحكم بحجم الخط ----
        control_frame = tk.Frame(win, bg=self.bg_color)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            control_frame,
            text="📏 حجم الخط:",
            font=("Arial", 10, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(side=tk.RIGHT, padx=5)

        size_label = tk.Label(
            control_frame,
            text=str(self.listbox_font_size),
            font=("Arial", 10, "bold"),
            bg=self.bg_color,
            fg=self.secondary_color,
            width=4
        )
        size_label.pack(side=tk.RIGHT, padx=5)

        tk.Button(
            control_frame,
            text="🔎 تصغير",
            font=("Arial", 8, "bold"),
            bg="#e74c3c",
            fg="white",
            padx=8,
            pady=2,
            command=lambda: self.decrease_listbox_font(size_label, listbox)
        ).pack(side=tk.RIGHT, padx=2)

        tk.Button(
            control_frame,
            text="🔍 تكبير",
            font=("Arial", 8, "bold"),
            bg="#27ae60",
            fg="white",
            padx=8,
            pady=2,
            command=lambda: self.increase_listbox_font(size_label, listbox)
        ).pack(side=tk.RIGHT, padx=2)

        # ---- إطار القائمة ----
        frame = tk.Frame(win, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            frame,
            font=("Arial", self.listbox_font_size),
            bg="#ffffff",
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            selectbackground="#a8d8ea",
            selectforeground="black",
            justify=tk.CENTER
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # تعبئة القائمة
        for i, record in enumerate(records[:1000]):
            preview = record['arabic'][:35] + "..." if len(record['arabic']) > 35 else record['arabic']
            listbox.insert(tk.END, f"رقم {record['number']}: {preview}")

        if len(records) > 1000:
            listbox.insert(tk.END, f"... وعرض {len(records)-1000} حديث إضافي")

        # دوال الانتقال والتنقل
        def go_to_hadith():
            selection = listbox.curselection()
            if not selection:
                messagebox.showinfo("تنبيه", "⚠️ الرجاء اختيار حديث من القائمة")
                return
            idx = selection[0]
            if idx < len(records):
                self.current_book_title = book_name
                self.current_page_index = idx
                self.load_current_page()

                for i, btn in enumerate(self.book_buttons):
                    if i == index:
                        btn.config(bg=self.secondary_color, fg="white")
                    else:
                        btn.config(bg="#f0f0f0", fg=self.primary_color)

                win.destroy()
                self.status_bar.config(text=f"✅ تم الانتقال إلى الحديث رقم {records[idx]['number']} من كتاب {book_name}")

        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="📖 عرض الحديث",
            font=("Arial", 10, "bold"),
            bg=self.secondary_color,
            fg="white",
            padx=20,
            pady=5,
            command=go_to_hadith
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="❌ إغلاق",
            font=("Arial", 10, "bold"),
            bg="#7f8c8d",
            fg="white",
            padx=20,
            pady=5,
            command=win.destroy
        ).pack(side=tk.LEFT, padx=5)

        listbox.bind("<Double-Button-1>", lambda e: go_to_hadith())

        # تحديث حجم الخط في بداية العرض
        listbox.config(font=("Arial", self.listbox_font_size))

    # =========================================================
    # دوال تكبير وتصغير خط قائمة الفهرس
    # =========================================================

    def increase_listbox_font(self, size_label, listbox):
        if self.listbox_font_size < self.listbox_max_font_size:
            self.listbox_font_size += 1
            listbox.config(font=("Arial", self.listbox_font_size))
            size_label.config(text=str(self.listbox_font_size))

    def decrease_listbox_font(self, size_label, listbox):
        if self.listbox_font_size > self.listbox_min_font_size:
            self.listbox_font_size -= 1
            listbox.config(font=("Arial", self.listbox_font_size))
            size_label.config(text=str(self.listbox_font_size))

    # =========================================================
    # دوال تكبير وتصغير نص الحديث
    # =========================================================

    def increase_hadith_font(self):
        if self.hadith_font_size < self.hadith_max_font_size:
            self.hadith_font_size += 2
            self.update_hadith_font()
            self.status_bar.config(text=f"🔍 تم تكبير نص الحديث إلى {self.hadith_font_size}")

    def decrease_hadith_font(self):
        if self.hadith_font_size > self.hadith_min_font_size:
            self.hadith_font_size -= 2
            self.update_hadith_font()
            self.status_bar.config(text=f"🔎 تم تصغير نص الحديث إلى {self.hadith_font_size}")

    def update_hadith_font(self):
        self.text_area.configure(font=("Arial", self.hadith_font_size))
        if self.font_size_label:
            self.font_size_label.config(text=str(self.hadith_font_size))

    # =========================================================
    # تحميل وعرض الصفحات
    # =========================================================

    def format_hadith(self, record):
        parts = [
            f"📖 {record['book']}",
            f"🔢 رقم: {record['number']}"
        ]
        if record.get("narrator"):
            parts.append(f"👤 الراوي: {record['narrator']}")
        parts.extend(["", "🔹 النص:", record["arabic"]])
        # نضيف \u200F في بداية النص الكامل
        return "\u200F" + "\n".join(parts)

    def load_current_page(self):
        if not self.data_ready or not self.current_book_title:
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, "\u200F⏳ جاري فتح الكتب...")
            self.page_label.config(text="الكتب قيد الفتح")
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
            return

        records = self.library_books.get(self.current_book_title, [])
        if not records:
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, f"\u200F⚠️ لا يوجد أحاديث في كتاب {self.current_book_title}")
            self.page_label.config(text=f"{self.current_book_title} — لا يوجد أحاديث")
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
            return

        if self.current_page_index >= len(records):
            self.current_page_index = len(records) - 1
        if self.current_page_index < 0:
            self.current_page_index = 0

        record = records[self.current_page_index]

        self.page_label.config(
            text=(
                f"{self.current_book_title} — "
                f"رقم {record['number']} "
                f"({self.current_page_index + 1} من {len(records)})"
            )
        )

        self.text_area.delete("1.0", tk.END)
        self.text_area.insert(tk.END, self.format_hadith(record))
        self.highlight_text()

        self.prev_btn.config(state=tk.NORMAL if self.current_page_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_page_index < len(records) - 1 else tk.DISABLED)

    def next_page(self):
        records = self.library_books.get(self.current_book_title, [])
        if self.current_page_index < len(records) - 1:
            self.current_page_index += 1
            self.load_current_page()

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.load_current_page()

    # =========================================================
    # البحث والتظليل
    # =========================================================

    def highlight_text(self, event=None):
        if self.text_area is None:
            return

        query = self.search_entry.get().strip()
        self.text_area.tag_remove("highlight", "1.0", tk.END)

        if not query or query == "اكتب كلمة للبحث...":
            return

        start = "1.0"
        while True:
            start = self.text_area.search(query, start, stopindex=tk.END, nocase=True)
            if not start:
                break
            end = f"{start}+{len(query)}c"
            self.text_area.tag_add("highlight", start, end)
            start = end

    def clear_search_box_and_highlight(self):
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "اكتب كلمة للبحث...")
        self.search_entry.selection_clear()
        self.search_entry.icursor(0)

        if self.text_area is not None:
            self.text_area.tag_remove("highlight", "1.0", tk.END)

        self.load_current_page()
        self.status_bar.config(text="🗑 تم مسح البحث وإزالة التظليل")

    def copy_search_text(self):
        text = self.search_entry.get().strip()
        if text and text != "اكتب كلمة للبحث...":
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_bar.config(text="✅ تم نسخ نص البحث")
        else:
            self.status_bar.config(text="❌ لا يوجد نص للنسخ")

    def paste_search_text(self):
        try:
            text = self.root.clipboard_get()
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, text)
            self.highlight_text()
            self.status_bar.config(text="✅ تم لصق نص البحث")
        except Exception:
            self.status_bar.config(text="❌ الحافظة فارغة")

    def copy_hadith_text(self):
        try:
            selected = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
                self.status_bar.config(text="✅ تم نسخ النص المحدد")
                return
        except tk.TclError:
            pass

        text = self.text_area.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_bar.config(text="✅ تم نسخ الحديث كاملاً")

    # =========================================================
    # البحث العام
    # =========================================================

    def search_all_books(self):
        raw_query = self.search_entry.get().strip()
        if not raw_query or raw_query == "اكتب كلمة للبحث...":
            messagebox.showwarning("تنبيه", "أدخل كلمة أو رقمًا للبحث")
            return

        if not self.data_ready:
            messagebox.showinfo("قاعدة البيانات", "⏳ لم تكتمل قراءة قاعدة البيانات.")
            return

        cleaned = self.clean_pasted_query(raw_query)
        requested_number = self.extract_number_from_query(cleaned)
        requested_book = self.extract_book_from_query(cleaned)
        normalized_query = self.normalize_arabic(cleaned)

        just_number = cleaned.translate(self.ARABIC_DIGITS).strip().isdigit()

        results = []

        # البحث حسب الرقم
        if just_number:
            number = int(cleaned.translate(self.ARABIC_DIGITS))
            results = [r for r in self.hadith_records if r["number"] == number]

        elif requested_number is not None:
            for rec in self.hadith_records:
                if rec["number"] != requested_number:
                    continue
                if requested_book and rec["book"] != requested_book:
                    continue
                results.append(rec)

        # البحث النصي
        if not results:
            words = re.findall(r"[\u0600-\u06FF\w]+", normalized_query)
            stop_words = {
                "صحيح", "سنن", "جامع", "كتاب", "رقم", "الحديث",
                "الراوي", "نص", "حديث", "عن", "قال", "قالوا",
                "من", "على", "إلى", "في", "و", "ف", "ب", "ل", "ك", "ما"
            }
            words = [w for w in words if len(w) >= 3 and w not in stop_words]

            if words:
                for rec in self.hadith_records:
                    search_text = " ".join([
                        rec.get("arabic", ""),
                        rec.get("book", ""),
                        rec.get("narrator", "")
                    ])
                    search_text_norm = self.normalize_arabic(search_text)
                    if any(word in search_text_norm for word in words):
                        results.append(rec)
            else:
                for rec in self.hadith_records:
                    search_text = " ".join([
                        rec.get("arabic", ""),
                        rec.get("book", ""),
                        rec.get("narrator", "")
                    ])
                    if normalized_query in self.normalize_arabic(search_text):
                        results.append(rec)

        # إزالة التكرارات
        unique = []
        seen = set()
        for rec in results:
            key = (rec["book"], rec["number"])
            if key not in seen:
                seen.add(key)
                unique.append(rec)

        if not unique:
            messagebox.showinfo(
                "نتائج البحث",
                f"❌ لم يتم العثور على نتائج للبحث عن:\n{raw_query}"
            )
            return

        self.show_hadith_results(unique[:500], f"🔍 نتائج البحث — {len(unique):,} نتيجة")

        if len(unique) > 500:
            self.status_bar.config(text=f"ℹ️ عُرضت أول 500 نتيجة من أصل {len(unique):,}")

    def show_hadith_results(self, results, title):
        win = Toplevel(self.root)
        win.title(title)
        win.geometry("900x680")
        win.config(bg=self.bg_color)

        tk.Label(
            win,
            text=title,
            font=("Arial", 14, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(pady=10)

        # إنشاء Text بدون justify
        text = tk.Text(
            win,
            font=("Arial", self.hadith_font_size),
            wrap=tk.WORD,
            bg="#ffffff",
            padx=12,
            pady=12
        )

        text.tag_configure(
            "book_title",
            foreground=self.primary_color,
            font=("Arial", self.hadith_font_size, "bold")
        )

        scrollbar = tk.Scrollbar(win, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for rec in results:
            text.insert(
                tk.END,
                f"\n📖 {rec['book']} — رقم {rec['number']}\n",
                "book_title"
            )

            if rec.get("narrator"):
                text.insert(tk.END, f"👤 الراوي: {rec['narrator']}\n")

            text.insert(tk.END, f"\n{rec['arabic']}\n")
            text.insert(tk.END, "\n" + "─" * 70 + "\n")

        text.config(state=tk.DISABLED)

        tk.Button(
            win,
            text="❌ إغلاق",
            font=("Arial", 10, "bold"),
            bg=self.primary_color,
            fg="white",
            command=win.destroy
        ).pack(pady=10)

    # =========================================================
    # دوال أخرى (ترجمة الراوي، بحث على الويب، إلخ)
    # =========================================================

    def search_by_hadith_number(self):
        if not self.data_ready:
            messagebox.showinfo("قاعدة البيانات", "⏳ لم تكتمل قراءة قاعدة البيانات.")
            return

        win = Toplevel(self.root)
        win.title("🔢 البحث حسب رقم الحديث")
        win.geometry("460x240")
        win.config(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text="🔢 أدخل رقم الحديث",
            font=("Arial", 15, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(pady=15)

        entry = tk.Entry(win, font=("Arial", 14), justify="center", width=18)
        entry.pack(pady=5)
        entry.focus_set()

        def do_search():
            raw = entry.get().strip().translate(self.ARABIC_DIGITS)
            if not raw.isdigit():
                messagebox.showwarning("تنبيه", "⚠️ أدخل رقم الحديث بالأرقام فقط")
                return

            number = int(raw)
            results = [r for r in self.hadith_records if r["number"] == number]
            win.destroy()

            if not results:
                messagebox.showinfo(
                    "نتيجة البحث",
                    f"❌ لم يتم العثور على الحديث رقم {number}."
                )
                return

            self.show_hadith_results(results, f"🔢 الحديث رقم {number}")

        tk.Button(
            win,
            text="🔍 بحث",
            font=("Arial", 11, "bold"),
            bg=self.secondary_color,
            fg="white",
            padx=20,
            pady=5,
            command=do_search
        ).pack(pady=12)

        entry.bind("<Return>", lambda e: do_search())

        tk.Button(
            win,
            text="❌ إلغاء",
            font=("Arial", 10),
            bg="#7f8c8d",
            fg="white",
            command=win.destroy
        ).pack()

    def search_narrator(self):
        name = self.search_entry.get().strip()
        if not name or name == "اكتب كلمة للبحث...":
            messagebox.showwarning("تنبيه", "⚠️ أدخل اسم الراوي")
            return
        self.open_biography_window(name, "راوي")

    def search_muhaddith(self):
        name = self.search_entry.get().strip()
        if not name or name == "اكتب كلمة للبحث...":
            messagebox.showwarning("تنبيه", "⚠️ أدخل اسم المحدث")
            return
        self.open_biography_window(name, "محدث")

    def open_biography_window(self, name, typ):
        encoded = urllib.parse.quote(name)
        win = Toplevel(self.root)
        win.title(f"📚 ترجمة ال{typ}: {name}")
        win.geometry("520x420")
        win.config(bg=self.bg_color)

        tk.Label(
            win,
            text=f"📚 ترجمة ال{typ}: {name}",
            font=("Arial", 14, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(pady=15)

        sources = (
            [
                ("📖 سير أعلام النبلاء", f"https://www.google.com/search?q={encoded}+سير+أعلام+النبلاء"),
                ("📖 تهذيب الكمال", f"https://www.google.com/search?q={encoded}+تهذيب+الكمال"),
                ("📖 معرفة الثقات", f"https://www.google.com/search?q={encoded}+معرفة+الثقات"),
                ("📖 الكاشف", f"https://www.google.com/search?q={encoded}+الكاشف+في+معرفة+الرواة")
            ] if typ == "راوي" else [
                ("📖 طبقات الحفاظ", f"https://www.google.com/search?q={encoded}+طبقات+الحفاظ"),
                ("📖 تذكرة الحفاظ", f"https://www.google.com/search?q={encoded}+تذكرة+الحفاظ"),
                ("📖 شذرات الذهب", f"https://www.google.com/search?q={encoded}+شذرات+الذهب"),
                ("📖 العبر", f"https://www.google.com/search?q={encoded}+العبر+في+خبر+من+غبر")
            ]
        )

        for label, url in sources:
            tk.Button(
                win,
                text=label,
                font=("Arial", 10),
                bg=self.secondary_color,
                fg="white",
                command=lambda u=url: webbrowser.open(u)
            ).pack(pady=4, padx=30, fill=tk.X)

        tk.Button(
            win,
            text="🌐 بحث في ويكيبيديا",
            font=("Arial", 10),
            bg="#1d3557",
            fg="white",
            command=lambda: webbrowser.open(f"https://ar.wikipedia.org/wiki/{encoded}")
        ).pack(pady=5, padx=30, fill=tk.X)

        tk.Button(
            win,
            text="❌ إغلاق",
            font=("Arial", 10, "bold"),
            bg=self.primary_color,
            fg="white",
            command=win.destroy
        ).pack(pady=15)

    def search_on_web(self):
        query = self.search_entry.get().strip()
        if not query or query == "اكتب كلمة للبحث...":
            messagebox.showwarning("تنبيه", "أدخل كلمة للبحث على الإنترنت")
            return
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query))

    # =========================================================
    # دوال أخرى (مشاركة، سطح المكتب، عن البرنامج)
    # =========================================================

    def share_app(self):
        info = """🕌 الموسوعة الإسلامية الشاملة

📖 22 كتابًا في الحديث الشريف وعلومه
🔍 البحث العام
🔢 البحث حسب رقم الحديث
🕌 مواقيت الصلاة
📝 دفتر الملاحظات
🗑 مسح البحث وإزالة التظليل

👨‍💻 المطور: حسان مارديني
📧 hassanmardinli@gmail.com
📞 00905060917640

جميع الحقوق محفوظة © 2026"""

        win = Toplevel(self.root)
        win.title("📤 مشاركة التطبيق")
        win.geometry("520x470")
        win.config(bg=self.bg_color)

        text = tk.Text(win, font=("Arial", 11), wrap=tk.WORD, bg="#ffffff")
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        text.insert(tk.END, info)
        text.config(state=tk.DISABLED)

        frame = tk.Frame(win, bg=self.bg_color)
        frame.pack(pady=8)

        def copy_info():
            self.root.clipboard_clear()
            self.root.clipboard_append(info)
            messagebox.showinfo("نجاح", "✅ تم نسخ معلومات التطبيق")

        def share_whatsapp():
            webbrowser.open("https://wa.me/?text=" + urllib.parse.quote(info))

        def share_email():
            webbrowser.open(
                "mailto:?subject=" + urllib.parse.quote("الموسوعة الإسلامية الشاملة") +
                "&body=" + urllib.parse.quote(info)
            )

        tk.Button(frame, text="📋 نسخ", bg="#2980b9", fg="white", command=copy_info).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="💬 واتساب", bg="#25D366", fg="white", command=share_whatsapp).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="📧 بريد", bg="#D44638", fg="white", command=share_email).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="❌ إغلاق", bg=self.primary_color, fg="white", command=win.destroy).pack(side=tk.LEFT, padx=5)

    def create_desktop_shortcut(self):
        try:
            desktop = Path.home() / "Desktop"
            desktop.mkdir(exist_ok=True)
            bat_path = desktop / "الموسوعة_الإسلامية.bat"
            script_name = Path(__file__).name

            bat_path.write_text(
                '@echo off\n'
                'cd /d "%~dp0"\n'
                f'py "{script_name}"\n'
                'if errorlevel 1 python "{script_name}"\n'
                'if errorlevel 1 pause\n',
                encoding="utf-8"
            )

            messagebox.showinfo("نجاح", f"✅ تم إنشاء الاختصار على سطح المكتب:\n{bat_path}")

        except Exception as exc:
            messagebox.showerror("خطأ", f"❌ حدث خطأ: {exc}")

    def show_about_dialog(self):
        win = Toplevel(self.root)
        win.title("عن البرنامج")
        win.geometry("520x540")
        win.config(bg=self.bg_color)

        tk.Label(
            win,
            text="🕌 الموسوعة الإسلامية الشاملة",
            font=("Arial", 18, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(pady=15)

        info = """📖 برنامج إسلامي شامل

✅ 22 كتابًا (17 أساسي + 5 إضافي)
✅ البحث العام في الكتب
✅ البحث حسب رقم الحديث
✅ تكبير وتصغير نص الحديث
✅ تكبير وتصغير خط الفهرس
✅ تظليل نتائج البحث
✅ نسخ الحديث
✅ مواقيت الصلاة
✅ دفتر الملاحظات

─────────────────────
👨‍💻 المطور: حسان مارديني
📧 hassanmardinli@gmail.com
📞 00905060917640
─────────────────────

جميع الحقوق محفوظة © 2026"""

        text = tk.Text(win, font=("Arial", 11), wrap=tk.WORD, bg="#ffffff")
        text.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        text.insert(tk.END, info)
        text.config(state=tk.DISABLED)

        tk.Button(
            win,
            text="❌ إغلاق",
            font=("Arial", 10, "bold"),
            bg=self.primary_color,
            fg="white",
            command=win.destroy
        ).pack(pady=10)

    # =========================================================
    # قسم الصلاة
    # =========================================================

    def build_prayer_section(self):
        self.prayer_frame = tk.Frame(self.container, bg=self.bg_color)

        tk.Label(
            self.prayer_frame,
            text="🕌 مواقيت الصلاة",
            font=("Arial", 18, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(pady=(15, 8))

        location_frame = tk.Frame(self.prayer_frame, bg=self.bg_color)
        location_frame.pack(pady=5)

        tk.Label(
            location_frame,
            text="📍 المدينة والدولة:",
            font=("Arial", 11, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(side=tk.RIGHT, padx=5)

        self.prayer_city_entry = tk.Entry(
            location_frame,
            font=("Arial", 11),
            width=30,
            justify="center"
        )
        self.prayer_city_entry.pack(side=tk.RIGHT, padx=5)
        self.prayer_city_entry.insert(0, "Istanbul, Turkey")

        tk.Button(
            location_frame,
            text="🔄 جلب المواقيت",
            font=("Arial", 10, "bold"),
            bg=self.secondary_color,
            fg="white",
            padx=12,
            pady=3,
            command=self.load_prayer_times
        ).pack(side=tk.RIGHT, padx=5)

        tk.Label(
            self.prayer_frame,
            text="يتم جلب المواقيت عند طلبك فقط.",
            font=("Arial", 10),
            bg=self.bg_color,
            fg="#555555"
        ).pack(pady=5)

        self.prayer_date_label = tk.Label(
            self.prayer_frame,
            text="",
            font=("Arial", 11, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        )
        self.prayer_date_label.pack(pady=5)

        self.prayer_times_frame = tk.Frame(self.prayer_frame, bg=self.bg_color)
        self.prayer_times_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        self.prayer_status_label = tk.Label(
            self.prayer_frame,
            text="أدخل المدينة ثم اضغط «جلب المواقيت».",
            font=("Arial", 10),
            bg=self.bg_color,
            fg="#555555"
        )
        self.prayer_status_label.pack(pady=5)

        self.prayer_city_entry.bind("<Return>", lambda e: self.load_prayer_times())

    def load_prayer_times(self):
        city = self.prayer_city_entry.get().strip()
        if not city:
            messagebox.showwarning(
                "تنبيه",
                "⚠️ اكتب اسم المدينة والدولة، مثل: Istanbul, Turkey"
            )
            return

        self.prayer_status_label.config(text="⏳ جارٍ جلب مواقيت الصلاة...")
        threading.Thread(target=self.fetch_prayer_times, args=(city,), daemon=True).start()

    def fetch_prayer_times(self, city):
        try:
            date_str = datetime.now().strftime("%d-%m-%Y")
            url = (
                "https://api.aladhan.com/v1/timingsByAddress/"
                f"{date_str}?address={urllib.parse.quote(city)}&method=13"
            )

            request = Request(url, headers={"User-Agent": "Islamic Encyclopedia"})

            with urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))

            if data.get("code") != 200 or not data.get("data"):
                raise RuntimeError("لم يتم العثور على مواقيت لهذه المدينة.")

            payload = data["data"]

            self.root.after(
                0,
                lambda: self.display_prayer_times(
                    city,
                    payload.get("timings", {}),
                    payload.get("date", {}).get("gregorian", {}),
                    payload.get("date", {}).get("hijri", {})
                )
            )

        except Exception as exc:
            msg = str(exc)
            self.root.after(
                0,
                lambda m=msg: self.prayer_status_label.config(text=f"❌ تعذر جلب المواقيت: {m}")
            )

    def display_prayer_times(self, city, timings, gregorian, hijri):
        for widget in self.prayer_times_frame.winfo_children():
            widget.destroy()

        self.prayer_date_label.config(
            text=(
                f"📍 {city}   |   "
                f"📅 {gregorian.get('day', '')}/"
                f"{gregorian.get('month', {}).get('number', '')}/"
                f"{gregorian.get('year', '')}"
            )
        )

        prayer_names = [
            ("Fajr", "🌙 الفجر"),
            ("Sunrise", "🌅 الشروق"),
            ("Dhuhr", "☀️ الظهر"),
            ("Asr", "🌤️ العصر"),
            ("Maghrib", "🌇 المغرب"),
            ("Isha", "🌙 العشاء")
        ]

        for index, (key, label) in enumerate(prayer_names):
            card = tk.Frame(
                self.prayer_times_frame,
                bg="#ffffff",
                bd=1,
                relief=tk.RIDGE
            )

            card.grid(row=index // 3, column=index % 3, padx=8, pady=8, sticky="nsew")
            self.prayer_times_frame.grid_columnconfigure(index % 3, weight=1)
            self.prayer_times_frame.grid_rowconfigure(index // 3, weight=1)

            tk.Label(
                card,
                text=label,
                font=("Arial", 12, "bold"),
                bg="#ffffff",
                fg=self.primary_color
            ).pack(pady=(12, 5))

            tk.Label(
                card,
                text=timings.get(key, "--:--"),
                font=("Arial", 20, "bold"),
                bg="#ffffff",
                fg=self.secondary_color
            ).pack(pady=(2, 12))

        hijri_month = hijri.get("month", {}) if isinstance(hijri, dict) else {}
        hijri_text = (
            f"🕌 التاريخ الهجري: {hijri.get('day', '')} "
            f"{hijri_month.get('ar', '')} {hijri.get('year', '')}"
            if hijri else ""
        )

        self.prayer_status_label.config(text=f"✅ تم تحديث مواقيت اليوم — {hijri_text}")

    # =========================================================
    # قسم الملاحظات
    # =========================================================

    def build_notes_section(self):
        self.notes_frame = tk.Frame(self.container, bg=self.bg_color)

        tk.Label(
            self.notes_frame,
            text="📝 دفتر الملاحظات",
            font=("Arial", 14, "bold"),
            bg=self.bg_color,
            fg=self.primary_color
        ).pack(pady=10)

        notes_control_frame = tk.Frame(self.notes_frame, bg=self.bg_color)
        notes_control_frame.pack(pady=5)

        tk.Button(
            notes_control_frame,
            text="📋 نسخ",
            font=("Arial", 10, "bold"),
            bg="#2980b9",
            fg="white",
            padx=10,
            command=self.copy_notes_text
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            notes_control_frame,
            text="📋 لصق",
            font=("Arial", 10, "bold"),
            bg="#27ae60",
            fg="white",
            padx=10,
            command=self.paste_notes_text
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            notes_control_frame,
            text="🗑 إلغاء التحديد",
            font=("Arial", 10, "bold"),
            bg="#7f8c8d",
            fg="white",
            padx=10,
            command=self.clear_notes_selection
        ).pack(side=tk.LEFT, padx=5)

        notes_text_frame = tk.Frame(self.notes_frame, bg=self.bg_color)
        notes_text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(notes_text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.notes_text = tk.Text(
            notes_text_frame,
            font=("Arial", 12),
            wrap=tk.WORD,
            bg="#ffffff",
            yscrollcommand=scrollbar.set,
            selectbackground="#a8d8ea",
            selectforeground="black"
        )

        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.notes_text.yview)
        self.notes_text.insert("1.0", "")

    def clear_notes_selection(self):
        try:
            self.notes_text.tag_remove("sel", "1.0", tk.END)
            self.status_bar.config(text="🗑 تم إلغاء التحديد في الملاحظات")
        except Exception as e:
            self.status_bar.config(text=f"⚠️ {str(e)}")

    def copy_notes_text(self):
        try:
            selected = self.notes_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
                self.status_bar.config(text="✅ تم نسخ النص المحدد من الملاحظات")
                return
        except tk.TclError:
            pass

        text = self.notes_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_bar.config(text="✅ تم نسخ الملاحظات بالكامل")

    def paste_notes_text(self):
        try:
            self.notes_text.insert(tk.INSERT, self.root.clipboard_get())
            self.status_bar.config(text="✅ تم لصق الملاحظات")
        except Exception:
            self.status_bar.config(text="❌ الحافظة فارغة")


if __name__ == "__main__":
    root = tk.Tk()
    app = CompleteHadithApp(root)
    root.mainloop()