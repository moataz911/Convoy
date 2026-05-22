[app]
title = مدير قوافل مرسال
package.name = ftpconvoy
package.domain = org.ftpconvoy

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,csv,txt
source.include_patterns = assets/*.ttf,*.ttf,Amiri-Regular.ttf,Cairo-Bold.ttf

version = 1.0

requirements = python3,kivy,kivymd,arabic-reshaper,python-bidi

orientation = portrait
fullscreen = 0
presplash.color = #009688

[android]
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a
p4a.bootstrap = sdl2
p4a.branch = master
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1