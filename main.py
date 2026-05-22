"""
FTP Contact Manager — Arabic Edition (Syntax Fixed)
تم مراجعة الكود بالكامل لضمان خلوه من أخطاء الـ Syntax
"""
import io
import csv
import json
import os
import re
import threading
import sys
from functools import lru_cache
from ftplib import FTP

# ══════════════════════════════════════════════════════════════════
# 1. Arabic Text Processing
# ══════════════════════════════════════════════════════════════════
try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi
    _ARABIC_OK = True
except ImportError:
    _ARABIC_OK = False
    print("[WARNING] arabic_reshaper or python-bidi not found!")

@lru_cache(maxsize=4096)
def ar(text):
    """تحويل النص العربي للصورة البصرية الصحيحة"""
    if not text or not _ARABIC_OK:
        return text
    try:
        return _bidi(arabic_reshaper.reshape(text))
    except Exception:
        return text

def _ar_in_kv(kv_string):
    """معالجة النصوص داخل ملف الـ KV"""
    def _replace(match):
        content = match.group(1)
        # فحص صحيح لمدى اليونيكود العربي
        if any('\u0600' <= c <= '\u06FF' for c in content):
            return '"{}"'.format(ar(content))
        return match.group(0)
    # Regex يطابق النصوص بين علامات التنصيص المزدوجة
    return re.sub(r'"([^"\n]*)"', _replace, kv_string)

# ══════════════════════════════════════════════════════════════════
# 2. Font Registration
# ══════════════════════════════════════════════════════════════════
from kivy.core.text import LabelBase
def _get_font_path(font_name):
    if os.path.exists(font_name):
        return font_name
    local_path = os.path.join(os.path.dirname(__file__), font_name)
    if os.path.exists(local_path):
        return local_path
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, font_name)
    return None

_AMIRI_PATH = _get_font_path("Amiri-Regular.ttf")

if _AMIRI_PATH:
    try:
        LabelBase.register(
            name='ArabicFont', 
            fn_regular=_AMIRI_PATH,
            fn_bold=_AMIRI_PATH
        )
        print("[INFO] Font registered: {}".format(_AMIRI_PATH))
    except Exception as e:
        print("[ERROR] Font registration failed: {}".format(e))
else:
    print("[ERROR] Amiri-Regular.ttf NOT FOUND!")

# ══════════════════════════════════════════════════════════════════
# 3. Imports
# ══════════════════════════════════════════════════════════════════
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import TwoLineAvatarIconListItem, IconRightWidget
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.chip import MDChip

# ══════════════════════════════════════════════════════════════════
# Screens & Constants
# ══════════════════════════════════════════════════════════════════
class HomeScreen(Screen): 
    pass
class AddScreen(Screen): 
    pass

class SearchScreen(Screen): 
    pass

class SettingsScreen(Screen): 
    pass

class FieldsScreen(Screen): 
    pass

class EditScreen(Screen): 
    pass

DEFAULT_FTP = {
    "host": "mediarouter", 
    "port": 21, 
    "user": "mmk",
    "password": "4d6F6174617@",
    "directory": "/Kingston-09511F45_usb1_1", 
    "filename": "moja.csv",
}

CONFIG_FILE = "ftp_config.json"
FIELDS_FILE = "fields_config.json"
LOCAL_CACHE = "local_cache.csv"
BUILTIN = ["الاسم", "السن", "رقم الهاتف"]

# ══════════════════════════════════════════════════════════════════
# KV Layout (تم إزالة جميع التعليقات الداخلية لضمان صحة الـ Syntax)
# ══════════════════════════════════════════════════════════════════
KV = """
ScreenManager:
    transition: SlideTransition()
    HomeScreen:
    AddScreen:
    SearchScreen:
    SettingsScreen:
    FieldsScreen:
    EditScreen:

<HomeScreen>:
    name: "home"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "مدير جهات الاتصال"
            font_name: "ArabicFont"
            right_action_items: [["magnify", lambda x: app.go_to("search")], ["cog", lambda x: app.go_to("settings")]]            left_action_items: [["format-list-bulleted", lambda x: app.go_to("fields")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_status_bar
            size_hint_y: None
            height: 0
            md_bg_color: 0.88, 0.17, 0.17, 1
            padding: dp(8), dp(4)
            MDLabel:
                id: ftp_status_label
                text: ""
                halign: "center"
                font_name: "ArabicFont"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
        MDScrollView:
            on_scroll_y: app.on_scroll_y(self, self.scroll_y)
            MDList:
                id: record_list
                padding: dp(8), dp(6)
                spacing: dp(6)
        MDFloatingActionButton:
            icon: "plus"
            pos_hint: {"right": 0.95, "bottom": 0.05}
            on_release: app.go_to("add")

<AddScreen>:
    name: "add"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إضافة جهة اتصال"
            font_name: "ArabicFont"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_add
            size_hint_y: None
            height: 0
            md_bg_color: 0.88, 0.17, 0.17, 1
            padding: dp(10), dp(4)
            MDLabel:
                text: "غير متصل بسيرفر FTP — لا يمكن الحفظ"
                halign: "center"
                font_name: "ArabicFont"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"                id: fields_box
                padding: dp(16), dp(16)
                spacing: dp(14)
                adaptive_height: True
        MDRaisedButton:
            text: "حفظ السجل"
            font_name: "ArabicFont"
            pos_hint: {"center_x": 0.5}
            size_hint_x: 0.85
            on_release: app.save_record()

<EditScreen>:
    name: "edit"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "تعديل البيانات"
            font_name: "ArabicFont"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_edit
            size_hint_y: None
            height: 0
            md_bg_color: 0.88, 0.17, 0.17, 1
            padding: dp(10), dp(4)
            MDLabel:
                text: "غير متصل بسيرفر FTP — لا يمكن الحفظ"
                halign: "center"
                font_name: "ArabicFont"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: edit_fields_box
                padding: dp(16), dp(16)
                spacing: dp(14)
                adaptive_height: True
        MDRaisedButton:
            text: "تحديث البيانات"
            font_name: "ArabicFont"
            pos_hint: {"center_x": 0.5}
            size_hint_x: 0.85
            on_release: app.update_record()

<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"        MDTopAppBar:
            title: "بحث"
            font_name: "ArabicFont"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(12), dp(10)
            spacing: dp(10)
            MDTextField:
                id: search_input
                hint_text: "ابحث بالاسم أو أي معلومة..."
                font_name: "ArabicFont"
                on_text: app.do_search(self.text)
        MDScrollView:
            MDList:
                id: search_list

<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إعدادات FTP"
            font_name: "ArabicFont"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(20), dp(16)
                spacing: dp(14)
                adaptive_height: True
                MDTextField:
                    id: ftp_host
                    hint_text: "Host (IP / Domain)"
                    font_name: "ArabicFont"
                MDTextField:
                    id: ftp_port
                    hint_text: "Port"
                    input_filter: "int"
                    font_name: "ArabicFont"
                MDTextField:
                    id: ftp_user
                    hint_text: "Username"
                    font_name: "ArabicFont"
                MDTextField:
                    id: ftp_password
                    hint_text: "Password"
                    password: True                    font_name: "ArabicFont"
                MDTextField:
                    id: ftp_directory
                    hint_text: "Remote Directory"
                    font_name: "ArabicFont"
                MDTextField:
                    id: ftp_filename
                    hint_text: "Filename (e.g. contacts.csv)"
                    font_name: "ArabicFont"
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(10)
                    MDRaisedButton:
                        text: "حفظ"
                        font_name: "ArabicFont"
                        on_release: app.save_settings()
                    MDFlatButton:
                        text: "اختبار الاتصال"
                        font_name: "ArabicFont"
                        on_release: app.test_connection()

<FieldsScreen>:
    name: "fields"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إدارة الحقول"
            font_name: "ArabicFont"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(10), dp(10)
            spacing: dp(10)
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(6)
                MDTextField:
                    id: new_field_input
                    hint_text: "اسم الحقل الجديد"
                    size_hint_x: 0.5
                    font_name: "ArabicFont"
                MDTextField:
                    id: field_type_input
                    hint_text: "text / checkbox / multiselect"
                    size_hint_x: 0.5
                    font_name: "ArabicFont"
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(6)                MDTextField:
                    id: field_options_input
                    hint_text: "خيارات: خيار1، خيار2"
                    font_name: "ArabicFont"
                MDIconButton:
                    icon: "plus"
                    on_release: app.add_field()
            MDScrollView:
                MDList:
                    id: fields_list
"""

# ══════════════════════════════════════════════════════════════════
# Helpers & Logic
# ══════════════════════════════════════════════════════════════════
def parse_multi(value):
    return [v for v in (value or "").split("|") if v]

def serialize_multi(selected):
    return "|".join(selected)

class FTPManager:
    def __init__(self, cfg):
        self.cfg = cfg

    def _connect(self):
        ftp = FTP()
        ftp.connect(self.cfg["host"], int(self.cfg["port"]), timeout=10)
        ftp.login(self.cfg["user"], self.cfg["password"])
        if self.cfg.get("directory"):
            ftp.cwd(self.cfg["directory"])
        return ftp

    def test(self):
        try:
            self._connect().quit()
            return True, ar("تم الاتصال بنجاح")
        except Exception as e:
            return False, ar("فشل الاتصال: {}".format(e))

    def read_csv(self):
        try:
            ftp = self._connect()
            buf = io.BytesIO()
            ftp.retrbinary("RETR {}".format(self.cfg['filename']), buf.write)
            ftp.quit()
            text = buf.getvalue().decode("utf-8")
            with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                f.write(text)
            return list(csv.DictReader(io.StringIO(text)))        except Exception as e:
            print("[FTP Read] {}".format(e))
            if os.path.exists(LOCAL_CACHE):
                with open(LOCAL_CACHE, encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            return []

    def write_csv(self, records, fieldnames):
        try:
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(records)
            data = buf.getvalue()
            with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                f.write(data)
            ftp = self._connect()
            ftp.storbinary("STOR {}".format(self.cfg['filename']),
                          io.BytesIO(data.encode("utf-8")))
            ftp.quit()
            return True
        except Exception as e:
            print("[FTP Write] {}".format(e))
            return False

class ContactApp(MDApp):
    def __init__(self, **kw):
        super(ContactApp, self).__init__(**kw)
        self.records = []
        self.fields = [
            {"name": "الاسم", "type": "text", "required": True},
            {"name": "السن", "type": "text", "required": False},
            {"name": "رقم الهاتف", "type": "text", "required": False},
        ]
        self.ftp_config = dict(DEFAULT_FTP)
        self._dirty = False
        self._editing_idx = -1
        self._add_widgets = {}
        self._edit_widgets = {}
        self._ftp_ok = False
        self._page_size = 20
        self._displayed = 0
        self._loading_more = False

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(_ar_in_kv(KV))

    def on_start(self):        self._load_config()
        self._load_fields()
        self._initial_load()
        Clock.schedule_interval(self._auto_sync, 15)
        Clock.schedule_interval(self._periodic_check, 10)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    self.ftp_config = json.load(f)
            except Exception:
                pass
        self.ftp = FTPManager(self.ftp_config)

    def _load_fields(self):
        if os.path.exists(FIELDS_FILE):
            try:
                with open(FIELDS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                if data and isinstance(data[0], str):
                    data = [{"name": n, "type": "text", "required": False} for n in data]
                self.fields = data
            except Exception:
                pass

    def _save_fields(self):
        with open(FIELDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fields, f, ensure_ascii=False, indent=2)

    def _field_names(self):
        return [fd["name"] for fd in self.fields]

    def _snack(self, text):
        msg = ar(text)
        def _show(dt):
            try:
                from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
                MDSnackbar(MDSnackbarText(text=msg),
                          y=dp(24), pos_hint={"center_x": .5},
                          size_hint_x=.92, duration=3).open()
            except (ImportError, TypeError):
                try:
                    from kivymd.uix.snackbar import Snackbar
                    s = Snackbar()
                    s.text = msg
                    s.open()
                except Exception:
                    self._dlg(ar("رسالة"), msg)
        Clock.schedule_once(_show, 0)
    def _dlg(self, title, text, buttons=None):
        if buttons is None:
            btn = MDFlatButton(text=ar("حسناً"), font_name="ArabicFont")
            d = MDDialog(title=ar(title), text=ar(text), buttons=[btn], font_name="ArabicFont")
            btn.bind(on_release=lambda x: d.dismiss())
        else:
            d = MDDialog(title=ar(title), text=ar(text), buttons=buttons, font_name="ArabicFont")
        d.open()
        return d

    def _periodic_check(self, dt):
        prev = self._ftp_ok
        def _bg():
            ok, _ = self.ftp.test()
            def _ui(dt2):
                self._ftp_ok = ok
                if prev and not ok:
                    self._snack("انقطع الاتصال بسيرفر FTP")
                self._update_bars()
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def _update_bars(self):
        try:
            bar = self.root.get_screen("home").ids.ftp_status_bar
            lbl = self.root.get_screen("home").ids.ftp_status_label
            bar.height = 0 if self._ftp_ok else dp(30)
            lbl.text = "" if self._ftp_ok else ar("غير متصل بسيرفر FTP")
        except Exception:
            pass
        h = dp(36) if not self._ftp_ok else 0
        for sn, bid in [("add", "ftp_warning_add"), ("edit", "ftp_warning_edit")]:
            try:
                self.root.get_screen(sn).ids[bid].height = h
            except Exception:
                pass

    def _require_ftp(self, cb):
        self._snack("جاري التحقق من الاتصال...")
        def _bg():
            ok, msg = self.ftp.test()
            def _ui(dt):
                self._ftp_ok = ok
                self._update_bars()
                if ok:
                    cb()
                else:
                    self._no_ftp_dlg(msg)
            Clock.schedule_once(_ui, 0)        threading.Thread(target=_bg, daemon=True).start()

    def _no_ftp_dlg(self, msg=""):
        btn_s = MDRaisedButton(text=ar("إعدادات FTP"), font_name="ArabicFont")
        btn_c = MDFlatButton(text=ar("إغلاق"), font_name="ArabicFont")
        d = self._dlg(
            ar("غير متصل بالسيرفر"),
            ar("لا يمكن حفظ البيانات.\nيجب الاتصال بسيرفر FTP أولاً.\n\n{}".format(msg)),
            [btn_s, btn_c])
        btn_s.bind(on_release=lambda x: (d.dismiss(), self.go_to("settings")))
        btn_c.bind(on_release=lambda x: d.dismiss())

    def go_to(self, name):
        self.root.transition = SlideTransition(
            direction="left" if name != "home" else "right")
        self.root.current = name
        if name == "settings": 
            self._load_settings_ui()
        elif name == "fields": 
            self._refresh_fields_ui()
        elif name == "add": 
            self._build_add_form()
            self._update_bars()
        elif name == "edit": 
            self._update_bars()
        elif name == "home": 
            self._displayed = 0
            self._refresh_list()

    def _initial_load(self):
        def _bg():
            ok, msg = self.ftp.test()
            recs = self.ftp.read_csv() if ok else []
            def _ui(dt):
                self._ftp_ok = ok
                self.records = recs
                self._displayed = 0
                self._refresh_list()
                self._update_bars()
                if not ok:
                    self._snack("تعذر الاتصال: {}".format(msg))
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def _auto_sync(self, dt):
        if self._dirty:
            return
        def _bg():
            recs = self.ftp.read_csv()
            if recs and recs != self.records:                self.records = recs
                Clock.schedule_once(lambda dt2: self._refresh_list(), 0)
        threading.Thread(target=_bg, daemon=True).start()

    def _refresh_list(self, append=False):
        lst = self.root.get_screen("home").ids.record_list
        if not append:
            lst.clear_widgets()
            self._displayed = 0
        if not self.records:
            if not append:
                lst.add_widget(MDLabel(
                    text=ar("لا توجد سجلات"),
                    halign="center", font_name="ArabicFont",
                    height=dp(70), size_hint_y=None))
            return
        start = self._displayed
        end = min(start + self._page_size, len(self.records))
        for i in range(start, end):
            lst.add_widget(self._make_item(i, self.records[i]))
        lst.add_widget(MDCard(height=dp(1), size_hint_y=None,
                             elevation=0, md_bg_color=[0,0,0,.08]))
        self._displayed = end
        self._loading_more = False

    def _make_item(self, i, rec):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True,
                         padding=[dp(14), dp(8)], spacing=dp(4))
        row = MDBoxLayout(adaptive_height=True, spacing=dp(8))

        info = MDBoxLayout(orientation="vertical", adaptive_height=True)
        name_val = rec.get("الاسم", "") or "بدون اسم"
        info.add_widget(MDLabel(
            text=ar(name_val),
            font_style="H6", font_name="ArabicFont", adaptive_height=True, halign="right"))

        parts = []
        if rec.get("السن"): 
            parts.append(ar("السن: {}".format(rec['السن'])))
        if rec.get("رقم الهاتف"): 
            parts.append(ar("الهاتف: {}".format(rec['رقم الهاتف'])))
        if parts:
            info.add_widget(MDLabel(
                text=" | ".join(parts),
                font_style="Caption", theme_text_color="Secondary",
                font_name="ArabicFont", adaptive_height=True, halign="right"))

        row.add_widget(info)

        btns = MDBoxLayout(adaptive_size=True, spacing=dp(2))        eb = MDIconButton(icon="pencil", theme_text_color="Primary")
        db = MDIconButton(icon="delete", theme_text_color="Error")
        eb.bind(on_release=lambda x, idx=i: self.go_to_edit(idx))
        db.bind(on_release=lambda x, idx=i: self._confirm_delete(idx))
        btns.add_widget(eb)
        btns.add_widget(db)
        row.add_widget(btns)
        box.add_widget(row)

        for fd in self.fields:
            if fd["type"] != "multiselect": 
                continue
            selected = parse_multi(rec.get(fd["name"], ""))
            if not selected: 
                continue
            chips_row = MDBoxLayout(adaptive_height=True,
                                   spacing=dp(4), padding=[0, dp(2)])
            chips_row.add_widget(MDLabel(
                text=ar('{}: '.format(fd["name"])),
                font_style="Caption", adaptive_size=True,
                font_name="ArabicFont", theme_text_color="Secondary"))
            for opt in selected:
                try:
                    chip = MDChip(text=ar(opt), font_name="ArabicFont")
                    chips_row.add_widget(chip)
                except Exception:
                    chips_row.add_widget(MDLabel(
                        text=ar("[{}]".format(opt)),
                        font_style="Caption", adaptive_size=True, font_name="ArabicFont"))
            box.add_widget(chips_row)
        return box

    def on_scroll_y(self, sv, val):
        if val < 0.1 and not self._loading_more and self._displayed < len(self.records):
            self._loading_more = True
            self._refresh_list(append=True)

    def _make_field_widget(self, fd, current=""):
        name = fd["name"]
        ftype = fd["type"]
        req = ar(" (مطلوب)") if fd.get("required") else ""
        if ftype == "text":
            tf = MDTextField(hint_text=ar(name) + req,
                           mode="rectangle", text=current or "",
                           font_name="ArabicFont", multiline=False)
            tf.field_type = "text"
            return tf
        if ftype == "checkbox":
            c = MDBoxLayout(adaptive_height=True, spacing=dp(10),
                           size_hint_y=None, height=dp(44))            cb = MDCheckbox(active=(current == "true"),
                           size_hint=(None, None), size=(dp(32), dp(32)))
            lbl = MDLabel(text=ar(name), adaptive_height=True, 
                         halign="right", font_name="ArabicFont")
            c.add_widget(cb)
            c.add_widget(lbl)
            c.checkbox = cb
            c.field_type = "checkbox"
            return c
        if ftype == "multiselect":
            c = MDBoxLayout(orientation="vertical", adaptive_height=True,
                           spacing=dp(6), padding=[0, dp(6)])
            c.add_widget(MDLabel(text=ar(name), font_style="Subtitle1",
                               adaptive_height=True, halign="right", font_name="ArabicFont"))
            selected = parse_multi(current)
            opts = fd.get("options", [])
            cb_map = {}
            row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
            for opt in opts:
                sub = MDBoxLayout(adaptive_size=True, spacing=dp(4))
                cb = MDCheckbox(active=(opt in selected),
                               size_hint=(None, None), size=(dp(28), dp(28)))
                sub.add_widget(cb)
                sub.add_widget(MDLabel(text=ar(opt), font_style="Caption",
                                     adaptive_size=True, font_name="ArabicFont"))
                row.add_widget(sub)
                cb_map[opt] = cb
            c.add_widget(row)
            c.cb_map = cb_map
            c.field_type = "multiselect"
            return c
        return None

    def _read_val(self, w):
        ft = getattr(w, "field_type", None)
        if ft == "text": 
            return w.text.strip()
        if ft == "checkbox": 
            return "true" if w.checkbox.active else "false"
        if ft == "multiselect": 
            return serialize_multi(
                [o for o, cb in w.cb_map.items() if cb.active])
        return ""

    def _build_add_form(self):
        box = self.root.get_screen("add").ids.fields_box
        for w in list(box.children):
            if not isinstance(w, MDRaisedButton):
                box.remove_widget(w)
        self._add_widgets = {}        for fd in reversed(self.fields):
            wid = self._make_field_widget(fd, "")
            if wid:
                self._add_widgets[fd["name"]] = wid
                box.add_widget(wid, index=len(box.children))

    def save_record(self):
        rec = {}
        for fd in self.fields:
            w = self._add_widgets.get(fd["name"])
            val = self._read_val(w) if w else ""
            if fd.get("required") and not val:
                self._snack('الحقل «{}» مطلوب'.format(fd["name"]))
                return
            rec[fd["name"]] = val
        def _do():
            self.records.insert(0, rec)
            self._dirty = True
            ok = self.ftp.write_csv(self.records, self._field_names())
            if ok:
                self._dirty = False
                Clock.schedule_once(lambda dt: self._snack("تمت الإضافة بنجاح"), 0)
                Clock.schedule_once(lambda dt: self.go_to("home"), 0)
            else:
                self.records.pop(0)
                self._dirty = False
                Clock.schedule_once(lambda dt: self._no_ftp_dlg("فشل رفع الملف"), 0)
        self._require_ftp(_do)

    def go_to_edit(self, idx):
        self._editing_idx = idx
        rec = self.records[idx]
        self.go_to("edit")
        box = self.root.get_screen("edit").ids.edit_fields_box
        for w in list(box.children):
            if not isinstance(w, MDRaisedButton):
                box.remove_widget(w)
        self._edit_widgets = {}
        for fd in reversed(self.fields):
            wid = self._make_field_widget(fd, rec.get(fd["name"], ""))
            if wid:
                self._edit_widgets[fd["name"]] = wid
                box.add_widget(wid, index=len(box.children))

    def update_record(self):
        if self._editing_idx == -1: 
            return
        old = dict(self.records[self._editing_idx])
        new_vals = {n: self._read_val(w) for n, w in self._edit_widgets.items()}
        def _do():            for k, v in new_vals.items():
                self.records[self._editing_idx][k] = v
            self._dirty = True
            ok = self.ftp.write_csv(self.records, self._field_names())
            if ok:
                self._dirty = False
                Clock.schedule_once(lambda dt: self._snack("تم التحديث بنجاح"), 0)
                Clock.schedule_once(lambda dt: self.go_to("home"), 0)
            else:
                self.records[self._editing_idx] = old
                self._dirty = False
                Clock.schedule_once(lambda dt: self._no_ftp_dlg("فشل رفع الملف"), 0)
        self._require_ftp(_do)

    def _confirm_delete(self, idx):
        btn_cancel = MDFlatButton(text=ar("إلغاء"), font_name="ArabicFont")
        btn_del = MDRaisedButton(text=ar("حذف"), md_bg_color="red", font_name="ArabicFont")
        d = self._dlg(ar("تأكيد الحذف"),
                     ar("هل أنت متأكد من حذف هذا السجل؟"),
                     [btn_cancel, btn_del])
        btn_cancel.bind(on_release=lambda x: d.dismiss())
        def _do(x):
            d.dismiss()
            def _bg():
                ok, msg = self.ftp.test()
                if not ok:
                    Clock.schedule_once(lambda dt: self._no_ftp_dlg(msg), 0)
                    return
                self.records.pop(idx)
                self._dirty = True
                self.ftp.write_csv(self.records, self._field_names())
                self._dirty = False
                Clock.schedule_once(lambda dt: (
                    self._snack("تم الحذف"), self._refresh_list()), 0)
            threading.Thread(target=_bg, daemon=True).start()
        btn_del.bind(on_release=_do)

    def do_search(self, query):
        lst = self.root.get_screen("search").ids.search_list
        lst.clear_widgets()
        if not query: 
            return
        q = query.lower()
        for rec in self.records:
            if not any(q in str(v).lower() for v in rec.values()): 
                continue
            parts = []
            if rec.get("السن"): 
                parts.append(ar("السن: {}".format(rec['السن'])))
            if rec.get("رقم الهاتف"):                 parts.append(ar("الهاتف: {}".format(rec['رقم الهاتف'])))
            lst.add_widget(TwoLineAvatarIconListItem(
                text=ar(rec.get("الاسم", "")),
                secondary_text=" | ".join(parts),
                font_name="ArabicFont"))

    def _refresh_fields_ui(self, *_):
        lst = self.root.get_screen("fields").ids.fields_list
        lst.clear_widgets()
        tl = {"text": ar("نصي"), "checkbox": ar("اختيار"),
              "multiselect": ar("قائمة متعددة")}
        for fd in self.fields:
            name = fd["name"]
            tp = fd.get("type", "text")
            opts = fd.get("options", [])
            sec = tl.get(tp, tp)
            if tp == "multiselect" and opts:
                sec += ' · {}'.format(ar("، ".join(opts[:3]))) + (" ..." if len(opts)>3 else "")
            if name in BUILTIN:
                sec += ' · {}'.format(ar("أساسي"))
            item = TwoLineAvatarIconListItem(
                text=ar(name), secondary_text=sec, font_name="ArabicFont")
            if name not in BUILTIN:
                btn = IconRightWidget(icon="delete")
                btn.bind(on_release=lambda x, n=name: self._remove_field(n))
                item.add_widget(btn)
            lst.add_widget(item)

    def add_field(self):
        ids = self.root.get_screen("fields").ids
        name = ids.new_field_input.text.strip()
        ftype = ids.field_type_input.text.strip().lower() or "text"
        opts_raw = ids.field_options_input.text.strip()
        if not name:
            self._snack("أدخل اسم الحقل")
            return
        if any(fd["name"] == name for fd in self.fields):
            self._snack("الحقل موجود بالفعل")
            return
        if ftype not in ("text", "checkbox", "multiselect"):
            self._snack("النوع: text أو checkbox أو multiselect")
            return
        opts = []
        if ftype == "multiselect":
            opts = [o.strip() for o in opts_raw.split(",") if o.strip()]
            if len(opts) < 2:
                self._snack("أضف خيارين على الأقل مفصولة بفاصلة")
                return
        fd = {"name": name, "type": ftype, "required": False}
        if opts:             fd["options"] = opts
        self.fields.append(fd)
        for r in self.records: 
            r.setdefault(name, "")
        self._save_fields()
        ids.new_field_input.text = ""
        ids.field_type_input.text = ""
        ids.field_options_input.text = ""
        self._refresh_fields_ui()

    def _remove_field(self, name):
        if name in BUILTIN: 
            return
        self.fields = [fd for fd in self.fields if fd["name"] != name]
        for r in self.records: 
            r.pop(name, None)
        self._save_fields()
        self._refresh_fields_ui()

    def _load_settings_ui(self):
        ids = self.root.get_screen("settings").ids
        for k in ["host","port","user","password","directory","filename"]:
            getattr(ids, "ftp_{}".format(k)).text = str(self.ftp_config.get(k, ""))

    def save_settings(self):
        ids = self.root.get_screen("settings").ids
        self.ftp_config = {k: getattr(ids, "ftp_{}".format(k)).text.strip()
                          for k in ["host","user","password","directory","filename"]}
        port_val = ids.ftp_port.text.strip()
        self.ftp_config["port"] = int(port_val) if port_val else 21
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.ftp_config, f, ensure_ascii=False, indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم حفظ الإعدادات")

    def test_connection(self):
        self._snack("جاري اختبار الاتصال...")
        def _bg():
            ok, msg = self.ftp.test()
            self._ftp_ok = ok
            Clock.schedule_once(lambda dt: self._snack(msg), 0)
            Clock.schedule_once(lambda dt: self._update_bars(), 0)
        threading.Thread(target=_bg, daemon=True).start()

if __name__ == "__main__":
    ContactApp().run()