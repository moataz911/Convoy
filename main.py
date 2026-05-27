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
            right_action_items: [["magnify", lambda x: app.go_to("search")], ["cog", lambda x: app.go_to("settings")]]
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
                    text: "حفظ التعديلات"
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.85
                    on_release: app.update_record()

# ── شاشة البحث ────────────────────────────────────────────
<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "البحث عن جهة اتصال"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: [dp(16), dp(10)]
            spacing: dp(10)
            MDTextField:
                id: search_input
                hint_text: "ابحث بالاسم أو أي معلومة..."
                mode: "rectangle"
                on_text: app.on_search_text(self.text)
            MDScrollView:
                MDList:
                    id: search_results
                    padding: [0, dp(10)]

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
            padding: [dp(16), dp(16)]
            spacing: dp(16)
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                spacing: dp(10)
                MDTextField:
                    id: new_field_input
                    hint_text: "اسم الحقل الجديد"
                    mode: "rectangle"
                MDRaisedButton:
                    text: "إضافة"
                    pos_hint: {"center_y": 0.5}
                    on_release: app.add_custom_field()
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                spacing: dp(10)
                MDTextField:
                    id: field_options_input
                    hint_text: "خيارات: خيار1، خيار2"
                    mode: "rectangle"
                    helper_text: "اختياري للحقول من نوع 'قائمة'"
                    helper_text_mode: "on_focus"
                MDRaisedButton:
                    id: field_type_btn
                    text: "نصي"
                    pos_hint: {"center_y": 0.5}
                    on_release: app.open_field_type_menu(self)
            MDLabel:
                text: "الحقول الحالية:"
                theme_text_color: "Primary"
                font_style: "Subtitle1"
                size_hint_y: None
                height: dp(30)
            MDScrollView:
                MDList:
                    id: fields_list

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
                padding: [dp(20), dp(20)]
                spacing: dp(15)
                adaptive_height: True
                MDTextField:
                    id: ftp_host
                    hint_text: "عنوان السيرفر (Host)"
                    text: "mediarouter"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_port
                    hint_text: "المنفذ (Port)"
                    text: "21"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_user
                    hint_text: "اسم المستخدم"
                    text: "mmk"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_password
                    hint_text: "كلمة المرور"
                    password: True
                    text: "4d6F6174617@"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_directory
                    hint_text: "المجلد"
                    text: "/Kingston-09511F45_usb1_1"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_filename
                    hint_text: "اسم ملف الـ CSV"
                    text: "moja.csv"
                    mode: "rectangle"
                MDBoxLayout:
                    spacing: dp(15)
                    size_hint_y: None
                    height: dp(50)
                    MDRaisedButton:
                        text: "حفظ الإعدادات"
                        size_hint_x: 0.6
                        on_release: app.save_settings()
                    MDRaisedButton:
                        text: "اختبار الاتصال"
                        size_hint_x: 0.4
                        md_bg_color: 0.3, 0.3, 0.3, 1
                        on_release: app.test_ftp_connection()
"""

# ══════════════════════════════════════════════════════════════════
#  FTP Manager — تم تحديثه بالكود المستخرج من py.py مع الحفاظ على التوافق
# ══════════════════════════════════════════════════════════════════
class FTPManager:
    """
    نظام إدارة الاتصال بـ FTP المستخرج من py.py والمطور للتوافق مع KivyMD.
    """

    def __init__(self, cfg):
        self.cfg = cfg

    def test(self):
        """يختبر الاتصال ويتحقق من الوصول للمجلد."""
        try:
            ftp = FTP()
            ftp.connect(str(self.cfg.get("host", "")), int(self.cfg.get("port", 21)), timeout=15)
            ftp.login(str(self.cfg.get("user", "")), str(self.cfg.get("password", "")))
            
            directory = str(self.cfg.get("directory", "")).strip()
            if directory:
                ftp.cwd(directory)
            
            ftp.quit()
            return True, "تم الاتصال بنجاح"
        except Exception as e:
            return False, f"فشل الاتصال: {e}"

    def read_csv(self):
        """يجلب الـ CSV من الـ FTP مع fallback للـ local cache."""
        try:
            ftp = FTP()
            ftp.connect(str(self.cfg.get("host", "")), int(self.cfg.get("port", 21)), timeout=15)
            ftp.login(str(self.cfg.get("user", "")), str(self.cfg.get("password", "")))
            
            directory = str(self.cfg.get("directory", "")).strip()
            if directory:
                ftp.cwd(directory)
            
            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {self.cfg['filename']}", buffer.write)
            raw = buffer.getvalue()
            ftp.quit()

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

            # تحديث الكاش المحلي
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

    def write_csv(self, records, fieldnames):
        """يحفظ السجلات محلياً أولاً ثم يرفعها للـ FTP."""
        try:
            # التحضير المحلي
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(records)
            data = buf.getvalue()

            try:
                with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                    f.write(data)
            except Exception as ce:
                print(f"[Cache] {ce}")

            # الرفع للـ FTP
            ftp = FTP()
            ftp.connect(str(self.cfg.get("host", "")), int(self.cfg.get("port", 21)), timeout=15)
            ftp.login(str(self.cfg.get("user", "")), str(self.cfg.get("password", "")))
            
            directory = str(self.cfg.get("directory", "")).strip()
            if directory:
                ftp.cwd(directory)
            
            ftp.storbinary(
                f"STOR {self.cfg['filename']}",
                io.BytesIO(data.encode("utf-8-sig"))  # UTF-8 BOM للـ Excel
            )
            ftp.quit()
            return True
        except Exception as e:
            print(f"[FTP Write] {e}")
            return False


# ══════════════════════════════════════════════════════════════════
#  App
# ══════════════════════════════════════════════════════════════════
class ContactApp(MDApp):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.records       = []
        self.fields        = [
            {"name": "الاسم",       "type": "text", "required": True},
            {"name": "السن",        "type": "text", "required": False},
            {"name": "رقم الهاتف", "type": "text", "required": False},
        ]
        self.ftp_config    = dict(DEFAULT_FTP)
        self._dirty        = False
        self._editing_idx  = -1
        self._add_widgets  = {}
        self._edit_widgets = {}
        self._ftp_ok       = False
        self._page_size    = 20
        self._displayed    = 0
        self._loading_more = False

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
                tf.hint_text       = ar(raw_hint)
                tf.halign          = "right"
                tf.base_direction  = "rtl"        # ← يجعل الكتابة من اليمين لليسار
                tf.text_language   = "ar"         # ← يخبر Kivy بلغة النص
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
                "text": ar("نصي  —  text"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="text", b=caller: self._select_field_type(x, b),
            },
            {
                "text": ar("اختيار  —  checkbox"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="checkbox", b=caller: self._select_field_type(x, b),
            },
            {
                "text": ar("قائمة متعددة  —  multiselect"),
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
            "text":        ar("نصي"),
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

    def _save_fields(self):
        json.dump(self.fields, open(FIELDS_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

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
        prev = self._ftp_ok
        def _bg():
            ok, _ = self.ftp.test()
            def _ui(dt):
                self._ftp_ok = ok
                self._update_status_bar()
                if ok and not prev:
                    self._snack("تم الاتصال بسيرفر FTP")
                    self._initial_load()
                elif not ok and prev:
                    self._snack("فقد الاتصال بسيرفر FTP")
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def _update_status_bar(self):
        bar = self.root.get_screen("home").ids.ftp_status_bar
        lbl = self.root.get_screen("home").ids.ftp_status_label
        
        # تحذيرات الشاشات الأخرى
        for sid in ["ftp_warning_add", "ftp_warning_edit"]:
            try:
                w = self.root.get_screen(sid.split("_")[-1]).ids[sid]
                w.height = 0 if self._ftp_ok else dp(32)
            except Exception: pass

        if self._ftp_ok:
            bar.height = 0
        else:
            bar.height = dp(32)
            lbl.text   = ar("أنت تعمل في الوضع المحلي (أوفلاين) — لن يتم حفظ البيانات على السيرفر")

    # ── Navigation ─────────────────────────────────────────────
    def go_to(self, screen_name, direction="left"):
        if screen_name == "add":
            self._setup_add_screen()
        elif screen_name == "fields":
            self._setup_fields_screen()
        elif screen_name == "home":
            direction = "right"
            self._initial_load()

        self.root.transition = SlideTransition(direction=direction)
        self.root.current    = screen_name

    # ── Data Loading ───────────────────────────────────────────
    def _initial_load(self):
        def _bg():
            recs = self.ftp.read_csv()
            def _ui(dt):
                self.records = recs
                self._displayed = 0
                self.root.get_screen("home").ids.record_list.clear_widgets()
                self._load_more_records()
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def on_scroll_y(self, scroll_view, scroll_y):
        if scroll_y < 0.1 and not self._loading_more:
            self._load_more_records()

    def _load_more_records(self):
        if self._displayed >= len(self.records):
            return
        
        self._loading_more = True
        target = min(self._displayed + self._page_size, len(self.records))
        lst    = self.root.get_screen("home").ids.record_list
        
        for i in range(self._displayed, target):
            r = self.records[i]
            lst.add_widget(self._create_list_item(r, i))
            
        self._displayed = target
        self._loading_more = False

    def _create_list_item(self, r, idx):
        name  = r.get("الاسم", "بدون اسم")
        phone = r.get("رقم الهاتف", "")
        item  = TwoLineAvatarIconListItem(
            text=ar(name),
            secondary_text=ar(phone),
            on_release=lambda x: self._open_edit(idx)
        )
        item.add_widget(IconRightWidget(icon="account-edit", on_release=lambda x: self._open_edit(idx)))
        return item

    # ── Add Screen ─────────────────────────────────────────────
    def _setup_add_screen(self):
        box = self.root.get_screen("add").ids.fields_box
        # احتفظ بالزر
        btn = box.children[0]
        box.clear_widgets()
        self._add_widgets = {}

        for fd in self.fields:
            name = fd["name"]
            if fd["type"] == "text":
                tf = MDTextField(
                    hint_text=ar(name),
                    mode="rectangle",
                    halign="right",
                    base_direction="rtl"
                )
                box.add_widget(tf)
                self._add_widgets[name] = tf
            elif fd["type"] == "checkbox":
                row = MDBoxLayout(adaptive_height=True, spacing=dp(10))
                cb  = MDCheckbox(size_hint=(None, None), size=(dp(48), dp(48)))
                row.add_widget(cb)
                row.add_widget(MDLabel(text=ar(name), halign="right"))
                box.add_widget(row)
                self._add_widgets[name] = cb
            elif fd["type"] == "multiselect":
                box.add_widget(MDLabel(text=ar(name), theme_text_color="Hint", font_style="Caption", halign="right"))
                chips = MDBoxLayout(adaptive_height=True, spacing=dp(8))
                opts  = fd.get("options", [])
                self._add_widgets[name] = []
                for o in opts:
                    cp = MDChip(text=ar(o), checkable=True)
                    chips.add_widget(cp)
                    self._add_widgets[name].append((o, cp))
                box.add_widget(chips)

        box.add_widget(btn)

    def save_record(self):
        new_r = {}
        for fd in self.fields:
            name = fd["name"]
            w    = self._add_widgets[name]
            if fd["type"] == "text":
                val = w.text.strip()
                if fd.get("required") and not val:
                    self._snack(f"يرجى إدخال {name}")
                    return
                new_r[name] = val
            elif fd["type"] == "checkbox":
                new_r[name] = "نعم" if w.active else "لا"
            elif fd["type"] == "multiselect":
                sel = [o for o, cp in w if cp.active]
                new_r[name] = " | ".join(sel)

        self.records.insert(0, new_r)
        self._dirty = True
        self._snack("تمت الإضافة بنجاح")
        self.go_to("home", "right")
        self._auto_sync(0)

    # ── Edit Screen ────────────────────────────────────────────
    def _open_edit(self, idx):
        self._editing_idx = idx
        r = self.records[idx]
        box = self.root.get_screen("edit").ids.edit_fields_box
        btn = box.children[0]
        box.clear_widgets()
        self._edit_widgets = {}

        # تأكد من وجود كل الحقول في السجل (حتى لو أضيفت حديثاً)
        for fd in self.fields:
            name = fd["name"]
            val  = r.get(name, "")
            if fd["type"] == "text":
                tf = MDTextField(
                    text=str(val),
                    hint_text=ar(name),
                    mode="rectangle",
                    halign="right",
                    base_direction="rtl"
                )
                box.add_widget(tf)
                self._edit_widgets[name] = tf
            elif fd["type"] == "checkbox":
                row = MDBoxLayout(adaptive_height=True, spacing=dp(10))
                cb  = MDCheckbox(active=(val == "نعم"), size_hint=(None, None), size=(dp(48), dp(48)))
                row.add_widget(cb)
                row.add_widget(MDLabel(text=ar(name), halign="right"))
                box.add_widget(row)
                self._edit_widgets[name] = cb
            elif fd["type"] == "multiselect":
                box.add_widget(MDLabel(text=ar(name), theme_text_color="Hint", font_style="Caption", halign="right"))
                chips = MDBoxLayout(adaptive_height=True, spacing=dp(8))
                opts  = fd.get("options", [])
                sel   = [s.strip() for s in str(val).split("|")]
                self._edit_widgets[name] = []
                for o in opts:
                    cp = MDChip(text=ar(o), checkable=True, active=(o in sel))
                    chips.add_widget(cp)
                    self._edit_widgets[name].append((o, cp))
                box.add_widget(chips)

        box.add_widget(btn)
        self.go_to("edit")

    def update_record(self):
        if self._editing_idx < 0: return
        r = self.records[self._editing_idx]
        
        for fd in self.fields:
            name = fd["name"]
            w    = self._edit_widgets[name]
            if fd["type"] == "text":
                r[name] = w.text.strip()
            elif fd["type"] == "checkbox":
                r[name] = "نعم" if w.active else "لا"
            elif fd["type"] == "multiselect":
                sel = [o for o, cp in w if cp.active]
                r[name] = " | ".join(sel)

        self._dirty = True
        self._snack("تم تحديث البيانات")
        self.go_to("home", "right")
        self._auto_sync(0)

    # ── Search ─────────────────────────────────────────────────
    def on_search_text(self, text):
        lst = self.root.get_screen("search").ids.search_results
        lst.clear_widgets()
        if not text.strip(): return

        query = text.lower()
        count = 0
        for i, r in enumerate(self.records):
            match = False
            for v in r.values():
                if query in str(v).lower():
                    match = True; break
            if match:
                lst.add_widget(self._create_list_item(r, i))
                count += 1
                if count > 50: break

    # ── Fields Management ──────────────────────────────────────
    def _setup_fields_screen(self):
        lst = self.root.get_screen("fields").ids.fields_list
        lst.clear_widgets()
        for i, fd in enumerate(self.fields):
            name = fd["name"]
            if name in BUILTIN: continue
            item = TwoLineAvatarIconListItem(text=ar(name), secondary_text=ar(f"النوع: {fd['type']}"))
            item.add_widget(IconRightWidget(icon="delete", on_release=lambda x, idx=i: self.delete_field(idx)))
            lst.add_widget(item)

    def add_custom_field(self):
        name = self.root.get_screen("fields").ids.new_field_input.text.strip()
        opts = self.root.get_screen("fields").ids.field_options_input.text.strip()
        ftype = getattr(self.root.get_screen("fields").ids.field_type_btn, '_field_type_value', 'text')
        
        if not name: return
        if any(f["name"] == name for f in self.fields):
            self._snack("هذا الحقل موجود بالفعل")
            return

        new_fd = {"name": name, "type": ftype, "required": False}
        if ftype == "multiselect" and opts:
            new_fd["options"] = [o.strip() for o in opts.split("،") if o.strip()]
        
        self.fields.append(new_fd)
        self._save_fields()
        self._setup_fields_screen()
        self.root.get_screen("fields").ids.new_field_input.text = ""
        self.root.get_screen("fields").ids.field_options_input.text = ""
        self._snack("تمت إضافة الحقل")

    def delete_field(self, idx):
        self.fields.pop(idx)
        self._save_fields()
        self._setup_fields_screen()

    # ── Settings ───────────────────────────────────────────────
    def save_settings(self):
        s = self.root.get_screen("settings").ids
        self.ftp_config = {
            "host": s.ftp_host.text.strip(),
            "port": int(s.ftp_port.text or 21),
            "user": s.ftp_user.text.strip(),
            "password": s.ftp_password.text.strip(),
            "directory": s.ftp_directory.text.strip(),
            "filename": s.ftp_filename.text.strip(),
        }
        json.dump(self.ftp_config, open(CONFIG_FILE, "w", encoding="utf-8"), indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم حفظ الإعدادات")
        self._periodic_check(0)

    def test_ftp_connection(self):
        s = self.root.get_screen("settings").ids
        tmp_cfg = {
            "host": s.ftp_host.text.strip(),
            "port": int(s.ftp_port.text or 21),
            "user": s.ftp_user.text.strip(),
            "password": s.ftp_password.text.strip(),
            "directory": s.ftp_directory.text.strip(),
        }
        tester = FTPManager(tmp_cfg)
        def _bg():
            ok, msg = tester.test()
            def _ui(dt):
                self._dlg(ar("نتيجة الاختبار"), ar(msg))
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    # ── Sync ───────────────────────────────────────────────────
    def _auto_sync(self, dt):
        if not self._dirty or not self._ftp_ok:
            return
        
        def _bg():
            if self.ftp.write_csv(self.records, self._field_names()):
                self._dirty = False
                def _ui(dt): self._snack("تمت المزامنة مع السيرفر")
                Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

if __name__ == "__main__":
    ContactApp().run()
