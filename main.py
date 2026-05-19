"""
FTP Contact Manager — Arabic Edition
مدير جهات الاتصال عبر FTP مع دعم كامل للغة العربية
متوافق مع KivyMD 1.2.0 + Kivy 2.3.1
"""
import io, csv, json, os, threading
from functools import lru_cache
from ftplib import FTP
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.metrics import dp
from kivy.core.text import LabelBase
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

# ═══════════════════════════════════════════════════════════════════
#  Arabic text support
#  يحوّل النص العربي لشكله الصحيح (حروف متصلة + اتجاه RTL)
#  يعمل مع النص العربي والإنجليزي والمختلط
# ═══════════════════════════════════════════════════════════════════
try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_display
    _ARABIC_OK = True
except ImportError:
    _ARABIC_OK = False

@lru_cache(maxsize=2048)
def ar(text: str) -> str:
    """
    أعد تشكيل النص العربي ليُعرض بشكل صحيح في Kivy.
    - النص العربي:  حروف متصلة + عرض من اليمين لليسار
    - النص الإنجليزي: يُعرض كما هو بدون تغيير
    - النص المختلط: يعالجه خوارزمية BiDi تلقائياً
    - في حالة عدم تثبيت المكتبات: يُعيد النص بدون تغيير
    """
    if not text:
        return text
    if not _ARABIC_OK:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return _bidi_display(reshaped)
    except Exception:
        return text

def _has_arabic(text: str) -> bool:
    """تحقق هل يحتوي النص على حروف عربية"""
    return any('\u0600' <= c <= '\u06FF' for c in (text or ""))

# ═══════════════════════════════════════════════════════════════════
#  Font Registration — Cairo-Bold.ttf
# ═══════════════════════════════════════════════════════════════════
_FONT = "Cairo"
_FONT_LOADED = False
for _fp in [
    "Cairo-Bold.ttf",
    os.path.join(os.path.dirname(__file__), "Cairo-Bold.ttf"),
]:
    if os.path.exists(_fp):
        LabelBase.register(name=_FONT, fn_regular=_fp, fn_bold=_fp)
        _FONT_LOADED = True
        break

if not _FONT_LOADED:
    _FONT = "Roboto"   # fallback to system font

# ═══════════════════════════════════════════════════════════════════
#  Screen classes
# ═══════════════════════════════════════════════════════════════════
class HomeScreen(Screen): pass
class AddScreen(Screen): pass
class SearchScreen(Screen): pass
class SettingsScreen(Screen): pass
class FieldsScreen(Screen): pass
class EditScreen(Screen): pass

# ═══════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════
DEFAULT_FTP_CONFIG = {
    "host": "mediarouter", "port": 21, "user": "mmk",
    "password": "4d6F6174617@",
    "directory": "/Kingston-09511F45_usb1_1", "filename": "moja.csv",
}
CONFIG_FILE  = "ftp_config.json"
FIELDS_FILE  = "fields_config.json"
LOCAL_CACHE  = "local_cache.csv"
BUILTIN      = ["الاسم", "السن", "رقم الهاتف"]

# ═══════════════════════════════════════════════════════════════════
#  KV Layout
# ═══════════════════════════════════════════════════════════════════
KV = """
#: import dp kivy.metrics.dp

# ── تطبيق خط Cairo على جميع الـ Labels تلقائياً ─────────────────
<Label>:
    font_name: app.font

<MDLabel>:
    font_name: app.font

# ─────────────────────────────────────────────────────────────────
ScreenManager:
    HomeScreen:
    AddScreen:
    SearchScreen:
    SettingsScreen:
    FieldsScreen:
    EditScreen:

# ══════════════════ الشاشة الرئيسية ══════════════════
<HomeScreen>:
    name: "home"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: home_toolbar
            title: ""
            right_action_items: [["magnify", lambda x: app.go_to("search")], ["cog", lambda x: app.go_to("settings")]]
            left_action_items: [["format-list-bulleted", lambda x: app.go_to("fields")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_status_bar
            size_hint_y: None
            height: 0
            md_bg_color: 0.9, 0.2, 0.2, 1
            padding: [dp(8), dp(4)]
            MDLabel:
                id: ftp_status_label
                text: ""
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                font_style: "Caption"
        MDScrollView:
            on_scroll_y: app.on_scroll_y(self, self.scroll_y)
            MDList:
                id: record_list
                padding: [dp(8), dp(6)]
                spacing: dp(6)
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.95, "bottom": 0.05}
        on_release: app.go_to("add")

# ══════════════════ شاشة الإضافة ══════════════════
<AddScreen>:
    name: "add"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: add_toolbar
            title: ""
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_add
            size_hint_y: None
            height: 0
            md_bg_color: 0.9, 0.2, 0.2, 1
            padding: [dp(10), dp(4)]
            MDLabel:
                id: ftp_warn_add_lbl
                text: ""
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                font_style: "Caption"
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: fields_box
                padding: [dp(16), dp(16)]
                spacing: dp(14)
                adaptive_height: True
                MDRaisedButton:
                    id: save_btn
                    text: ""
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.85
                    on_release: app.save_record()

# ══════════════════ شاشة التعديل ══════════════════
<EditScreen>:
    name: "edit"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: edit_toolbar
            title: ""
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_edit
            size_hint_y: None
            height: 0
            md_bg_color: 0.9, 0.2, 0.2, 1
            padding: [dp(10), dp(4)]
            MDLabel:
                id: ftp_warn_edit_lbl
                text: ""
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                font_style: "Caption"
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: edit_fields_box
                padding: [dp(16), dp(16)]
                spacing: dp(14)
                adaptive_height: True
                MDRaisedButton:
                    id: update_btn
                    text: ""
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.85
                    on_release: app.update_record()

# ══════════════════ شاشة البحث ══════════════════
<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: search_toolbar
            title: ""
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: [dp(12), dp(10)]
            spacing: dp(10)
            MDTextField:
                id: search_input
                hint_text: ""
                font_name: app.font
                on_text: app.do_search(self.text)
            MDScrollView:
                MDList:
                    id: search_list

# ══════════════════ شاشة الإعدادات ══════════════════
<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: settings_toolbar
            title: ""
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
                    font_name: app.font
                MDTextField:
                    id: ftp_port
                    hint_text: "Port"
                    input_filter: "int"
                    font_name: app.font
                MDTextField:
                    id: ftp_user
                    hint_text: "Username"
                    font_name: app.font
                MDTextField:
                    id: ftp_password
                    hint_text: "Password"
                    password: True
                    font_name: app.font
                MDTextField:
                    id: ftp_directory
                    hint_text: "Remote Directory"
                    font_name: app.font
                MDTextField:
                    id: ftp_filename
                    hint_text: "Filename  (e.g. contacts.csv)"
                    font_name: app.font
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(10)
                    MDRaisedButton:
                        id: save_settings_btn
                        text: ""
                        on_release: app.save_settings()
                    MDFlatButton:
                        id: test_conn_btn
                        text: ""
                        on_release: app.test_connection()

# ══════════════════ شاشة الحقول ══════════════════
<FieldsScreen>:
    name: "fields"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: fields_toolbar
            title: ""
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
                    hint_text: ""
                    font_name: app.font
                    size_hint_x: 0.5
                MDTextField:
                    id: field_type_input
                    hint_text: "text / checkbox / multiselect"
                    font_name: app.font
                    size_hint_x: 0.5
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(6)
                MDTextField:
                    id: field_options_input
                    hint_text: ""
                    font_name: app.font
                MDIconButton:
                    icon: "plus"
                    on_release: app.add_field()
            MDScrollView:
                MDList:
                    id: fields_list
"""

# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════
def parse_multi(value: str) -> list:
    return [v for v in (value or "").split("|") if v]

def serialize_multi(selected: list) -> str:
    return "|".join(selected)

# ═══════════════════════════════════════════════════════════════════
#  FTP Manager
# ═══════════════════════════════════════════════════════════════════
class FTPManager:
    def __init__(self, config):
        self.config = config

    def _connect(self):
        ftp = FTP()
        ftp.connect(self.config["host"], int(self.config["port"]), timeout=10)
        ftp.login(self.config["user"], self.config["password"])
        if self.config.get("directory"):
            ftp.cwd(self.config["directory"])
        return ftp

    def test(self):
        try:
            ftp = self._connect()
            ftp.quit()
            return True, ar("تم الاتصال بنجاح")
        except Exception as e:
            return False, ar(f"فشل الاتصال: {e}")

    def read_csv(self):
        try:
            ftp = self._connect()
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {self.config['filename']}", buf.write)
            ftp.quit()
            buf.seek(0)
            text = buf.read().decode("utf-8")
            with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                f.write(text)
            return list(csv.DictReader(io.StringIO(text)))
        except Exception as e:
            print(f"[FTP Read] {e}")
            if os.path.exists(LOCAL_CACHE):
                with open(LOCAL_CACHE, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            return []

    def write_csv(self, records, fieldnames):
        try:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
            data = output.getvalue()
            with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                f.write(data)
            ftp = self._connect()
            ftp.storbinary(
                f"STOR {self.config['filename']}",
                io.BytesIO(data.encode("utf-8")),
            )
            ftp.quit()
            return True
        except Exception as e:
            print(f"[FTP Write] {e}")
            return False

# ═══════════════════════════════════════════════════════════════════
#  App
# ═══════════════════════════════════════════════════════════════════
class ContactApp(MDApp):

    # يُعرَّض كـ property حتى تستطيع قواعد KV قراءته
    font = _FONT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.records       = []
        self.fields        = [
            {"name": "الاسم",       "type": "text", "required": True},
            {"name": "السن",        "type": "text", "required": False},
            {"name": "رقم الهاتف", "type": "text", "required": False},
        ]
        self.ftp_config    = dict(DEFAULT_FTP_CONFIG)
        self._dirty        = False
        self._editing_idx  = -1
        self._add_widgets  = {}
        self._edit_widgets = {}
        self._ftp_ok       = False
        self._page_size    = 20
        self._displayed    = 0
        self._loading_more = False

    # ── App method so KV can call app.ar(...) ─────────────────────
    def ar(self, text: str) -> str:
        return ar(text)

    # ── Build ─────────────────────────────────────────────────────
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style     = "Light"
        return Builder.load_string(KV)

    def on_start(self):
        self._apply_ui_strings()
        self._load_config()
        self._load_fields()
        self._initial_load()
        Clock.schedule_interval(self._auto_sync,      15)
        Clock.schedule_interval(self._periodic_check, 10)

    # ── Translate all static UI strings on start ──────────────────
    def _apply_ui_strings(self):
        """
        يضبط جميع النصوص العربية الثابتة في الواجهة بعد عملية
        إعادة التشكيل حتى تُعرض الحروف متصلة بشكل صحيح.
        """
        root = self.root

        def _title(screen, widget_id, text):
            try:
                root.get_screen(screen).ids[widget_id].title = ar(text)
            except Exception:
                pass

        def _text(screen, widget_id, text):
            try:
                root.get_screen(screen).ids[widget_id].text = ar(text)
            except Exception:
                pass

        def _hint(screen, widget_id, text):
            try:
                root.get_screen(screen).ids[widget_id].hint_text = ar(text)
            except Exception:
                pass

        # Toolbar titles
        _title("home",     "home_toolbar",     "مدير جهات الاتصال")
        _title("add",      "add_toolbar",      "إضافة جهة اتصال")
        _title("edit",     "edit_toolbar",     "تعديل البيانات")
        _title("search",   "search_toolbar",   "بحث")
        _title("settings", "settings_toolbar", "إعدادات FTP")
        _title("fields",   "fields_toolbar",   "إدارة الحقول")

        # Buttons
        _text("add",      "save_btn",          "حفظ السجل")
        _text("edit",     "update_btn",        "تحديث البيانات")
        _text("settings", "save_settings_btn", "حفظ")
        _text("settings", "test_conn_btn",     "اختبار الاتصال")

        # FTP warning labels
        _text("add",  "ftp_warn_add_lbl",
              "غير متصل بسيرفر FTP — لا يمكن الحفظ")
        _text("edit", "ftp_warn_edit_lbl",
              "غير متصل بسيرفر FTP — لا يمكن الحفظ")

        # Hint texts
        _hint("search", "search_input",       "ابحث بالاسم أو أي معلومة...")
        _hint("fields", "new_field_input",    "اسم الحقل الجديد")
        _hint("fields", "field_options_input","خيارات: خيار1، خيار2، خيار3")

    # ── Config ────────────────────────────────────────────────────
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.ftp_config = json.load(f)
            except Exception:
                pass
        self.ftp = FTPManager(self.ftp_config)

    def _load_fields(self):
        if os.path.exists(FIELDS_FILE):
            try:
                with open(FIELDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data and isinstance(data[0], str):
                    self.fields = [{"name": n, "type": "text", "required": False}
                                   for n in data]
                else:
                    self.fields = data
            except Exception:
                pass

    def _save_fields(self):
        with open(FIELDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fields, f, ensure_ascii=False, indent=2)

    def _field_names(self):
        return [fd["name"] for fd in self.fields]

    def _get_field(self, name):
        return next((fd for fd in self.fields if fd["name"] == name), None)

    # ── Notifications ─────────────────────────────────────────────
    def _snack(self, text: str):
        display = ar(text)
        def _show(dt):
            try:
                from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
                snack_lbl = MDSnackbarText(text=display)
                snack_lbl.font_name = _FONT
                MDSnackbar(
                    snack_lbl,
                    y=dp(24),
                    pos_hint={"center_x": 0.5},
                    size_hint_x=0.92,
                    duration=3,
                ).open()
            except (ImportError, TypeError):
                try:
                    from kivymd.uix.snackbar import Snackbar
                    s = Snackbar()
                    s.text = display
                    s.open()
                except Exception:
                    self._dialog(ar("رسالة"), display)
        Clock.schedule_once(_show, 0)

    def _dialog(self, title: str, text: str):
        try:
            btn = MDFlatButton(text=ar("حسناً"))
            d = MDDialog(title=title, text=text, buttons=[btn])
            btn.bind(on_release=lambda x: d.dismiss())
            d.open()
        except Exception:
            print(f"[{title}] {text}")

    # ── FTP status ────────────────────────────────────────────────
    def _periodic_check(self, dt):
        prev = self._ftp_ok
        def _check():
            ok, _ = self.ftp.test()
            def _update(dt2):
                self._ftp_ok = ok
                if prev and not ok:
                    self._snack("انقطع الاتصال بسيرفر FTP")
                self._refresh_status_bars()
            Clock.schedule_once(_update, 0)
        threading.Thread(target=_check, daemon=True).start()

    def _refresh_status_bars(self):
        try:
            bar = self.root.get_screen("home").ids.ftp_status_bar
            lbl = self.root.get_screen("home").ids.ftp_status_label
            if self._ftp_ok:
                bar.height = 0
                lbl.text   = ""
            else:
                bar.height = dp(32)
                lbl.text   = ar("غير متصل بسيرفر FTP")
        except Exception:
            pass
        h = dp(38) if not self._ftp_ok else 0
        for sn, bid in [("add", "ftp_warning_add"), ("edit", "ftp_warning_edit")]:
            try:
                self.root.get_screen(sn).ids[bid].height = h
            except Exception:
                pass

    def _require_ftp(self, callback):
        self._snack("جاري التحقق من الاتصال...")
        def _check():
            ok, msg = self.ftp.test()
            def _done(dt):
                self._ftp_ok = ok
                self._refresh_status_bars()
                if ok:
                    callback()
                else:
                    self._show_no_ftp_dialog(msg)
            Clock.schedule_once(_done, 0)
        threading.Thread(target=_check, daemon=True).start()

    def _show_no_ftp_dialog(self, msg=""):
        try:
            btn_settings = MDRaisedButton(text=ar("إعدادات FTP"))
            btn_close    = MDFlatButton(text=ar("إغلاق"))
            d = MDDialog(
                title=ar("غير متصل بالسيرفر"),
                text=ar(f"لا يمكن حفظ البيانات.\nيجب الاتصال بسيرفر FTP أولاً.\n\n{msg}"),
                buttons=[btn_settings, btn_close],
            )
            btn_settings.bind(on_release=lambda x: (d.dismiss(), self.go_to("settings")))
            btn_close.bind(on_release=lambda x: d.dismiss())
            d.open()
        except Exception:
            self._snack(f"خطأ: {msg}")

    # ── Navigation ────────────────────────────────────────────────
    def go_to(self, name: str):
        self.root.transition = SlideTransition(
            direction="left" if name != "home" else "right")
        self.root.current = name
        if   name == "settings": self._load_settings_ui()
        elif name == "fields":   self._refresh_fields_ui()
        elif name == "add":      self._build_add_form(); self._refresh_status_bars()
        elif name == "edit":     self._refresh_status_bars()
        elif name == "home":     self._displayed = 0; self._refresh_list()

    # ── Load ──────────────────────────────────────────────────────
    def _initial_load(self):
        def _task():
            ok, msg = self.ftp.test()
            recs = self.ftp.read_csv() if ok else []
            def _done(dt):
                self._ftp_ok = ok
                self.records = recs
                self._displayed = 0
                self._refresh_list()
                self._refresh_status_bars()
                if not ok:
                    self._snack(f"تعذر الاتصال: {msg}")
            Clock.schedule_once(_done, 0)
        threading.Thread(target=_task, daemon=True).start()

    def _auto_sync(self, dt):
        if self._dirty:
            return
        def _task():
            recs = self.ftp.read_csv()
            if recs and recs != self.records:
                self.records = recs
                Clock.schedule_once(lambda dt2: self._refresh_list(), 0)
        threading.Thread(target=_task, daemon=True).start()

    # ── List ──────────────────────────────────────────────────────
    def _refresh_list(self, append=False):
        lst = self.root.get_screen("home").ids.record_list
        if not append:
            lst.clear_widgets()
            self._displayed = 0
        if not self.records:
            if not append:
                lbl = MDLabel(
                    text=ar("لا توجد سجلات"),
                    halign="center",
                    height=dp(70),
                    size_hint_y=None,
                    font_name=_FONT,
                )
                lst.add_widget(lbl)
            return
        start = self._displayed
        end   = min(start + self._page_size, len(self.records))
        for i in range(start, end):
            lst.add_widget(self._make_item(i, self.records[i]))
            lst.add_widget(MDCard(
                height=dp(1), size_hint_y=None,
                elevation=0, md_bg_color=[0, 0, 0, 0.08]))
        self._displayed    = end
        self._loading_more = False

    def _make_item(self, i, rec):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True,
                          padding=[dp(14), dp(8)], spacing=dp(4))
        row = MDBoxLayout(adaptive_height=True, spacing=dp(8))

        # Info column
        info = MDBoxLayout(orientation="vertical", adaptive_height=True)

        name_text = ar(rec.get("الاسم", "") or ar("بدون اسم"))
        name_lbl  = MDLabel(
            text=name_text,
            font_style="H6",
            adaptive_height=True,
            font_name=_FONT,
            halign="right",
        )
        info.add_widget(name_lbl)

        details_parts = []
        if rec.get("السن"):
            details_parts.append(ar(f"السن: {rec['السن']}"))
        if rec.get("رقم الهاتف"):
            details_parts.append(ar(f"الهاتف: {rec['رقم الهاتف']}"))
        if details_parts:
            details_lbl = MDLabel(
                text="  |  ".join(details_parts),
                font_style="Caption",
                theme_text_color="Secondary",
                adaptive_height=True,
                font_name=_FONT,
                halign="right",
            )
            info.add_widget(details_lbl)

        row.add_widget(info)

        # Action buttons
        btns = MDBoxLayout(adaptive_size=True, spacing=dp(2))
        eb = MDIconButton(icon="pencil", theme_text_color="Primary")
        db = MDIconButton(icon="delete",  theme_text_color="Error")
        eb.bind(on_release=lambda x, idx=i: self.go_to_edit(idx))
        db.bind(on_release=lambda x, idx=i: self._confirm_delete(idx))
        btns.add_widget(eb)
        btns.add_widget(db)
        row.add_widget(btns)
        box.add_widget(row)

        # Multiselect chips
        for fd in self.fields:
            if fd["type"] == "multiselect":
                selected = parse_multi(rec.get(fd["name"], ""))
                if selected:
                    chips_row = MDBoxLayout(adaptive_height=True,
                                           spacing=dp(4), padding=[0, dp(2)])
                    chips_row.add_widget(MDLabel(
                        text=ar(f'{fd["name"]}: '),
                        font_style="Caption",
                        adaptive_size=True,
                        theme_text_color="Secondary",
                        font_name=_FONT,
                    ))
                    for opt in selected:
                        try:
                            chip = MDChip(text=ar(opt))
                            chips_row.add_widget(chip)
                        except Exception:
                            chips_row.add_widget(MDLabel(
                                text=ar(f"[{opt}]"),
                                font_style="Caption",
                                adaptive_size=True,
                                font_name=_FONT,
                            ))
                    box.add_widget(chips_row)
        return box

    def on_scroll_y(self, sv, val):
        if val < 0.1 and not self._loading_more and self._displayed < len(self.records):
            self._loading_more = True
            self._refresh_list(append=True)

    # ── Add Form ──────────────────────────────────────────────────
    def _build_add_form(self):
        box = self.root.get_screen("add").ids.fields_box
        for w in list(box.children):
            if not isinstance(w, MDRaisedButton):
                box.remove_widget(w)
        self._add_widgets = {}
        for fd in reversed(self.fields):
            widget = self._make_field_widget(fd, "")
            if widget:
                self._add_widgets[fd["name"]] = widget
                box.add_widget(widget, index=len(box.children))

    def _make_field_widget(self, fd, current_value):
        """ينشئ widget مناسباً لنوع الحقل مع دعم الخط العربي"""
        name    = fd["name"]
        ftype   = fd["type"]
        req_sfx = ar(" (مطلوب)") if fd.get("required") else ""

        if ftype == "text":
            tf = MDTextField(
                hint_text=ar(name) + req_sfx,
                mode="rectangle",
                text=current_value or "",
                font_name=_FONT,
                halign="right",
            )
            tf.field_type = "text"
            return tf

        elif ftype == "checkbox":
            container = MDBoxLayout(
                adaptive_height=True, spacing=dp(10),
                size_hint_y=None, height=dp(44))
            cb  = MDCheckbox(
                active=(current_value == "true"),
                size_hint=(None, None), size=(dp(32), dp(32)))
            lbl = MDLabel(
                text=ar(name),
                adaptive_height=True,
                font_name=_FONT,
                halign="right",
            )
            container.add_widget(cb)
            container.add_widget(lbl)
            container.checkbox   = cb
            container.field_type = "checkbox"
            return container

        elif ftype == "multiselect":
            container = MDBoxLayout(orientation="vertical", adaptive_height=True,
                                    spacing=dp(6), padding=[0, dp(6)])
            container.add_widget(MDLabel(
                text=ar(name),
                font_style="Subtitle1",
                adaptive_height=True,
                font_name=_FONT,
                halign="right",
            ))
            selected  = parse_multi(current_value)
            options   = fd.get("options", [])
            cb_map    = {}
            chips_box = MDBoxLayout(adaptive_height=True,
                                    spacing=dp(8), padding=[0, dp(2)])
            for opt in options:
                cb_row = MDBoxLayout(adaptive_size=True, spacing=dp(4))
                cb = MDCheckbox(
                    active=(opt in selected),
                    size_hint=(None, None), size=(dp(28), dp(28)))
                cb_row.add_widget(cb)
                cb_row.add_widget(MDLabel(
                    text=ar(opt),
                    font_style="Caption",
                    adaptive_size=True,
                    font_name=_FONT,
                ))
                chips_box.add_widget(cb_row)
                cb_map[opt] = cb
            container.add_widget(chips_box)
            container.cb_map     = cb_map
            container.field_type = "multiselect"
            return container

        return None

    def _read_widget_value(self, widget):
        ft = getattr(widget, "field_type", None)
        if ft == "text":
            return widget.text.strip()
        if ft == "checkbox":
            return "true" if widget.checkbox.active else "false"
        if ft == "multiselect":
            return serialize_multi(
                [opt for opt, cb in widget.cb_map.items() if cb.active])
        return ""

    # ── Save ──────────────────────────────────────────────────────
    def save_record(self):
        new_rec = {}
        for fd in self.fields:
            name   = fd["name"]
            widget = self._add_widgets.get(name)
            val    = self._read_widget_value(widget) if widget else ""
            if fd.get("required") and not val:
                self._snack(f"الحقل «{name}» مطلوب")
                return
            new_rec[name] = val

        def _do():
            self.records.insert(0, new_rec)
            self._dirty = True
            ok = self.ftp.write_csv(self.records, self._field_names())
            if ok:
                self._dirty = False
                Clock.schedule_once(lambda dt: self._snack("تمت الإضافة بنجاح ✓"), 0)
                Clock.schedule_once(lambda dt: self.go_to("home"),               0)
            else:
                self.records.pop(0)
                self._dirty = False
                Clock.schedule_once(lambda dt: self._show_no_ftp_dialog("فشل رفع الملف"), 0)
        self._require_ftp(_do)

    # ── Edit ──────────────────────────────────────────────────────
    def go_to_edit(self, idx: int):
        self._editing_idx = idx
        rec = self.records[idx]
        self.go_to("edit")
        box = self.root.get_screen("edit").ids.edit_fields_box
        for w in list(box.children):
            if not isinstance(w, MDRaisedButton):
                box.remove_widget(w)
        self._edit_widgets = {}
        for fd in reversed(self.fields):
            widget = self._make_field_widget(fd, rec.get(fd["name"], ""))
            if widget:
                self._edit_widgets[fd["name"]] = widget
                box.add_widget(widget, index=len(box.children))

    def update_record(self):
        if self._editing_idx == -1:
            return
        old = dict(self.records[self._editing_idx])
        new_vals = {name: self._read_widget_value(w)
                    for name, w in self._edit_widgets.items()}

        def _do():
            for k, v in new_vals.items():
                self.records[self._editing_idx][k] = v
            self._dirty = True
            ok = self.ftp.write_csv(self.records, self._field_names())
            if ok:
                self._dirty = False
                Clock.schedule_once(lambda dt: self._snack("تم التحديث بنجاح ✓"), 0)
                Clock.schedule_once(lambda dt: self.go_to("home"),                0)
            else:
                self.records[self._editing_idx] = old
                self._dirty = False
                Clock.schedule_once(
                    lambda dt: self._show_no_ftp_dialog("فشل رفع الملف"), 0)
        self._require_ftp(_do)

    # ── Delete ────────────────────────────────────────────────────
    def _confirm_delete(self, idx: int):
        btn_cancel = MDFlatButton(text=ar("إلغاء"))
        btn_delete = MDRaisedButton(text=ar("حذف"), md_bg_color="red")
        d = MDDialog(
            text=ar("هل أنت متأكد من حذف هذا السجل؟"),
            buttons=[btn_cancel, btn_delete],
        )
        btn_cancel.bind(on_release=lambda x: d.dismiss())
        def _do(x):
            d.dismiss()
            def _exec():
                ok, msg = self.ftp.test()
                if not ok:
                    Clock.schedule_once(
                        lambda dt: self._show_no_ftp_dialog(msg), 0)
                    return
                self.records.pop(idx)
                self._dirty = True
                self.ftp.write_csv(self.records, self._field_names())
                self._dirty = False
                Clock.schedule_once(
                    lambda dt: (self._snack("تم الحذف"), self._refresh_list()), 0)
            threading.Thread(target=_exec, daemon=True).start()
        btn_delete.bind(on_release=_do)
        d.open()

    # ── Search ────────────────────────────────────────────────────
    def do_search(self, query: str):
        lst = self.root.get_screen("search").ids.search_list
        lst.clear_widgets()
        if not query:
            return
        q = query.lower()
        for rec in self.records:
            if any(q in str(v).lower() for v in rec.values()):
                name_raw = rec.get("الاسم", "")
                age      = rec.get("السن", "")
                phone    = rec.get("رقم الهاتف", "")
                sec_parts = []
                if age:   sec_parts.append(ar(f"السن: {age}"))
                if phone: sec_parts.append(ar(f"الهاتف: {phone}"))
                item = TwoLineAvatarIconListItem(
                    text=ar(name_raw),
                    secondary_text="  |  ".join(sec_parts),
                )
                lst.add_widget(item)

    # ── Fields Management ─────────────────────────────────────────
    def _refresh_fields_ui(self, *a):
        lst = self.root.get_screen("fields").ids.fields_list
        lst.clear_widgets()
        type_labels = {
            "text":        ar("نصي"),
            "checkbox":    ar("اختيار"),
            "multiselect": ar("قائمة متعددة"),
        }
        for fd in self.fields:
            name    = fd["name"]
            tp      = fd.get("type", "text")
            opts    = fd.get("options", [])
            tl      = type_labels.get(tp, tp)
            sec     = tl
            if tp == "multiselect" and opts:
                preview = "، ".join(opts[:3])
                sec += f"  ·  {ar(preview)}" + (" ..." if len(opts) > 3 else "")
            if name in BUILTIN:
                sec += f"  ·  {ar('أساسي')}"
            item = TwoLineAvatarIconListItem(
                text=ar(name),
                secondary_text=sec,
            )
            if name not in BUILTIN:
                btn = IconRightWidget(icon="delete")
                btn.bind(on_release=lambda x, n=name: self._remove_field(n))
                item.add_widget(btn)
            lst.add_widget(item)

    def add_field(self):
        ids         = self.root.get_screen("fields").ids
        name        = ids.new_field_input.text.strip()
        ftype       = ids.field_type_input.text.strip().lower() or "text"
        options_raw = ids.field_options_input.text.strip()

        if not name:
            self._snack("أدخل اسم الحقل")
            return
        if any(fd["name"] == name for fd in self.fields):
            self._snack("الحقل موجود بالفعل")
            return
        if ftype not in ("text", "checkbox", "multiselect"):
            self._snack("النوع يجب أن يكون: text أو checkbox أو multiselect")
            return
        if ftype == "multiselect":
            opts = [o.strip() for o in options_raw.split(",") if o.strip()]
            if len(opts) < 2:
                self._snack("أضف خيارين على الأقل مفصولة بفاصلة")
                return
        else:
            opts = []

        new_fd = {"name": name, "type": ftype, "required": False}
        if opts:
            new_fd["options"] = opts
        self.fields.append(new_fd)
        for r in self.records:
            r.setdefault(name, "")
        self._save_fields()
        ids.new_field_input.text    = ""
        ids.field_type_input.text   = ""
        ids.field_options_input.text = ""
        self._refresh_fields_ui()

    def _remove_field(self, name: str):
        if name not in BUILTIN:
            self.fields  = [fd for fd in self.fields if fd["name"] != name]
            for r in self.records:
                r.pop(name, None)
            self._save_fields()
            self._refresh_fields_ui()

    # ── Settings ──────────────────────────────────────────────────
    def _load_settings_ui(self):
        ids = self.root.get_screen("settings").ids
        for k in ["host", "port", "user", "password", "directory", "filename"]:
            getattr(ids, f"ftp_{k}").text = str(self.ftp_config.get(k, ""))

    def save_settings(self):
        ids = self.root.get_screen("settings").ids
        self.ftp_config = {
            k: getattr(ids, f"ftp_{k}").text.strip()
            for k in ["host", "user", "password", "directory", "filename"]
        }
        self.ftp_config["port"] = int(ids.ftp_port.text.strip() or 21)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.ftp_config, f, ensure_ascii=False, indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم حفظ الإعدادات ✓")

    def test_connection(self):
        self._snack("جاري اختبار الاتصال...")
        def _task():
            ok, msg = self.ftp.test()
            self._ftp_ok = ok
            Clock.schedule_once(lambda dt: self._snack(msg),                    0)
            Clock.schedule_once(lambda dt: self._refresh_status_bars(),         0)
        threading.Thread(target=_task, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ContactApp().run()
