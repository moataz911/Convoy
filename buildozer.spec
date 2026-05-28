[app]
title = Marsal Convoys
package.name = marsalconvoys
package.domain = com.marsal
source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.exclude_exts = spec,pyc,pyo
source.exclude_dirs = tests,bin,venv,.buildozer,__pycache__,.git
version = 1.0
orientation = portrait
android.allow_backup = True
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,materialyoucolor,exceptiongroup,requests

android.api = 34
android.minapi = 24
android.sdk = 34
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

android.extra_manifest_xml = \
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="28"/>

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
