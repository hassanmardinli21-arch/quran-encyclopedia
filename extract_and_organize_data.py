import zipfile
from pathlib import Path

# مسار المشروع الرئيسي
project_base = Path(r"F:\تطبيقات صنعي\الموسوعة_الإسلامية")
zip_path = project_base / "data" / "hadith-json-1.2.0.zip"
extract_to = project_base / "data" / "extracted_books"

print("="*60)
print("📦 بدء فك ومعالجة أرشيف بيانات الموسوعة")
print("="*60)

if zip_path.exists():
    print(f"📁 جاري فك الملف: {zip_path.name} ...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"✅ تم فك الأرشيف بنجاح في المسار:\n   {extract_to}")
        
        # استعراض بعض الملفات المستخرجة للتأكد
        extracted_files = list(extract_to.rglob("*.json"))
        print(f"📊 إجمالي ملفات الـ JSON المستخرجة: {len(extracted_files)} ملف.")
        print("💡 الآن أصبحت ملفات البيانات جاهزة للاستخدام في تطبيقك وموقعك!")
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء فك الملف المضغوط: {e}")
else:
    print(f"❌ ملف الـ ZIP غير موجود في المسار المحدد:\n   {zip_path}")

print("="*60)