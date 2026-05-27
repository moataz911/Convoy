[app]

title = تسجيل قوافل مرسال
package.name = ftpcontactmanager
package.domain = org.ftpcontacts

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,csv,txt,xml
source.include_patterns = Amiri-Regular.ttf,Cairo-Bold.ttf,network_security_config.xml

version = 1.0

requirements = python3,kivy==2.3.1,kivymd==1.2.0,arabic-reshaper,python-bidi

orientation = portrait
fullscreen = 0
presplash.color = #009688

[android]
android.add_assets = network_security_config.xml:res/xml/network_security_config.xml
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CHANGE_NETWORK_STATE,ACCESS_WIFI_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
p4a.bootstrap = sdl2
p4a.branch = master
android.enable_androidx = True

# السماح بـ FTP (cleartext) + network security config
android.extra_manifest_application_arguments = android:usesCleartextTraffic="true" android:networkSecurityConfig="@xml/network_security_config"

[buildozer]

log_level = 2
warn_on_root = 1
