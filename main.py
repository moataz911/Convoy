"""
FTP Contact Manager - Fixed Arabic & RTL
"""
import io, csv, json, os, threading, re
from ftplib import FTP
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
from kivy.core.text import LabelBase

# استيراد مكتبات معالجة اللغة العربية
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

def fix_text(text):
    """إصلاح عرض النص العربي (Reshaping & Bidi)"""
    if not text or not isinstance(text, str):
        return text
    if not arabic_reshaper or not get_display:
        return text
    # التحقق من وجود حروف عربية
    if not re.search(r'[\u0600-\u06FF]', text):
        return text
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

# تسجيل الخط
font_path = "Cairo-Bold.ttf"
if not os.path.exists(font_path):
    font_path = os.path.join(os.path.dirname(__file__), "Cairo-Bold.ttf")

if os.path.exists(font_path):
    LabelBase.register(name="Arabic", fn_regular=font_path)

class HomeScreen(Screen): pass
class AddScreen(Screen): pass
class SearchScreen(Screen): pass
class SettingsScreen(Screen): pass
class FieldsScreen(Screen): pass
class EditScreen(Screen): pass

DEFAULT_FTP_CONFIG = {
    "host": "mediarouter", "port": 21, "user": "mmk",
    "password": "4d6F6174617@",
    "directory": "/Kingston-09511F45_usb1_1", "filename": "moja.csv",
}
CONFIG_FILE  = "ftp_config.json"
FIELDS_FILE  = "fields_config.json"
LOCAL_CACHE  = "local_cache.csv"
BUILTIN      = ["الاسم", "السن", "رقم الهاتف"]

# إضافة قواعد KV لفرض الخط والاتجاه
KV = """
#:import fix_text __main__.fix_text

<MDLabel>:
    font_name: "Arabic"

<MDTextField>:
    font_name_hint: "Arabic"
    font_name_helper_text: "Arabic"
    font_name_max_length: "Arabic"
    # لضمان ظهور النص العربي بشكل صحيح في خانات الإدخال
    base_direction: "rtl"
    text_size: self.size
    halign: "right"

<MDRaisedButton>:
    font_name: "Arabic"

<MDFlatButton>:
    font_name: "Arabic"

ScreenManager:
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
            title: fix_text("مدير جهات الاتصال")
            right_action_items: [["magnify", lambda x: app.go_to("search")], ["cog", lambda x: app.go_to("settings")]]
            left_action_items: [["format-list-bulleted", lambda x: app.go_to("fields")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_status_bar
            size_hint_y: None
            height: 0
            md_bg_color: 1, 0.2, 0.2, 1
            padding: dp(8)
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
                padding: dp(10)
                spacing: dp(8)
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.95, "bottom": 0.05}
        on_release: app.go_to("add")

<AddScreen>:
    name: "add"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: fix_text("اضافة جديد")
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: fields_box
                padding: dp(20)
                spacing: dp(15)
                adaptive_height: True
                MDRaisedButton:
                    text: fix_text("حفظ السجل")
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.8
                    on_release: app.save_record()

<EditScreen>:
    name: "edit"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: fix_text("تعديل السجل")
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: edit_fields_box
                padding: dp(20)
                spacing: dp(15)
                adaptive_height: True
                MDRaisedButton:
                    text: fix_text("تحديث البيانات")
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.8
                    on_release: app.update_record()

<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: fix_text("بحث")
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(10)
            spacing: dp(10)
            MDTextField:
                id: search_input
                hint_text: fix_text("ابحث بالاسم او اي معلومة...")
                on_text: app.do_search(self.text)
            MDScrollView:
                MDList:
                    id: search_list

<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: fix_text("اعدادات FTP")
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(20)
                spacing: dp(15)
                adaptive_height: True
                MDTextField:
                    id: ftp_host
                    hint_text: "Host (IP/Domain)"
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
                    hint_text: "Filename (e.g. data.csv)"
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(10)
                    MDRaisedButton:
                        text: fix_text("حفظ")
                        on_release: app.save_settings()
                    MDFlatButton:
                        text: fix_text("اختبار الاتصال")
                        on_release: app.test_connection()

<FieldsScreen>:
    name: "fields"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: fix_text("ادارة الحقول")
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(10)
            spacing: dp(10)
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(5)
                MDTextField:
                    id: new_field_input
                    hint_text: fix_text("اسم الحقل الجديد")
                    size_hint_x: 0.5
                MDTextField:
                    id: field_type_input
                    hint_text: fix_text("النوع: text/checkbox/multiselect")
                    size_hint_x: 0.5
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(5)
                MDTextField:
                    id: field_options_input
                    hint_text: fix_text("خيارات القائمة: خيار1,خيار2,خيار3")
                MDIconButton:
                    icon: "plus"
                    on_release: app.add_field()
            MDScrollView:
                MDList:
                    id: fields_list
"""

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
            ftp = self._connect(); ftp.quit()
            return True, "تم الاتصال بنجاح"
        except Exception as e:
            return False, f"فشل الاتصال: {e}"

    def read_csv(self):
        try:
            ftp = self._connect()
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {self.config['filename']}", buf.write)
            ftp.quit()
            buf.seek(0)
            text = buf.read().decode("utf-8")
            with open(LOCAL_CACHE, "w", encoding="utf-8") as f: f.write(text)
            return list(csv.DictReader(io.StringIO(text)))
        except Exception as e:
            if os.path.exists(LOCAL_CACHE):
                with open(LOCAL_CACHE, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            return []

    def write_csv(self, records, fieldnames):
        try:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader(); writer.writerows(records)
            with open(LOCAL_CACHE, "w", encoding="utf-8") as f: f.write(output.getvalue())
            ftp = self._connect()
            ftp.storbinary(f"STOR {self.config['filename']}", io.BytesIO(output.getvalue().encode("utf-8")))
            ftp.quit()
            return True
        except Exception as e:
            return False

class ContactApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.records   = []
        self.fields    = [
            {"name":"الاسم","type":"text","required":True},
            {"name":"السن","type":"text","required":False},
            {"name":"رقم الهاتف","type":"text","required":False},
        ]
        self.ftp_config   = dict(DEFAULT_FTP_CONFIG)
        self._dirty       = False
        self._editing_idx = -1
        self._add_widgets   = {}
        self._edit_widgets  = {}
        self._ftp_ok      = False
        self._page_size   = 20
        self._displayed   = 0
        self._loading_more = False

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        
        # تعيين الخط العربي في الثيم
        self.theme_cls.font_styles.update({
            "H1": ["Arabic", 96, False, -1.5],
            "H2": ["Arabic", 60, False, -0.5],
            "H3": ["Arabic", 48, False, 0],
            "H4": ["Arabic", 34, False, 0.25],
            "H5": ["Arabic", 24, False, 0],
            "H6": ["Arabic", 20, False, 0.15],
            "Subtitle1": ["Arabic", 16, False, 0.15],
            "Subtitle2": ["Arabic", 14, False, 0.1],
            "Body1": ["Arabic", 16, False, 0.5],
            "Body2": ["Arabic", 14, False, 0.25],
            "Button": ["Arabic", 14, True, 1.25],
            "Caption": ["Arabic", 12, False, 0.4],
            "Overline": ["Arabic", 10, False, 1.5],
        })
        
        return Builder.load_string(KV)

    def on_start(self):
        self._load_config()
        self._load_fields()
        self._initial_load()
        Clock.schedule_interval(self._auto_sync, 15)
        Clock.schedule_interval(self._periodic_check, 10)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.ftp_config = json.load(f)
            except: pass
        self.ftp = FTPManager(self.ftp_config)

    def _load_fields(self):
        if os.path.exists(FIELDS_FILE):
            try:
                with open(FIELDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data and isinstance(data[0], str):
                    self.fields = [{"name": n, "type": "text", "required": False} for n in data]
                else:
                    self.fields = data
            except: pass

    def _save_fields(self):
        with open(FIELDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fields, f, ensure_ascii=False, indent=2)

    def _snack(self, text: str):
        def _show(dt):
            try:
                from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
                MDSnackbar(MDSnackbarText(text=fix_text(text)),
                           y=dp(24), pos_hint={"center_x": 0.5},
                           size_hint_x=0.9, duration=3).open()
            except: pass
        Clock.schedule_once(_show, 0)

    def _simple_dialog(self, title, text):
        try:
            d = MDDialog(title=fix_text(title), text=fix_text(text),
                         buttons=[MDFlatButton(text=fix_text("حسناً"), on_release=lambda x: d.dismiss())])
            d.open()
        except: pass

    def _periodic_check(self, dt):
        def _check():
            ok, _ = self.ftp.test()
            def _update(dt2):
                self._ftp_ok = ok
                self._refresh_status_bars()
            Clock.schedule_once(_update, 0)
        threading.Thread(target=_check, daemon=True).start()

    def _refresh_status_bars(self):
        try:
            bar = self.root.get_screen("home").ids.ftp_status_bar
            lbl = self.root.get_screen("home").ids.ftp_status_label
            bar.height = 0 if self._ftp_ok else dp(28)
            lbl.text = "" if self._ftp_ok else fix_text("غير متصل بسيرفر FTP")
        except: pass

    def _require_ftp(self, callback):
        def _check():
            ok, msg = self.ftp.test()
            def _done(dt):
                self._ftp_ok = ok
                if ok: callback()
                else: self._snack(f"خطأ: {msg}")
            Clock.schedule_once(_done, 0)
        threading.Thread(target=_check, daemon=True).start()

    def go_to(self, name: str):
        self.root.transition = SlideTransition(direction="left" if name != "home" else "right")
        self.root.current = name
        if name == "settings":   self._load_settings_ui()
        elif name == "fields":   self._refresh_fields_ui()
        elif name == "add":      self._build_add_form()
        elif name == "home":     self._displayed = 0; self._refresh_list()

    def _initial_load(self):
        def _task():
            ok, _ = self.ftp.test()
            recs = self.ftp.read_csv() if ok else []
            def _done(dt):
                self._ftp_ok = ok
                self.records = recs
                self._refresh_list()
            Clock.schedule_once(_done, 0)
        threading.Thread(target=_task, daemon=True).start()

    def _auto_sync(self, dt):
        if self._dirty: return
        def _task():
            recs = self.ftp.read_csv()
            if recs and recs != self.records:
                self.records = recs
                Clock.schedule_once(lambda dt2: self._refresh_list(), 0)
        threading.Thread(target=_task, daemon=True).start()

    def _refresh_list(self, append=False):
        lst = self.root.get_screen("home").ids.record_list
        if not append:
            lst.clear_widgets(); self._displayed = 0
        if not self.records:
            if not append:
                lst.add_widget(MDLabel(text=fix_text("لا توجد سجلات"), halign="center", height=dp(60), size_hint_y=None))
            return
        start, end = self._displayed, min(self._displayed + self._page_size, len(self.records))
        for i in range(start, end):
            lst.add_widget(self._make_item(i, self.records[i]))
        self._displayed = end
        self._loading_more = False

    def _make_item(self, i, rec):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True, padding=[dp(14), dp(8)], spacing=dp(4))
        row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        info = MDBoxLayout(orientation="vertical", adaptive_height=True)
        
        info.add_widget(MDLabel(text=fix_text(rec.get("الاسم","بدون اسم")), font_style="H6", halign="right"))
        
        details = f"السن: {rec.get('السن','')} | الهاتف: {rec.get('رقم الهاتف','')}"
        info.add_widget(MDLabel(text=fix_text(details), font_style="Caption", theme_text_color="Secondary", halign="right"))
        
        row.add_widget(info)
        btns = MDBoxLayout(adaptive_size=True, spacing=dp(2))
        eb = MDIconButton(icon="pencil", on_release=lambda x, idx=i: self.go_to_edit(idx))
        db = MDIconButton(icon="delete", theme_text_color="Error", on_release=lambda x, idx=i: self._confirm_delete(idx))
        btns.add_widget(eb); btns.add_widget(db)
        row.add_widget(btns)
        box.add_widget(row)
        return box

    def on_scroll_y(self, sv, val):
        if val < 0.1 and not self._loading_more and self._displayed < len(self.records):
            self._loading_more = True
            self._refresh_list(append=True)

    def _build_add_form(self):
        box = self.root.get_screen("add").ids.fields_box
        for w in list(box.children):
            if not isinstance(w, MDRaisedButton): box.remove_widget(w)
        self._add_widgets = {}
        for fd in reversed(self.fields):
            if fd["type"] == "text":
                tf = MDTextField(hint_text=fix_text(fd["name"]), mode="rectangle")
                self._add_widgets[fd["name"]] = tf
                box.add_widget(tf, index=len(box.children))

    def save_record(self):
        new_rec = {name: w.text.strip() for name, w in self._add_widgets.items()}
        def _do():
            self.records.insert(0, new_rec); self._dirty = True
            if self.ftp.write_csv(self.records, [fd["name"] for fd in self.fields]):
                self._dirty = False
                self._snack("تم الحفظ"); self.go_to("home")
        self._require_ftp(_do)

    def go_to_edit(self, idx: int):
        self._editing_idx = idx
        rec = self.records[idx]
        self.go_to("edit")
        box = self.root.get_screen("edit").ids.edit_fields_box
        for w in list(box.children):
            if not isinstance(w, MDRaisedButton): box.remove_widget(w)
        self._edit_widgets = {}
        for fd in reversed(self.fields):
            if fd["type"] == "text":
                tf = MDTextField(hint_text=fix_text(fd["name"]), text=rec.get(fd["name"],""), mode="rectangle")
                self._edit_widgets[fd["name"]] = tf
                box.add_widget(tf, index=len(box.children))

    def update_record(self):
        new_vals = {name: w.text.strip() for name, w in self._edit_widgets.items()}
        def _do():
            for k, v in new_vals.items(): self.records[self._editing_idx][k] = v
            self._dirty = True
            if self.ftp.write_csv(self.records, [fd["name"] for fd in self.fields]):
                self._dirty = False
                self._snack("تم التحديث"); self.go_to("home")
        self._require_ftp(_do)

    def _confirm_delete(self, idx: int):
        def _do(x):
            d.dismiss()
            self.records.pop(idx)
            self.ftp.write_csv(self.records, [fd["name"] for fd in self.fields])
            self._refresh_list()
        d = MDDialog(text=fix_text("حذف السجل؟"), buttons=[MDFlatButton(text=fix_text("الغاء"), on_release=lambda x: d.dismiss()), MDRaisedButton(text=fix_text("حذف"), on_release=_do)])
        d.open()

    def do_search(self, query: str):
        lst = self.root.get_screen("search").ids.search_list
        lst.clear_widgets()
        if not query: return
        q = query.lower()
        for rec in self.records:
            if any(q in str(v).lower() for v in rec.values()):
                lst.add_widget(TwoLineAvatarIconListItem(text=fix_text(rec.get("الاسم","")), secondary_text=fix_text(rec.get("رقم الهاتف",""))))

    def _refresh_fields_ui(self, *a):
        lst = self.root.get_screen("fields").ids.fields_list
        lst.clear_widgets()
        for fd in self.fields:
            lst.add_widget(TwoLineAvatarIconListItem(text=fix_text(fd["name"]), secondary_text=fix_text(fd.get("type","text"))))

    def save_settings(self):
        s = self.root.get_screen("settings").ids
        self.ftp_config.update({"host": s.ftp_host.text, "port": s.ftp_port.text, "user": s.ftp_user.text, "password": s.ftp_password.text, "directory": s.ftp_directory.text, "filename": s.ftp_filename.text})
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.ftp_config, f)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم الحفظ")

    def test_connection(self):
        def _task():
            ok, msg = self.ftp.test()
            Clock.schedule_once(lambda dt: self._simple_dialog("النتيجة", msg), 0)
        threading.Thread(target=_task, daemon=True).start()

    def _load_settings_ui(self):
        s = self.root.get_screen("settings").ids
        s.ftp_host.text = self.ftp_config.get("host","")
        s.ftp_port.text = str(self.ftp_config.get("port","21"))
        s.ftp_user.text = self.ftp_config.get("user","")
        s.ftp_password.text = self.ftp_config.get("password","")
        s.ftp_directory.text = self.ftp_config.get("directory","")
        s.ftp_filename.text = self.ftp_config.get("filename","")

if __name__ == "__main__":
    ContactApp().run()
