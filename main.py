# -*- coding: utf-8 -*-
"""
FTP Contact Manager — Arabic Edition
تسجيل قوافل مرسال — نظام إدارة السجلات عبر FTP
متوافق مع KivyMD 1.2.0 + Kivy 2.3.1
"""
import io, csv, json, os, re, threading, sys
from functools import lru_cache
from ftplib import FTP

# ══════════════════════════════════════════════════════════════════
#  UTF-8 enforcement — يجب أن يكون قبل أي عملية I/O
# ══════════════════════════════════════════════════════════════════
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════
#  Arabic text support — inline + optional external packages
#  يعمل 100% بدون packages خارجية (inline fallback مدمج في الكود)
# ══════════════════════════════════════════════════════════════════
try:
    import arabic_reshaper as _ext_reshaper
    from bidi.algorithm import get_display as _ext_bidi
    _ARABIC_OK = True
except ImportError:
    _ext_reshaper = None
    _ext_bidi     = None
    _ARABIC_OK    = False

# ── Inline Arabic letter forms: (isolated, final, initial, medial) ──
_AR_FORMS = {
    '\u0621': ('\uFE80', None,    None,    None   ),
    '\u0622': ('\uFE81', '\uFE82', None,    None   ),
    '\u0623': ('\uFE83', '\uFE84', None,    None   ),
    '\u0624': ('\uFE85', '\uFE86', None,    None   ),
    '\u0625': ('\uFE87', '\uFE88', None,    None   ),
    '\u0626': ('\uFE89', '\uFE8A', '\uFE8B', '\uFE8C'),
    '\u0627': ('\uFE8D', '\uFE8E', None,    None   ),
    '\u0628': ('\uFE8F', '\uFE90', '\uFE91', '\uFE92'),
    '\u0629': ('\uFE93', '\uFE94', None,    None   ),
    '\u062A': ('\uFE95', '\uFE96', '\uFE97', '\uFE98'),
    '\u062B': ('\uFE99', '\uFE9A', '\uFE9B', '\uFE9C'),
    '\u062C': ('\uFE9D', '\uFE9E', '\uFE9F', '\uFEA0'),
    '\u062D': ('\uFEA1', '\uFEA2', '\uFEA3', '\uFEA4'),
    '\u062E': ('\uFEA5', '\uFEA6', '\uFEA7', '\uFEA8'),
    '\u062F': ('\uFEA9', '\uFEAA', None,    None   ),
    '\u0630': ('\uFEAB', '\uFEAC', None,    None   ),
    '\u0631': ('\uFEAD', '\uFEAE', None,    None   ),
    '\u0632': ('\uFEAF', '\uFEB0', None,    None   ),
    '\u0633': ('\uFEB1', '\uFEB2', '\uFEB3', '\uFEB4'),
    '\u0634': ('\uFEB5', '\uFEB6', '\uFEB7', '\uFEB8'),
    '\u0635': ('\uFEB9', '\uFEBA', '\uFEBB', '\uFEBC'),
    '\u0636': ('\uFEBD', '\uFEBE', '\uFEBF', '\uFEC0'),
    '\u0637': ('\uFEC1', '\uFEC2', '\uFEC3', '\uFEC4'),
    '\u0638': ('\uFEC5', '\uFEC6', '\uFEC7', '\uFEC8'),
    '\u0639': ('\uFEC9', '\uFECA', '\uFECB', '\uFECC'),
    '\u063A': ('\uFECD', '\uFECE', '\uFECF', '\uFED0'),
    '\u0641': ('\uFED1', '\uFED2', '\uFED3', '\uFED4'),
    '\u0642': ('\uFED5', '\uFED6', '\uFED7', '\uFED8'),
    '\u0643': ('\uFED9', '\uFEDA', '\uFEDB', '\uFEDC'),
    '\u0644': ('\uFEDD', '\uFEDE', '\uFEDF', '\uFEE0'),
    '\u0645': ('\uFEE1', '\uFEE2', '\uFEE3', '\uFEE4'),
    '\u0646': ('\uFEE5', '\uFEE6', '\uFEE7', '\uFEE8'),
    '\u0647': ('\uFEE9', '\uFEEA', '\uFEEB', '\uFEEC'),
    '\u0648': ('\uFEED', '\uFEEE', None,    None   ),
    '\u0649': ('\uFEEF', '\uFEF0', None,    None   ),
    '\u064A': ('\uFEF1', '\uFEF2', '\uFEF3', '\uFEF4'),
}
_AR_DISC  = {'\u0621','\u0622','\u0623','\u0624','\u0625','\u0627',
             '\u0629','\u062F','\u0630','\u0631','\u0632','\u0648','\u0649'}
_LAM_ALEF = {
    '\u0622': ('\uFEF5', '\uFEF6'),
    '\u0623': ('\uFEF7', '\uFEF8'),
    '\u0625': ('\uFEF9', '\uFEFA'),
    '\u0627': ('\uFEFB', '\uFEFC'),
}

def _ar_reshape_inline(text):
    chars = list(text)
    n = len(chars)
    out = []
    i = 0
    while i < n:
        ch = chars[i]
        if ch == '\u0644' and i + 1 < n and chars[i+1] in _LAM_ALEF:
            prev_conn = i > 0 and chars[i-1] in _AR_FORMS and chars[i-1] not in _AR_DISC
            lig = _LAM_ALEF[chars[i+1]]
            out.append(lig[1] if prev_conn else lig[0])
            i += 2; continue
        if ch not in _AR_FORMS:
            out.append(ch); i += 1; continue
        f = _AR_FORMS[ch]
        pc = i > 0 and chars[i-1] in _AR_FORMS and chars[i-1] not in _AR_DISC
        nc = ch not in _AR_DISC and i + 1 < n and chars[i+1] in _AR_FORMS
        if pc and nc:   out.append(f[3] or f[1] or f[0])
        elif pc:        out.append(f[1] or f[0])
        elif nc:        out.append(f[2] or f[0])
        else:           out.append(f[0])
        i += 1
    return ''.join(out)

def _ar_bidi_inline(text):
    """
    Visual BiDi for Kivy (LTR engine):
    1. Splits into RTL (Arabic) and LTR runs
    2. Reverses order of runs
    3. Reverses characters WITHIN each RTL run
    This matches python-bidi output for Arabic text.
    """
    import unicodedata
    runs, cur_rtl, cur = [], None, []
    for ch in text:
        rtl = unicodedata.bidirectional(ch) in ('R', 'AL', 'AN')
        if rtl != cur_rtl and cur:
            runs.append((cur_rtl, ''.join(cur))); cur = []
        cur_rtl = rtl; cur.append(ch)
    if cur: runs.append((cur_rtl, ''.join(cur)))
    result = []
    for is_rtl, run_text in reversed(runs):
        # Reverse chars within RTL runs (critical for correct visual display)
        result.append(run_text[::-1] if is_rtl else run_text)
    return ''.join(result)

@lru_cache(maxsize=4096)
def ar(text: str) -> str:
    """
    يحوّل النص العربي إلى صورته البصرية الصحيحة لـ Kivy.
    يستخدم arabic_reshaper+python-bidi إن كانا متاحَين،
    وإلا يستخدم التطبيق المدمج inline (يعمل 100% على Android).
    """
    if not text:
        return text
    try:
        if _ARABIC_OK:
            shaped    = _ext_reshaper.reshape(text)
            bidi_text = _ext_bidi(shaped)
        else:
            shaped    = _ar_reshape_inline(text)
            bidi_text = _ar_bidi_inline(shaped)
        return '\u202D' + bidi_text + '\u202C'
    except Exception:
        try:
            shaped    = _ar_reshape_inline(text)
            bidi_text = _ar_bidi_inline(shaped)
            return '\u202D' + bidi_text + '\u202C'
        except Exception:
            return text

@lru_cache(maxsize=4096)
def _ar_for_input(text: str) -> str:
    """تشكيل عربي لحقول TextInput — reshape+reverse بدون \u202D...\u202C."""
    if not text:
        return text
    try:
        shaped = (_ext_reshaper.reshape(text) if _ARABIC_OK
                  else _ar_reshape_inline(text))
        return (_ext_bidi(shaped) if _ARABIC_OK else _ar_bidi_inline(shaped))
    except Exception:
        try: return _ar_bidi_inline(_ar_reshape_inline(text))
        except Exception: return text


def _ar_in_kv(kv: str) -> str:
    """
    يُعيد تشكيل كل نص عربي موجود بين علامتَي اقتباس في سلسلة KV
    قبل تمريرها إلى Builder.load_string().
    هذا يضمن أن كل النصوص الثابتة تُعرض بشكل صحيح من أول لحظة.
    """
    def _replace(m):
        s = m.group(1)
        if any('\u0600' <= c <= '\u06FF' for c in s):
            return f'"{ar(s)}"'
        return m.group(0)
    return re.sub(r'"([^"\n]*)"', _replace, kv)


# ══════════════════════════════════════════════════════════════════
#  Font registration  ─  قبل أي استيراد لـ Kivy/KivyMD
# ══════════════════════════════════════════════════════════════════
from kivy.core.text import LabelBase

_HERE = os.path.dirname(os.path.abspath(__file__))

def _font_path(name):
    for p in [name, os.path.join(_HERE, name)]:
        if os.path.exists(p):
            return p
    return None

# تسجيل الخطوط يحدث داخل build() بعد تهيئة التطبيق للتوافق مع Android
# Font registration happens inside build() after app init — Android-safe

# ══════════════════════════════════════════════════════════════════
#  Kivy / KivyMD imports  ─  بعد تسجيل الخط
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
from kivymd.uix.menu import MDDropdownMenu

# ══════════════════════════════════════════════════════════════════
#  Screen classes
# ══════════════════════════════════════════════════════════════════
class HomeScreen(Screen): pass
class AddScreen(Screen): pass
class SearchScreen(Screen): pass
class SettingsScreen(Screen): pass
class FieldsScreen(Screen): pass
class EditScreen(Screen): pass

# ══════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════
DEFAULT_FTP = {
    "host": "mediarouter", "port": 21, "user": "mmk",
    "password": "4d6F6174617@",
    "directory": "/Kingston-09511F45_usb1_1", "filename": "moja.csv",
}
CONFIG_FILE  = "ftp_config.json"
FIELDS_FILE  = "fields_config.json"
LOCAL_CACHE  = "local_cache.csv"
BUILTIN      = ["الاسم", "السن", "رقم الهاتف"]

# ══════════════════════════════════════════════════════════════════
#  KV layout  (النصوص العربية تُعاد صياغتها في build() قبل التحميل)
# ══════════════════════════════════════════════════════════════════
KV = """
ScreenManager:
    HomeScreen:
    AddScreen:
    SearchScreen:
    SettingsScreen:
    FieldsScreen:
    EditScreen:

# ── الشاشة الرئيسية ───────────────────────────────────────
<HomeScreen>:
    name: "home"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "تسجيل قوافل مرسال"
            right_action_items: [["magnify", lambda x: app.go_to("search")], ["sort-variant", lambda x: app.toggle_reorder_mode()], ["cog", lambda x: app.go_to("settings")]]
            left_action_items:  [["format-list-bulleted", lambda x: app.go_to("fields")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_status_bar
            size_hint_y: None
            height: 0
            md_bg_color: 0.88, 0.17, 0.17, 1
            padding: [dp(8), dp(4)]
            MDLabel:
                id: ftp_status_label
                text: ""
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
        MDScrollView:
            on_scroll_y: app.on_scroll_y(self, self.scroll_y)
            MDList:
                id: record_list
                padding:  [dp(8), dp(6)]
                spacing: dp(6)
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.95, "bottom": 0.05}
        on_release: app.go_to("add")

# ── شاشة الإضافة ──────────────────────────────────────────
<AddScreen>:
    name: "add"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إضافة جهة اتصال"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_add
            size_hint_y: None
            height: 0
            md_bg_color: 0.88, 0.17, 0.17, 1
            padding: [dp(10), dp(4)]
            MDLabel:
                text: "غير متصل بسيرفر FTP — لا يمكن الحفظ"
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: fields_box
                padding: [dp(16), dp(16)]
                spacing: dp(14)
                adaptive_height: True
                MDRaisedButton:
                    text: "حفظ السجل"
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.85
                    on_release: app.save_record()

# ── شاشة التعديل ──────────────────────────────────────────
<EditScreen>:
    name: "edit"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "تعديل البيانات"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_edit
            size_hint_y: None
            height: 0
            md_bg_color: 0.88, 0.17, 0.17, 1
            padding: [dp(10), dp(4)]
            MDLabel:
                text: "غير متصل بسيرفر FTP — لا يمكن الحفظ"
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: edit_fields_box
                padding: [dp(16), dp(16)]
                spacing: dp(14)
                adaptive_height: True
                MDRaisedButton:
                    text: "تحديث البيانات"
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.85
                    on_release: app.update_record()

# ── شاشة البحث ────────────────────────────────────────────
<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "بحث"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: [dp(12), dp(10)]
            spacing: dp(10)
            MDTextField:
                id: search_input
                hint_text: "ابحث بالاسم أو أي معلومة..."
                on_text: app.do_search(self.text)
                halign: "right"
                mode: "rectangle"
                base_direction: "rtl"
                text_language: "ar"
            MDScrollView:
                MDList:
                    id: search_list

# ── شاشة الإعدادات ────────────────────────────────────────
<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إعدادات FTP"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: [dp(20), dp(16)]
                spacing: dp(14)
                adaptive_height: True
                MDTextField:
                    id: ftp_host
                    hint_text: "Host (IP / Domain)"
                MDTextField:
                    id: ftp_port
                    hint_text: "Port"
                    input_filter: "int"
                MDTextField:
                    id: ftp_user
                    hint_text: "Username"
                MDTextField:
                    id: ftp_password
                    hint_text: "Password"
                    password: True
                MDTextField:
                    id: ftp_directory
                    hint_text: "Remote Directory"
                MDTextField:
                    id: ftp_filename
                    hint_text: "Filename  (e.g. contacts.csv)"
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(10)
                    MDRaisedButton:
                        text: "حفظ"
                        on_release: app.save_settings()
                    MDFlatButton:
                        text: "اختبار الاتصال"
                        on_release: app.test_connection()
                    MDRaisedButton:
                        text: "استيراد ملف"
                        md_bg_color: app.theme_cls.accent_color
                        on_release: app._open_ftp_browser()

# ── شاشة الحقول ───────────────────────────────────────────
<FieldsScreen>:
    name: "fields"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إدارة الحقول"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: [dp(10), dp(10)]
            spacing: dp(10)
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(6)
                MDTextField:
                    id: new_field_input
                    hint_text: "اسم الحقل الجديد"
                    size_hint_x: 0.5
                    halign: "right"
                    mode: "rectangle"
                    base_direction: "rtl"
                    text_language: "ar"
                MDRaisedButton:
                    id: field_type_btn
                    text: "text"
                    size_hint_x: 0.5
                    on_release: app.open_field_type_menu(self)
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(6)
                MDTextField:
                    id: field_options_input
                    hint_text: "خيارات: خيار1، خيار2"
                    halign: "right"
                    mode: "rectangle"
                    base_direction: "rtl"
                    text_language: "ar"
                MDIconButton:
                    icon: "plus"
                    on_release: app.add_field()
            MDScrollView:
                MDList:
                    id: fields_list
"""

# ══════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════
def parse_multi(value):
    return [v for v in (value or "").split("|") if v]

def serialize_multi(selected):
    return "|".join(selected)

def _rlbl(**kw):
    """
    ينشئ MDLabel مع ربط text_size بالعرض تلقائياً.
    هذا ضروري لـ Kivy: بدون text_size لا يُطبَّق halign='right' فعلياً،
    لأن النص بدونه يُعرض في مساحة بحجم النص نفسه فقط.
    """
    lbl = MDLabel(**kw)
    lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
    return lbl

def attach_ar_handler(tf, initial_value: str = "") -> None:
    """
    يُرفق معالج الإدخال العربي بأي MDTextField.
    — يخزّن القيمة الخامة في tf._raw_value (بدون أحرف التشكيل البصري)
    — يؤجل إعادة العرض للـ frame القادم حتى لا يُعطَّل الكتابة
    — يُهيّئ العرض إن وُجدت قيمة ابتدائية (وضع التعديل)
    — محمي ضد الاستدعاء المزدوج على نفس الـ widget
    """
    if getattr(tf, '_ar_handler_attached', False):
        if initial_value:
            tf._raw_value = initial_value
        return
    tf._ar_handler_attached = True
    tf._raw_value  = initial_value or ""
    tf._ar_syncing = False
    tf._shape_ev   = None

    def _on_text(inst, val, w=tf):
        if w._ar_syncing:
            return
        prev_disp = _ar_for_input(w._raw_value) if w._raw_value else ""
        delta = len(val) - len(prev_disp)
        changed = False
        if delta > 0:
            from_end = val[len(prev_disp):]
            real_new = ''.join(
                c for c in from_end
                if not ('\uFE70' <= c <= '\uFEFF')
                and c not in '\u202D\u202C\u200F\u200E')
            if not real_new:
                from_start = val[:delta]
                real_new = ''.join(
                    c for c in from_start
                    if not ('\uFE70' <= c <= '\uFEFF')
                    and c not in '\u202D\u202C\u200F\u200E')
            if real_new:
                w._raw_value = w._raw_value + real_new
                changed = True
        elif delta < 0:
            d2 = abs(delta)
            w._raw_value = w._raw_value[:-d2] if d2 <= len(w._raw_value) else ""
            changed = True
        elif not val:
            w._raw_value = ""
            changed = True
        if changed:
            if w._shape_ev:
                w._shape_ev.cancel()
            def _do_shape(dt, w=w):
                nd = _ar_for_input(w._raw_value) if w._raw_value else ""
                if nd != w.text:
                    w._ar_syncing = True
                    w.text = nd
                    w._ar_syncing = False
                w._shape_ev = None
            w._shape_ev = Clock.schedule_once(_do_shape, 0)

    tf.bind(text=_on_text)

    if initial_value:
        def _init_display(dt, w=tf, c=initial_value):
            w._ar_syncing = True
            w.text = _ar_for_input(c) if c else ""
            w._ar_syncing = False
        Clock.schedule_once(_init_display, 0)


# ══════════════════════════════════════════════════════════════════
#  FTP Manager
# ══════════════════════════════════════════════════════════════════
class FTPManager:
    """
    مدير اتصال FTP المحسّن — بناءً على best practices من Python ftplib:
    - Passive mode (PASV) مطلوب لأغلب الراوترات المنزلية
    - finally block يضمن إغلاق الاتصال دائماً حتى لو حدث خطأ
    - cascade encoding للـ CSV: utf-8-sig ← utf-8 ← windows-1256
    """

    def __init__(self, cfg):
        self.cfg = cfg

    # ── helpers ────────────────────────────────────────────────
    def _connect(self):
        """يفتح اتصال FTP مع passive mode و timeout 15 ثانية."""
        ftp = FTP()
        ftp.connect(
            host=str(self.cfg.get("host", "")),
            port=int(self.cfg.get("port", 21)),
            timeout=15
        )
        ftp.login(
            user=str(self.cfg.get("user", "")),
            passwd=str(self.cfg.get("password", ""))
        )
        ftp.set_pasv(True)                   # Passive mode: مطلوب للراوترات/NAT
        directory = str(self.cfg.get("directory", "")).strip()
        if directory:
            ftp.cwd(directory)
        return ftp

    def _close(self, ftp):
        """إغلاق آمن للاتصال — لا يرمي استثناء."""
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass

    # ── public methods ─────────────────────────────────────────
    def get_mtime(self):
        """
        يُعيد وقت آخر تعديل للملف على FTP (MDTM command).
        يُستخدم لتجنب تحميل الملف لو لم يتغير — توفير 99% من البيانات.
        يُعيد None لو الأمر غير مدعوم من السيرفر.
        """
        ftp = None
        try:
            ftp = self._connect()
            resp = ftp.sendcmd(f"MDTM {self.cfg['filename']}")
            return resp.split()[-1]   # "213 20250529123456" → "20250529123456"
        except Exception:
            return None               # بعض السيرفرات لا تدعم MDTM
        finally:
            if ftp:
                self._close(ftp)

    def test(self):
        """يختبر الاتصال ويتحقق من الوصول للمجلد."""
        ftp = None
        try:
            ftp = self._connect()
            ftp.pwd()                        # يتأكد من صلاحية المجلد
            return True, "تم الاتصال بنجاح"
        except Exception as e:
            return False, f"فشل الاتصال: {e}"
        finally:
            if ftp:
                self._close(ftp)

    def read_csv(self):
        """يجلب الـ CSV من الـ FTP مع fallback للـ local cache."""
        ftp = None
        try:
            ftp = self._connect()
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {self.cfg['filename']}", buf.write)
            raw = buf.getvalue()
            self._close(ftp)
            ftp = None

            # Cascade encoding: BOM → UTF-8 → Windows-1256 → replace
            text = None
            for enc in ("utf-8-sig", "utf-8", "windows-1256"):
                try:
                    text = raw.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    pass
            if text is None:
                text = raw.decode("utf-8", errors="replace")

            try:
                with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                pass

            return list(csv.DictReader(io.StringIO(text)))

        except Exception as e:
            print(f"[FTP Read] {e}")
            try:
                if os.path.exists(LOCAL_CACHE):
                    with open(LOCAL_CACHE, encoding="utf-8") as f:
                        return list(csv.DictReader(f))
            except Exception:
                pass
            return []
        finally:
            if ftp:
                self._close(ftp)

    def write_csv(self, records, fieldnames):
        """يحفظ السجلات محلياً أولاً ثم يرفعها للـ FTP."""
        ftp = None
        try:
            buf = io.StringIO()
            # extrasaction='ignore': يتجاهل حقول زيادة بدل ما يرمي KeyError
            w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(records)
            data = buf.getvalue()

            try:
                with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                    f.write(data)
            except Exception as ce:
                print(f"[Cache] {ce}")

            ftp = self._connect()
            ftp.storbinary(
                f"STOR {self.cfg['filename']}",
                io.BytesIO(data.encode("utf-8-sig"))  # UTF-8 BOM للـ Excel
            )
            return True
        except Exception as e:
            print(f"[FTP Write] {e}")
            return False
        finally:
            if ftp:
                self._close(ftp)


# ══════════════════════════════════════════════════════════════════
#  App
# ══════════════════════════════════════════════════════════════════
class ContactApp(MDApp):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.records       = []
        self.fields        = [
            {"name": "الاسم",       "type": "text",                           "required": True},
            {"name": "السن",        "type": "text", "input_type": "number", "required": False},
            {"name": "رقم الهاتف", "type": "text", "input_type": "number", "required": False},
        ]
        self.ftp_config    = dict(DEFAULT_FTP)
        self._dirty        = False
        self._editing_idx  = -1
        self._add_widgets  = {}
        self._edit_widgets = {}
        self._ftp_ok       = False
        self._checking     = False   # guard: prevents overlapping _periodic_check threads
        self._syncing      = False   # guard: prevents overlapping _auto_sync threads
        self._page_size    = 20
        self._max_displayed = 200   # حد أقصى للـ widgets المعروضة في القائمة
        self._displayed    = 0
        self._loading_more = False
        self._search_ev    = None   # debounce للبحث
        self._last_mtime   = None   # آخر وقت تعديل للملف على FTP (لـ MDTM check)
        self._ftp_pending  = False  # هل هناك بيانات بانتظار الرفع؟
        self._drag_tgt_idx = -1     # مؤشر العنصر المستهدف أثناء السحب
        self._reorder_mode = False  # وضع إعادة الترتيب

    # ── Build ──────────────────────────────────────────────────
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style     = "Light"
        # ← تسجيل الخطوط هنا بعد تهيئة self.directory (يعمل بشكل صحيح على Android)
        self._register_arabic_fonts()
        # ← تُعاد صياغة كل النصوص العربية في KV قبل تحميلها
        return Builder.load_string(_ar_in_kv(KV))

    def _register_arabic_fonts(self):
        """
        يسجّل الخطوط العربية لجميع متغيرات Roboto المستخدمة في KivyMD.
        MDTopAppBar (H6) تستخدم "RobotoMedium" — يجب تسجيلها صراحةً.
        يستخدم self.directory لإيجاد الخطوط بشكل موثوق على Android و Desktop.
        """
        from kivy.resources import resource_add_path, resource_find
        # أضف مجلد التطبيق لمسارات Kivy حتى تجد resource_find الخطوط
        resource_add_path(self.directory)
        font_registered = False
        for font_file in ["Amiri-Regular.ttf", "Cairo-Bold.ttf"]:
            path = resource_find(font_file)
            if not path:
                candidate = os.path.join(self.directory, font_file)
                if os.path.exists(candidate):
                    path = candidate
            if path:
                try:
                    # سجّل لجميع متغيرات Roboto المستخدمة من KivyMD:
                    # "RobotoMedium" مطلوب لعنوان MDTopAppBar (H6 style)
                    for font_name in ["Roboto", "RobotoMedium", "RobotoBold", "RobotoLight", "ArabicF"]:
                        LabelBase.register(name=font_name, fn_regular=path, fn_bold=path)
                    print(f"[Font] All Roboto variants registered with Arabic font: {path}")
                    font_registered = True
                    break  # Amiri له الأولوية — نتوقف عند أول خط يُوجد
                except Exception as e:
                    print(f"[Font] Failed to register {font_file}: {e}")
        if not font_registered:
            print(f"[Font] WARNING: No Arabic font found in {self.directory}")

    def on_start(self):
        self._load_config()
        self._load_fields()
        self._initial_load()
        Clock.schedule_interval(self._auto_sync,      15)
        Clock.schedule_interval(self._periodic_check, 10)
        Clock.schedule_interval(self._ftp_periodic_sync, 60) # رفع دوري كل دقيقة
        # إعداد اتجاه RTL لحقول الإدخال بعد تهيئة الشاشات
        Clock.schedule_once(self._init_rtl_inputs, 0)

    def _init_rtl_inputs(self, dt):
        """
        يضبط base_direction='rtl' + halign='right' لجميع حقول الإدخال العربية
        المُعرَّفة في KV. نُعيد ضبط hint_text بالعربي الخام (بدون ar()) حتى
        لا يتعارض مع base_direction ولا يحدث عكس مضاعف للنص.
        """
        rtl_fields = [
            ("search",  "search_input",        "ابحث بالاسم أو أي معلومة..."),
            ("fields",  "new_field_input",      "اسم الحقل الجديد"),
            ("fields",  "field_options_input",  "خيارات: خيار1، خيار2"),
        ]
        for screen_name, field_id, raw_hint in rtl_fields:
            try:
                tf = self.root.get_screen(screen_name).ids[field_id]
                tf.hint_text      = ar(raw_hint)
                tf.halign         = "right"
                tf.mode           = "rectangle"  # ← إطار مستطيل مثل حقول الإدخال
                tf.base_direction = "rtl"        # ← يجعل الكتابة من اليمين لليسار
                tf.text_language  = "ar"         # ← يخبر Kivy بلغة النص
                attach_ar_handler(tf)            # ← معالج الإدخال العربي الموحَّد
            except Exception as e:
                print(f"[RTL] {field_id}: {e}")

    # ── Field type dropdown ──────────────────────────────────
    def open_field_type_menu(self, caller):
        """يفتح قائمة منسدلة لاختيار نوع الحقل"""
        if getattr(self, '_active_type_menu', None):
            try:
                self._active_type_menu.dismiss()
            except Exception:
                pass
        items = [
            {
                "text": ar("نصي — كلمات"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="text_word", b=caller: self._select_field_type(x, b),
            },
            {
                "text": ar("نصي — أرقام"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="text_number", b=caller: self._select_field_type(x, b),
            },
            {
                "text": ar("اختيار — checkbox"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="checkbox", b=caller: self._select_field_type(x, b),
            },
            {
                "text": ar("قائمة متعددة — multiselect"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="multiselect", b=caller: self._select_field_type(x, b),
            },
        ]
        self._active_type_menu = MDDropdownMenu(
            caller=caller,
            items=items,
            width_mult=4,
        )
        self._active_type_menu.open()

    def _select_field_type(self, ftype, btn):
        """يحفظ النوع المختار ويحدّث نص الزر"""
        btn._field_type_value = ftype
        labels = {
            "text_word":   ar("نصي — كلمات"),
            "text_number": ar("نصي — أرقام"),
            "checkbox":    ar("اختيار"),
            "multiselect": ar("قائمة متعددة"),
        }
        btn.text = labels.get(ftype, ftype)
        if getattr(self, '_active_type_menu', None):
            try:
                self._active_type_menu.dismiss()
            except Exception:
                pass
        self._active_type_menu = None

    # ── app.ar() متاح من KV إن احتاجه أحد ────────────────────
    def ar(self, text):
        return ar(text)

    # ── Config ─────────────────────────────────────────────────
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                self.ftp_config = json.load(open(CONFIG_FILE, encoding="utf-8"))
            except Exception:
                pass
        self.ftp = FTPManager(self.ftp_config)

    def _load_fields(self):
        if os.path.exists(FIELDS_FILE):
            try:
                data = json.load(open(FIELDS_FILE, encoding="utf-8"))
                if data and isinstance(data[0], str):
                    data = [{"name": n, "type": "text", "required": False}
                            for n in data]
                self.fields = data
            except Exception:
                pass
        # تأكد دائماً أن السن ورقم الهاتف يفتحان لوحة أرقام (للمستخدمين القدامى)
        for fd in self.fields:
            if fd["name"] in ("السن", "رقم الهاتف") and fd.get("type") == "text":
                fd.setdefault("input_type", "number")

    def _save_fields(self):
        with open(FIELDS_FILE, "w", encoding="utf-8") as _f:
            json.dump(self.fields, _f, ensure_ascii=False, indent=2)

    def _field_names(self):
        return [fd["name"] for fd in self.fields]

    # ── Snackbar ───────────────────────────────────────────────
    def _snack(self, text):
        """Toast notification using Window overlay instead of MDSnackbar.
        MDSnackbarText in KivyMD 1.2.0 renders empty — bypassed entirely."""
        has_orig = any('\u0600' <= c <= '\u06FF' for c in (text or ''))
        msg = ar(text) if has_orig else str(text or '')
        if not msg:
            return

        def _show(dt):
            try:
                from kivy.core.window import Window
                from kivy.uix.label import Label
                from kivy.uix.boxlayout import BoxLayout
                from kivy.graphics import Color, RoundedRectangle
                from kivy.animation import Animation

                W = Window.width * 0.88
                H = dp(52)
                X = Window.width * 0.06
                Y = dp(24)

                box = BoxLayout(
                    size_hint=(None, None), size=(W, H), pos=(X, Y),
                    padding=(dp(14), dp(8))
                )
                with box.canvas.before:
                    Color(0.12, 0.12, 0.12, 0.92)
                    rr = RoundedRectangle(size=(W, H), pos=(X, Y),
                                         radius=[dp(8), dp(8), dp(8), dp(8)])
                box.bind(pos=lambda i, v: setattr(rr, 'pos', v))
                box.bind(size=lambda i, v: setattr(rr, 'size', v))

                from kivymd.uix.label import MDLabel
                lbl = MDLabel(
                    text=msg,
                    halign='center',               # center — same as MDTopAppBar title
                    valign='middle',
                    theme_text_color='Custom',
                    text_color=(1, 1, 1, 1),
                    font_style='Body1',
                    size_hint=(1, 1),
                )
                lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))
                box.add_widget(lbl)

                box.opacity = 0
                Window.add_widget(box, index=0)
                Animation(opacity=1, duration=0.2).start(box)

                def _remove(dt):
                    def _done(*_):
                        try: Window.remove_widget(box)
                        except Exception: pass
                    anim = Animation(opacity=0, duration=0.2)
                    anim.bind(on_complete=_done)
                    anim.start(box)
                Clock.schedule_once(_remove, 3)

            except Exception as e:
                print(f'[Snack] {e}')
                try: self._dlg(ar('\u0625\u0634\u0639\u0627\u0631'), str(text))
                except Exception: pass

        Clock.schedule_once(_show, 0)

    def _dlg(self, title, text, buttons=None):
        if buttons is None:
            btn = MDFlatButton(text=ar("حسناً"))
            d   = MDDialog(title=title, text=text, buttons=[btn])
            btn.bind(on_release=lambda x: d.dismiss())
        else:
            d = MDDialog(title=title, text=text, buttons=buttons)
        d.open()
        return d

    # ── FTP status ─────────────────────────────────────────────
    def _periodic_check(self, dt):
        # Guard: skip if a previous check is still running (FTP timeout = 15s > interval 10s)
        if self._checking:
            return
        self._checking = True
        prev = self._ftp_ok
        def _bg():
            ok, _ = self.ftp.test()
            def _ui(dt2):
                self._ftp_ok   = ok
                self._checking = False   # release guard
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
            lbl.text   = "" if self._ftp_ok else ar("غير متصل بسيرفر FTP")
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
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def _no_ftp_dlg(self, msg=""):
        btn_s = MDRaisedButton(text=ar("إعدادات FTP"))
        btn_c = MDFlatButton(text=ar("إغلاق"))
        d = self._dlg(
            ar("غير متصل بالسيرفر"),
            ar(f"لا يمكن حفظ البيانات.\nيجب الاتصال بسيرفر FTP أولاً.\n\n{msg}"),
            [btn_s, btn_c])
        btn_s.bind(on_release=lambda x: (d.dismiss(), self.go_to("settings")))
        btn_c.bind(on_release=lambda x: d.dismiss())

    def _open_ftp_browser(self):
        """تصفح ملفات CSV على FTP"""
        def _bg():
            ftp_c = None
            try:
                ftp_c = self.ftp._connect()
                files = [f for f in ftp_c.nlst() if f.lower().endswith(".csv")]
                Clock.schedule_once(lambda dt: self._show_ftp_files_dialog(files), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._snack(f"خطأ في التصفح: {e}"), 0)
            finally:
                if ftp_c: self.ftp._close(ftp_c)
        threading.Thread(target=_bg, daemon=True).start()

    def _show_ftp_files_dialog(self, files):
        if not files:
            self._snack("لا توجد ملفات CSV")
            return
        
        from kivymd.uix.list import OneLineListItem
        from kivy.uix.scrollview import ScrollView
        from kivymd.uix.list import MDList

        scroll = ScrollView(size_hint_y=None, height=dp(300))
        lst = MDList()
        d = self._dlg(ar("اختر ملفاً للاستيراد"), "", [MDFlatButton(text=ar("إلغاء"), on_release=lambda x: d.dismiss())])
        d.add_widget(scroll)
        scroll.add_widget(lst)

        for f in files:
            item = OneLineListItem(text=f, on_release=lambda x, fname=f: (d.dismiss(), self._import_ftp_file(fname)))
            lst.add_widget(item)
        d.open()

    def _import_ftp_file(self, filename):
        """تحميل واستيراد الملف (حتى 15MB)"""
        def _bg():
            ftp_c = None
            try:
                ftp_c = self.ftp._connect()
                # التحقق من الحجم
                size = ftp_c.size(filename)
                if size > 15 * 1024 * 1024:
                    Clock.schedule_once(lambda dt: self._snack("الملف كبير جداً (أكبر من 15MB)"), 0)
                    return

                buf = io.BytesIO()
                ftp_c.retrbinary(f"RETR {filename}", buf.write)
                raw = buf.getvalue()
                
                text = None
                for enc in ("utf-8-sig", "utf-8", "windows-1256"):
                    try:
                        text = raw.decode(enc)
                        break
                    except: pass
                if not text: text = raw.decode("utf-8", errors="replace")
                
                new_recs = list(csv.DictReader(io.StringIO(text)))
                if new_recs:
                    self.records.extend(new_recs) # APPEND
                    self._save_local_and_sync()
                    Clock.schedule_once(lambda dt: (self._refresh_list(), self._snack(f"تم استيراد {len(new_recs)} سجل")), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._snack(f"فشل الاستيراد: {e}"), 0)
            finally:
                if ftp_c: self.ftp._close(ftp_c)
        threading.Thread(target=_bg, daemon=True).start()

    # ── Navigation ─────────────────────────────────────────────
    def go_to(self, name):
        self.root.transition = SlideTransition(
            direction="left" if name != "home" else "right")
        self.root.current = name
        if   name == "settings": self._load_settings_ui()
        elif name == "fields":
            self._refresh_fields_ui()
            # أعِد ضبط RTL عند العودة لشاشة الحقول (قد تُعاد تهيئة الـ ids)
            Clock.schedule_once(self._init_rtl_inputs, 0)
        elif name == "add":      self._build_add_form(); self._update_bars()
        elif name == "edit":     self._update_bars()
        elif name == "home":     self._displayed = 0; self._refresh_list()
        elif name == "search":
            # أعِد ضبط RTL عند فتح شاشة البحث
            Clock.schedule_once(self._init_rtl_inputs, 0)

    def toggle_reorder_mode(self):
        self._reorder_mode = not self._reorder_mode
        self._refresh_list()
        self._snack("تم تفعيل وضع الترتيب" if self._reorder_mode else "تم إيقاف وضع الترتيب")

    # ── Initial load ───────────────────────────────────────────
    def _initial_load(self):
        try:
            if os.path.exists(LOCAL_CACHE):
                with open(LOCAL_CACHE, encoding="utf-8") as _cf:
                    cached = list(csv.DictReader(_cf))
                if cached:
                    self.records    = cached
                    self._displayed = 0
                    self._refresh_list()
        except Exception:
            pass
        def _bg():
            ok, msg = self.ftp.test()
            recs    = self.ftp.read_csv() if ok else []
            def _ui(dt):
                self._ftp_ok = ok
                if recs and recs != self.records:
                    self.records    = recs
                    self._displayed = 0
                    self._refresh_list()
                self._update_bars()
                if not ok and not self.records:
                    self._snack(f"تعذر الاتصال: {msg}")
                elif not ok:
                    self._snack("يعمل بالبيانات المحلية — لا اتصال بـ FTP")
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def _save_local_and_sync(self, immediate_ftp=False) -> bool:
        """Local-First Helper: حفظ فوري + FTP دوري أو فوري."""
        try:
            buf = io.StringIO()
            w   = csv.DictWriter(buf, fieldnames=self._field_names(), extrasaction="ignore")
            w.writeheader(); w.writerows(self.records)
            csv_data = buf.getvalue()
            with open(LOCAL_CACHE, "w", encoding="utf-8") as _lf:
                _lf.write(csv_data)
        except Exception as le:
            print(f"[LocalSave] {le}"); return False

        if immediate_ftp:
            def _ftp_bg():
                ftp_c = None
                try:
                    ftp_c = self.ftp._connect()
                    ftp_c.storbinary(f"STOR {self.ftp.cfg['filename']}",
                                     io.BytesIO(csv_data.encode("utf-8-sig")))
                    self._ftp_pending = False
                except Exception as fe:
                    print(f"[FTP Immediate Sync] {fe}")
                    self._ftp_pending = True
                finally:
                    if ftp_c: self.ftp._close(ftp_c)
            threading.Thread(target=_ftp_bg, daemon=True).start()
        else:
            self._ftp_pending = True
        return True

    def _ftp_periodic_sync(self, dt):
        """يرفع البيانات للسيرفر كل دقيقة إذا كان هناك تعديلات معلقة."""
        if not self._ftp_pending or self._syncing:
            return
        
        try:
            with open(LOCAL_CACHE, "r", encoding="utf-8") as f:
                csv_data = f.read()
        except Exception:
            return

        def _bg():
            self._syncing = True
            ftp_c = None
            try:
                ftp_c = self.ftp._connect()
                ftp_c.storbinary(f"STOR {self.ftp.cfg['filename']}",
                                 io.BytesIO(csv_data.encode("utf-8-sig")))
                self._ftp_pending = False
                print("[FTP Periodic Sync] Success")
            except Exception as e:
                print(f"[FTP Periodic Sync] Failed: {e}")
            finally:
                if ftp_c: self.ftp._close(ftp_c)
                self._syncing = False
        
        threading.Thread(target=_bg, daemon=True).start()

    def _auto_sync(self, dt):
        # Guard: skip if dirty or a previous sync is still running
        if self._dirty or self._syncing:
            return
        self._syncing = True
        def _bg():
            # فحص وقت التعديل أولاً (MDTM) — أسرع من تحميل الملف كله
            # لو الملف لم يتغير: نتخطى التحميل ونوفر 99% من البيانات
            mtime = self.ftp.get_mtime()
            if mtime and mtime == self._last_mtime:
                # الملف لم يتغير — لا داعي للتحميل
                def _skip(dt2):
                    self._syncing = False
                Clock.schedule_once(_skip, 0)
                return
            # الملف تغيّر (أو MDTM غير مدعوم) — حمّل البيانات كاملة
            recs = self.ftp.read_csv()
            if mtime:
                self._last_mtime = mtime
            def _ui(dt2):
                self._syncing = False
                if recs and recs != self.records:
                    self.records = recs
                    self._refresh_list()
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    # ── List ───────────────────────────────────────────────────
    def _refresh_list(self, append=False):
        lst = self.root.get_screen("home").ids.record_list
        if not append:
            lst.clear_widgets(); self._displayed = 0
        if not self.records:
            if not append:
                lst.add_widget(_rlbl(
                    text=ar("لا توجد سجلات"),
                    halign="center",
                    height=dp(70), size_hint_y=None))
            return
        start = self._displayed
        # حد أقصى للعرض لمنع تراكم الـ widgets في الذاكرة
        end   = min(start + self._page_size, len(self.records), self._max_displayed)
        for i in range(start, end):
            lst.add_widget(self._make_item(i, self.records[i]))
            lst.add_widget(MDCard(height=dp(1), size_hint_y=None,
                                  elevation=0, md_bg_color=[0,0,0,.08]))
        self._displayed = end
        # إشعار للمستخدم لو وصل للحد الأقصى
        if self._displayed >= self._max_displayed < len(self.records):
            lst.add_widget(_rlbl(
                text=ar(f"يعرض أحدث {self._max_displayed} سجل — استخدم البحث للوصول للبقية"),
                halign="center", theme_text_color="Secondary",
                height=dp(50), size_hint_y=None))
        self._loading_more = False

    def _make_item(self, i, rec):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True,
                          padding=[dp(14), dp(8)], spacing=dp(4))
        row = MDBoxLayout(adaptive_height=True, spacing=dp(8))

        # Drag Handle (يظهر فقط في وضع الترتيب)
        if self._reorder_mode:
            handle = MDIconButton(icon="drag-variant", theme_text_color="Secondary")
            handle.bind(on_touch_down=lambda inst, touch: self._on_handle_touch(inst, touch, rec, box))
            row.add_widget(handle)

        info = MDBoxLayout(orientation="vertical", adaptive_height=True)
        info.add_widget(_rlbl(
            text=ar(rec.get("الاسم","") or "بدون اسم"),
            font_style="H6", adaptive_height=True, halign="right"))

        parts = []
        if rec.get("السن"):        parts.append(ar(f"السن: {rec['السن']}"))
        if rec.get("رقم الهاتف"): parts.append(ar(f"الهاتف: {rec['رقم الهاتف']}"))
        if parts:
            info.add_widget(_rlbl(
                text="  |  ".join(parts),
                font_style="Caption", theme_text_color="Secondary",
                adaptive_height=True, halign="right"))

        btns = MDBoxLayout(adaptive_size=True, spacing=dp(2))
        eb = MDIconButton(icon="pencil", theme_text_color="Primary")
        db = MDIconButton(icon="delete",  theme_text_color="Error")
        eb.bind(on_release=lambda x, idx=i: self.go_to_edit(idx))
        db.bind(on_release=lambda x, idx=i: self._confirm_delete(idx))
        btns.add_widget(eb); btns.add_widget(db)
        row.add_widget(btns)
        row.add_widget(info)
        box.add_widget(row)

        # chips للحقول متعددة الاختيار
        for fd in self.fields:
            if fd["type"] != "multiselect": continue
            selected = parse_multi(rec.get(fd["name"], ""))
            if not selected: continue
            chips_row = MDBoxLayout(adaptive_height=True,
                                    spacing=dp(4), padding=[0, dp(2)])
            chips_row.add_widget(_rlbl(
                text=ar(f'{fd["name"]}: '),
                font_style="Caption", adaptive_height=True,
                theme_text_color="Secondary", halign="right"))
            for opt in selected:
                try:
                    chips_row.add_widget(MDChip(text=ar(opt)))
                except Exception:
                    chips_row.add_widget(MDLabel(
                        text=ar(f"[{opt}]"),
                        font_style="Caption", adaptive_size=True))
            box.add_widget(chips_row)

        # Checkboxes تفاعلية — تظهر في القائمة وتُحفظ مباشرة
        for fd in self.fields:
            if fd["type"] != "checkbox": continue
            val  = rec.get(fd["name"], "false")
            cb_row = MDBoxLayout(adaptive_height=True, spacing=dp(8),
                                 padding=[0, dp(2)])
            cb_w = MDCheckbox(
                active=(val == "true"),
                size_hint=(None, None), size=(dp(28), dp(28))
            )
            cb_w.bind(active=lambda inst, v, r=rec, n=fd["name"]:
                      self._toggle_checkbox_by_ref(r, n, v))
            cb_row.add_widget(cb_w)
            cb_row.add_widget(_rlbl(text=ar(fd["name"]),
                                    adaptive_height=True, halign="right"))
            box.add_widget(cb_row)

        return box

    def on_scroll_y(self, sv, val):
        if val < 0.1 and not self._loading_more and self._displayed < len(self.records):
            self._loading_more = True
            self._refresh_list(append=True)

    def _on_handle_touch(self, inst, touch, rec, widget):
        if inst.collide_point(*touch.pos):
            touch.grab(inst)
            widget.md_bg_color = [0, 0, 0, 0.1]
            # ابحث عن الفهرس الحالي للسجل في القائمة
            try:
                self._drag_idx = self.records.index(rec)
            except ValueError:
                return False
            self._drag_widget = widget
            # ربط حركة اللمس
            inst.bind(on_touch_move=self._on_drag_move, on_touch_up=self._on_drag_end)
            return True
        return False

    def _on_drag_move(self, inst, touch):
        if touch.grab_current is inst:
            lst = self.root.get_screen("home").ids.record_list
            # الحصول على جميع العناصر الحقيقية (التي ليست فواصل)
            items = [c for c in lst.children if isinstance(c, MDBoxLayout)]
            for i, child in enumerate(items):
                if child.collide_point(*child.to_widget(*touch.pos)):
                    # Kivy children are reversed
                    self._drag_tgt_idx = len(items) - 1 - i
                    break
            return True
        return False

    def _on_drag_end(self, inst, touch):
        if touch.grab_current is inst:
            touch.ungrab(inst)
            self._drag_widget.md_bg_color = [0, 0, 0, 0]
            if hasattr(self, "_drag_idx") and self._drag_tgt_idx != -1 and self._drag_idx != self._drag_tgt_idx:
                # تحديث الترتيب في البيانات
                item = self.records.pop(self._drag_idx)
                # التأكد من أن الـ index لا يزال صالحاً
                tgt = min(self._drag_tgt_idx, len(self.records))
                self.records.insert(tgt, item)
                self._save_local_and_sync()
                self._refresh_list()
            self._drag_tgt_idx = -1
            inst.unbind(on_touch_move=self._on_drag_move, on_touch_up=self._on_drag_end)
            return True
        return False

    def _toggle_checkbox_by_ref(self, rec_ref, field_name, is_active):
        """يبدّل قيمة checkbox من شاشة القائمة ويحفظ فوراً"""
        rec_ref[field_name] = "true" if is_active else "false"
        self._dirty = True
        def _bg():
            if self._save_local_and_sync():
                self._dirty = False
        threading.Thread(target=_bg, daemon=True).start()

    # ── Field widget factory ────────────────────────────────────
    def _make_field_widget(self, fd, current=""):
        name  = fd["name"]
        ftype = fd["type"]
        req   = " (مطلوب)" if fd.get("required") else ""  # خام — ar() يُطبَّق لاحقاً على النص كاملاً

        if ftype == "text":
            tf = MDTextField(
                hint_text=ar(name + req),
                mode="rectangle",
                text="",
                halign="right",
                base_direction="rtl",
                text_language="ar",
            )
            tf.field_type = "text"

            if fd.get("input_type") == "number":
                # أرقام: لوحة رقمية + فلتر — w.text يحمل القيمة مباشرة
                tf.input_filter = "int"
                tf.input_type   = "number"
                if current:
                    def _init_num(dt, w=tf, c=current):
                        w.text = c
                    Clock.schedule_once(_init_num, 0)
            else:
                # نص عربي: attach_ar_handler يوحّد منطق الإدخال (يشمل _init_display)
                attach_ar_handler(tf, current)
            return tf

        if ftype == "checkbox":
            # يظهر فقط في شاشة العرض (القائمة) — لا في نماذج Add/Edit
            return None

        if ftype == "multiselect":
            c = MDBoxLayout(orientation="vertical", adaptive_height=True,
                            spacing=dp(6), padding=[0, dp(6)])
            c.add_widget(_rlbl(text=ar(name), font_style="Subtitle1",
                               adaptive_height=True, halign="right"))
            selected = parse_multi(current)
            opts     = fd.get("options", [])
            cb_map   = {}
            row      = MDBoxLayout(adaptive_height=True, spacing=dp(8))
            for opt in opts:
                sub = MDBoxLayout(adaptive_size=True, spacing=dp(4))
                cb  = MDCheckbox(active=(opt in selected),
                                 size_hint=(None, None), size=(dp(28), dp(28)))
                sub.add_widget(cb)
                sub.add_widget(MDLabel(text=ar(opt), font_style="Caption",
                                       adaptive_size=True))
                row.add_widget(sub)
                cb_map[opt] = cb
            c.add_widget(row)
            c.cb_map     = cb_map
            c.field_type = "multiselect"
            return c

        return None

    def _read_val(self, w):
        ft = getattr(w, "field_type", None)
        if ft == "text":        return getattr(w, "_raw_value", w.text).strip()
        if ft == "checkbox":    return "true" if w.checkbox.active else "false"
        if ft == "multiselect": return serialize_multi(
            [o for o, cb in w.cb_map.items() if cb.active])
        return ""

    # ── Add form ───────────────────────────────────────────────
    def _build_add_form(self):
        box = self.root.get_screen("add").ids.fields_box
        for w in list(box.children):
            if not isinstance(w, MDRaisedButton):
                box.remove_widget(w)
        self._add_widgets = {}
        for fd in reversed(self.fields):
            wid = self._make_field_widget(fd, "")
            if wid:
                self._add_widgets[fd["name"]] = wid
                box.add_widget(wid, index=len(box.children))

    def save_record(self):
        rec = {}
        for fd in self.fields:
            w   = self._add_widgets.get(fd["name"])
            val = self._read_val(w) if w else ""
            if fd.get("required") and not val:
                self._snack(f'الحقل «{fd["name"]}» مطلوب'); return
            rec[fd["name"]] = val
        
        self.records.insert(0, rec)
        if self._save_local_and_sync():
            self._snack("تمت الإضافة بنجاح ✓")
            self._build_add_form()
            self.go_to("home")
        else:
            self.records.pop(0)
            self._snack("فشل الحفظ المحلي")

    # ── Edit form ──────────────────────────────────────────────
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
        if self._editing_idx == -1: return
        target_rec = self.records[self._editing_idx]
        old_snap   = dict(target_rec)
        new_vals   = {n: self._read_val(w) for n, w in self._edit_widgets.items()}

        for k, v in new_vals.items():
            target_rec[k] = v
        
        if self._save_local_and_sync():
            self._snack("تم التحديث بنجاح ✓")
            self.go_to("home")
        else:
            for k, v in old_snap.items():
                target_rec[k] = v
            self._snack("فشل الحفظ المحلي")

    # ── Delete ─────────────────────────────────────────────────
    def _confirm_delete(self, idx):
        btn_cancel = MDFlatButton(text=ar("إلغاء"))
        btn_del    = MDRaisedButton(text=ar("حذف"), md_bg_color=[1, 0, 0, 1])
        d = self._dlg(ar("تأكيد الحذف"),
                      ar("هل أنت متأكد من حذف هذا السجل؟"),
                      [btn_cancel, btn_del])
        btn_cancel.bind(on_release=lambda x: d.dismiss())
        # نحفظ مرجعاً للسجل نفسه (وليس الـ index) لتفادي حذف سجل خاطئ
        # إذا تغيّر ترتيب السجلات بسبب auto-sync أثناء ظهور نافذة التأكيد
        rec_to_delete = self.records[idx]
        def _do(x):
            d.dismiss()
            if rec_to_delete not in self.records:
                self._snack("السجل لم يُوجد — ربما حُدِّث")
                return
            self.records.remove(rec_to_delete)
            if self._save_local_and_sync(immediate_ftp=True):
                self._snack("تم الحذف")
                self._refresh_list()
            else:
                self.records.insert(0, rec_to_delete)
                self._no_ftp_dlg("فشل حذف البيانات")
        btn_del.bind(on_release=_do)

    # ── Search ─────────────────────────────────────────────────
    def do_search(self, query):
        # Debounce: انتظر 300ms بعد توقف الكتابة قبل تنفيذ البحث الفعلي
        if self._search_ev:
            self._search_ev.cancel()
        self._search_ev = Clock.schedule_once(lambda dt: self._execute_search(), 0.3)

    def _execute_search(self):
        """تنفيذ البحث الفعلي بعد انقضاء الـ debounce"""
        self._search_ev = None
        lst = self.root.get_screen("search").ids.search_list
        lst.clear_widgets()
        # استخدام _raw_value لتجنب أحرف التشكيل البصري في مطابقة البحث
        try:
            tf    = self.root.get_screen("search").ids.search_input
            query = getattr(tf, "_raw_value", "")
        except Exception:
            return
        if not query: return
        q = query.lower()
        for rec in self.records:
            if not any(q in str(v).lower() for v in rec.values()): continue
            parts = []
            if rec.get("السن"):        parts.append(ar(f"السن: {rec['السن']}"))
            if rec.get("رقم الهاتف"): parts.append(ar(f"الهاتف: {rec['رقم الهاتف']}"))
            lst.add_widget(TwoLineAvatarIconListItem(
                text=ar(rec.get("الاسم", "")),
                secondary_text="  |  ".join(parts)))

    # ── Fields management ──────────────────────────────────────
    def _refresh_fields_ui(self, *_):
        lst = self.root.get_screen("fields").ids.fields_list
        lst.clear_widgets()
        tl  = {"checkbox": ar("اختيار — من القائمة"),
               "multiselect": ar("قائمة متعددة")}
        for fd in self.fields:
            name = fd["name"]; tp = fd.get("type", "text")
            opts = fd.get("options", [])
            # نوع النص: أرقام أم كلمات؟
            if tp == "text":
                sec = ar("نصي — أرقام") if fd.get("input_type") == "number" else ar("نصي — كلمات")
            else:
                sec = tl.get(tp, tp)
            if tp == "multiselect" and opts:
                sec += f'  ·  {ar("، ".join(opts[:3]))}' + (" ..." if len(opts)>3 else "")
            if name in BUILTIN:
                sec += f'  ·  {ar("أساسي")}'
            item = TwoLineAvatarIconListItem(
                text=ar(name), secondary_text=sec)
            if name not in BUILTIN:
                btn = IconRightWidget(icon="delete")
                btn.bind(on_release=lambda x, n=name: self._remove_field(n))
                item.add_widget(btn)
            lst.add_widget(item)

    def add_field(self):
        ids      = self.root.get_screen("fields").ids
        # استخدام _raw_value للحصول على النص الخام بدون أحرف التشكيل البصري
        name     = getattr(ids.new_field_input,     "_raw_value", ids.new_field_input.text).strip()
        ftype_v  = getattr(ids.field_type_btn, '_field_type_value', 'text_word')
        opts_raw = getattr(ids.field_options_input, "_raw_value", ids.field_options_input.text).strip()
        if not name:
            self._snack("أدخل اسم الحقل"); return
        if any(fd["name"] == name for fd in self.fields):
            self._snack("الحقل موجود بالفعل"); return
        # ربط قيمة الزر بنوع الحقل و input_type
        _fmap = {
            "text_word":   ("text",        "text"),
            "text_number": ("text",        "number"),
            "checkbox":    ("checkbox",    None),
            "multiselect": ("multiselect", None),
        }
        if ftype_v not in _fmap:
            self._snack("اختر نوع الحقل من القائمة"); return
        ftype, input_type = _fmap[ftype_v]
        opts = []
        if ftype == "multiselect":
            opts = [o.strip() for o in opts_raw.split(",") if o.strip()]
            if len(opts) < 2:
                self._snack("أضف خيارين على الأقل مفصولة بفاصلة"); return
        fd = {"name": name, "type": ftype, "required": False}
        if input_type == "number": fd["input_type"] = "number"
        if opts: fd["options"] = opts
        self.fields.append(fd)
        for r in self.records: r.setdefault(name, "")
        self._save_fields()
        ids.new_field_input.text              = ""
        ids.new_field_input._raw_value        = ""   # إعادة تعيين القيمة الخامة أيضاً
        ids.field_type_btn.text               = ar("نصي — كلمات")
        ids.field_type_btn._field_type_value  = "text_word"
        ids.field_options_input.text          = ""
        ids.field_options_input._raw_value    = ""   # إعادة تعيين القيمة الخامة أيضاً
        self._refresh_fields_ui()

    def _remove_field(self, name):
        if name in BUILTIN: return
        self.fields  = [fd for fd in self.fields if fd["name"] != name]
        for r in self.records: r.pop(name, None)
        self._save_fields(); self._refresh_fields_ui()
        self._save_local_and_sync()

    # ── Settings ───────────────────────────────────────────────
    def _load_settings_ui(self):
        ids = self.root.get_screen("settings").ids
        for k in ["host","port","user","password","directory","filename"]:
            getattr(ids, f"ftp_{k}").text = str(self.ftp_config.get(k, ""))

    def save_settings(self):
        ids = self.root.get_screen("settings").ids
        self.ftp_config = {k: getattr(ids, f"ftp_{k}").text.strip()
                           for k in ["host","user","password","directory","filename"]}
        self.ftp_config["port"] = int(ids.ftp_port.text.strip() or 21)
        with open(CONFIG_FILE, "w", encoding="utf-8") as _f:
            json.dump(self.ftp_config, _f, ensure_ascii=False, indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم حفظ الإعدادات ✓")

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

