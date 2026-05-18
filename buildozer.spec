[app]

# عنوان التطبيق كما يظهر على الجهاز
title = قوافل مرسال

# اسم الحزمة (أحرف إنجليزية صغيرة وأرقام فقط)
package.name = ftpconvoymanager

# نطاق الحزمة (عكسي)
package.domain = org.ftpconvoy

# مجلد الكود المصدري (نفس مجلد buildozer.spec)
source.dir = .

# الامتدادات التي سيتم تضمينها
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,csv,txt

# نقطة الدخول الرئيسية (يجب أن يكون اسمه main.py)
# الملف: main.py

# رقم الإصدار
version = 1.0

# المكتبات المطلوبة
# kivy: إطار العمل الرئيسي
# kivymd: مكتبة Material Design
# hostpython3: ضروري للبناء
requirements = python3,kivy==2.3.1,kivymd==1.2.0

# توجيه الشاشة
orientation = portrait

# وضع ملء الشاشة
fullscreen = 0

# أيقونة التطبيق (ضع ملف icon.png بجانب main.py لتخصيصها)
# icon.filename = %(source.dir)s/icon.png

# صورة الشاشة الترحيبية
# presplash.filename = %(source.dir)s/presplash.png

# لون خلفية شاشة الترحيب
presplash.color = #009688

# ─── إعدادات Android ──────────────────────────────────

[android]

# الصلاحيات المطلوبة
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# إصدار Android API المستهدف
android.api = 33

# أدنى إصدار Android مدعوم (Android 5.0)
android.minapi = 21

# إصدار NDK
android.ndk = 25b

# إصدار NDK API (يجب مطابقة minapi)
android.ndk_api = 21

# قبول تراخيص SDK تلقائياً
android.accept_sdk_license = True

# بنيات المعالج المدعومة (arm64 للأجهزة الحديثة + armeabi للقديمة)
android.archs = arm64-v8a, armeabi-v7a

# Bootstrap (sdl2 هو الافتراضي لـ Kivy)
p4a.bootstrap = sdl2

# فرع python-for-android
p4a.branch = master

# تمكين AndroidX
android.enable_androidx = True

# ─── إعدادات iOS (غير مستخدمة) ───────────────────────

[buildozer]

# مستوى تفاصيل السجل (2 = تفصيلي)
log_level = 2

# تحذير عند البناء كـ root
warn_on_root = 1
