
[app]

# عنوان التطبيق الذي سيظهر للمستخدم
title = تسجيل قوافل مرسال

# اسم الحزمة (package name) المستخدم في Android
package.name = ftpcontactmanager
package.domain = org.ftpcontacts

# دليل مصدر التطبيق (نفس الدليل الحالي)
source.dir = .

# امتدادات الملفات التي يجب تضمينها في الحزمة
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,csv,txt,xml

# أنماط الملفات المحددة التي يجب تضمينها (الخطوط وملف إعدادات الشبكة)
source.include_patterns = Amiri-Regular.ttf,Cairo-Bold.ttf,network_security_config.xml

# إصدار التطبيق
version = 1.0

# متطلبات Python والمكتبات (Kivy, KivyMD, arabic-reshaper, python-bidi)
requirements = python3,kivy==2.3.1,kivymd==1.2.0,arabic-reshaper,python-bidi

# اتجاه الشاشة الافتراضي
orientation = portrait
# تعطيل وضع ملء الشاشة
fullscreen = 0
# لون شاشة البداية (presplash)
presplash.color = #009688

[android]
# إضافة ملف network_security_config.xml إلى موارد Android
android.add_assets = network_security_config.xml:res/xml/network_security_config.xml

# أذونات Android المطلوبة:
# INTERNET: للوصول إلى الإنترنت وخادم FTP
# ACCESS_NETWORK_STATE: للوصول إلى معلومات حالة الشبكة
# CHANGE_NETWORK_STATE: لتغيير حالة اتصال الشبكة
# ACCESS_WIFI_STATE: للوصول إلى معلومات حالة Wi-Fi
# WRITE_EXTERNAL_STORAGE: للكتابة على وحدة التخزين الخارجية (لحفظ الملفات المحلية)
# READ_EXTERNAL_STORAGE: للقراءة من وحدة التخزين الخارجية (لقراءة الملفات المحلية)
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CHANGE_NETWORK_STATE,ACCESS_WIFI_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# مستوى API المستهدف لـ Android
android.api = 33
# الحد الأدنى لمستوى API المدعوم
android.minapi = 21
# إصدار NDK المستخدم
android.ndk = 25b
android.ndk_api = 21
# قبول ترخيص SDK تلقائيًا
android.accept_sdk_license = True
# معماريات المعالج المدعومة
android.archs = arm64-v8a, armeabi-v7a
# نوع bootstrap لـ Python for Android
p4a.bootstrap = sdl2
p4a.branch = master
# تمكين دعم AndroidX (مطلوب لـ KivyMD الحديثة)
android.enable_androidx = True

# السماح بحركة مرور النص الواضح (cleartext) لـ FTP
# وتحديد ملف إعدادات أمان الشبكة (network_security_config)
android.extra_manifest_application_arguments = android:usesCleartextTraffic="true" android:networkSecurityConfig="@xml/network_security_config"

[buildozer]

# مستوى تسجيل buildozer
log_level = 2
# التحذير عند التشغيل كـ root
warn_on_root = 1
