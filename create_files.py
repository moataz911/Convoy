# create_files.py
import os

buildozer_spec = """[app]
title = BBproject
package.name = bbproject
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1

requirements = python3,kivy==2.3.0,kivymd==1.2.0,arabic-reshaper,python-bidi,requests,chardet,urllib3,idna,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

p4a.bootstrap = sdl2
p4a.branch = master

android.add_assets = Cairo-Bold.ttf:fonts/Cairo-Bold.ttf
android.debug_artifact = apk
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
"""

# ملاحظة: لتجنب تعقيد الترميز، أنصح بنسخ كود main.py من الرد السابق وحفظه يدوياً.
# لكن إذا أردت إنشاءه تلقائياً، استخدم هذا الأمر البديل في الطرفية:
# curl -L -o main.py "https://raw.githubusercontent.com/moataz911/Convoy/main/main.py"
# ثم عدل الأجزاء التي ذكرتها سابقاً.

with open("buildozer.spec", "w", encoding="utf-8") as f:
    f.write(buildozer_spec)
print("✅ تم إنشاء buildozer.spec بنجاح!")
print("💡 انسخ كود main.py من الرد السابق واحفظه باسم main.py في نفس المجلد.")
