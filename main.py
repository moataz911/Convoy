"""
FTP Contact Manager
مدير جهات الاتصال عبر FTP - يدعم حقول النص والاختيار والقائمة المتعددة
متوافق مع KivyMD 1.2.0
"""
import io, csv, json, os, threading
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

for _p in ["Cairo-Bold.ttf", os.path.join(os.path.dirname(__file__), "Cairo-Bold.ttf")]:
    if os.path.exists(_p):
        LabelBase.register(name="Arabic", fn_regular=_p)
        break

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

KV = """
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
            title: "مدير جهات الاتصال"
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
            title: "اضافة جديد"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_add
            size_hint_y: None
            height: 0
            md_bg_color: 1, 0.2, 0.2, 1
            padding: dp(10)
            MDLabel:
                text: "غير متصل بسيرفر FTP - لا يمكن الحفظ"
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                font_style: "Caption"
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: fields_box
                padding: dp(20)
                spacing: dp(15)
                adaptive_height: True
                MDRaisedButton:
                    text: "حفظ السجل"
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.8
                    on_release: app.save_record()

<EditScreen>:
    name: "edit"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "تعديل السجل"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            id: ftp_warning_edit
            size_hint_y: None
            height: 0
            md_bg_color: 1, 0.2, 0.2, 1
            padding: dp(10)
            MDLabel:
                text: "غير متصل بسيرفر FTP - لا يمكن الحفظ"
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                font_style: "Caption"
        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                id: edit_fields_box
                padding: dp(20)
                spacing: dp(15)
                adaptive_height: True
                MDRaisedButton:
                    text: "تحديث البيانات"
                    pos_hint: {"center_x": 0.5}
                    size_hint_x: 0.8
                    on_release: app.update_record()

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
            padding: dp(10)
            spacing: dp(10)
            MDTextField:
                id: search_input
                hint_text: "ابحث بالاسم او اي معلومة..."
                on_text: app.do_search(self.text)
            MDScrollView:
                MDList:
                    id: search_list

<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "اعدادات FTP"
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
                        text: "حفظ"
                        on_release: app.save_settings()
                    MDFlatButton:
                        text: "اختبار الاتصال"
                        on_release: app.test_connection()

<FieldsScreen>:
    name: "fields"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "ادارة الحقول"
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
                    hint_text: "اسم الحقل الجديد"
                    size_hint_x: 0.5
                MDTextField:
                    id: field_type_input
                    hint_text: "النوع: text/checkbox/multiselect"
                    size_hint_x: 0.5
            MDBoxLayout:
                adaptive_height: True
                spacing: dp(5)
                MDTextField:
                    id: field_options_input
                    hint_text: "خيارات القائمة: خيار1,خيار2,خيار3"
                MDIconButton:
                    icon: "plus"
                    on_release: app.add_field()
            MDScrollView:
                MDList:
                    id: fields_list
"""

# ─── helpers ──────────────────────────────────────────────
def parse_multi(value: str) -> list:
    return [v for v in (value or "").split("|") if v]

def serialize_multi(selected: list) -> str:
    return "|".join(selected)

# ─── FTP Manager ──────────────────────────────────────────
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
            print(f"FTP Read Error: {e}")
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
            print(f"FTP Write Error: {e}")
            return False

# ─── App ──────────────────────────────────────────────────
class ContactApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.records   = []
        # fields: list of dicts {name, type, required, options:[]}
        self.fields    = [
            {"name":"الاسم","type":"text","required":True},
            {"name":"السن","type":"text","required":False},
            {"name":"رقم الهاتف","type":"text","required":False},
        ]
        self.ftp_config   = dict(DEFAULT_FTP_CONFIG)
        self._dirty       = False
        self._editing_idx = -1
        self._add_widgets   = {}   # name -> widget(s)
        self._edit_widgets  = {}
        self._ftp_ok      = False
        self._page_size   = 20
        self._displayed   = 0
        self._loading_more = False

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(KV)

    def on_start(self):
        self._load_config()
        self._load_fields()
        self._initial_load()
        Clock.schedule_interval(self._auto_sync, 15)
        Clock.schedule_interval(self._periodic_check, 10)

    # ── Config ────────────────────────────────────────────
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
                # دعم الصيغة القديمة (list of strings)
                if data and isinstance(data[0], str):
                    self.fields = [{"name": n, "type": "text", "required": False} for n in data]
                else:
                    self.fields = data
            except: pass

    def _save_fields(self):
        with open(FIELDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fields, f, ensure_ascii=False, indent=2)

    def _field_names(self):
        return [fd["name"] for fd in self.fields]

    def _get_field(self, name):
        return next((fd for fd in self.fields if fd["name"] == name), None)

    # ── Notification ──────────────────────────────────────
    def _snack(self, text: str):
        def _show(dt):
            try:
                from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
                MDSnackbar(MDSnackbarText(text=text),
                           y=dp(24), pos_hint={"center_x": 0.5},
                           size_hint_x=0.9, duration=3).open()
            except (ImportError, TypeError):
                try:
                    from kivymd.uix.snackbar import Snackbar
                    s = Snackbar(); s.text = text; s.open()
                except Exception:
                    self._simple_dialog("رسالة", text)
        Clock.schedule_once(_show, 0)

    def _simple_dialog(self, title, text):
        try:
            d = MDDialog(title=title, text=text,
                         buttons=[MDFlatButton(text="حسناً", on_release=lambda x: d.dismiss())])
            d.open()
        except Exception: print(f"[{title}] {text}")

    # ── FTP status ────────────────────────────────────────
    def _periodic_check(self, dt):
        prev = self._ftp_ok
        def _check():
            ok, _ = self.ftp.test()
            def _update(dt2):
                self._ftp_ok = ok
                if prev and not ok: self._snack("انقطع الاتصال بسيرفر FTP")
                self._refresh_status_bars()
            Clock.schedule_once(_update, 0)
        threading.Thread(target=_check, daemon=True).start()

    def _refresh_status_bars(self):
        try:
            bar = self.root.get_screen("home").ids.ftp_status_bar
            lbl = self.root.get_screen("home").ids.ftp_status_label
            bar.height = 0 if self._ftp_ok else dp(28)
            lbl.text = "" if self._ftp_ok else "غير متصل بسيرفر FTP"
        except: pass
        h = dp(36) if not self._ftp_ok else 0
        for sn, bid in [("add","ftp_warning_add"),("edit","ftp_warning_edit")]:
            try: self.root.get_screen(sn).ids[bid].height = h
            except: pass

    def _require_ftp(self, callback):
        self._snack("جاري التحقق من الاتصال...")
        def _check():
            ok, msg = self.ftp.test()
            def _done(dt):
                self._ftp_ok = ok
                self._refresh_status_bars()
                if ok: callback()
                else: self._show_no_ftp_dialog(msg)
            Clock.schedule_once(_done, 0)
        threading.Thread(target=_check, daemon=True).start()

    def _show_no_ftp_dialog(self, msg=""):
        try:
            d = MDDialog(
                title="غير متصل بالسيرفر",
                text=f"لا يمكن حفظ البيانات.\nيجب الاتصال بسيرفر FTP اولاً.\n\n{msg}",
                buttons=[
                    MDRaisedButton(text="اعدادات FTP",
                                   on_release=lambda x: (d.dismiss(), self.go_to("settings"))),
                    MDFlatButton(text="اغلاق", on_release=lambda x: d.dismiss()),
                ])
            d.open()
        except Exception: self._snack(f"خطأ: {msg}")

    # ── Navigation ────────────────────────────────────────
    def go_to(self, name: str):
        self.root.transition = SlideTransition(
            direction="left" if name != "home" else "right")
        self.root.current = name
        if name == "settings":   self._load_settings_ui()
        elif name == "fields":   self._refresh_fields_ui()
        elif name == "add":      self._build_add_form(); self._refresh_status_bars()
        elif name == "edit":     self._refresh_status_bars()
        elif name == "home":     self._displayed = 0; self._refresh_list()

    # ── Load ──────────────────────────────────────────────
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
                if not ok: self._snack(f"تعذر الاتصال: {msg}")
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

    # ── List ──────────────────────────────────────────────
    def _refresh_list(self, append=False):
        lst = self.root.get_screen("home").ids.record_list
        if not append:
            lst.clear_widgets(); self._displayed = 0
        if not self.records:
            if not append:
                lst.add_widget(MDLabel(text="لا توجد سجلات", halign="center",
                                       height=dp(60), size_hint_y=None))
            return
        start, end = self._displayed, min(self._displayed + self._page_size, len(self.records))
        for i in range(start, end):
            lst.add_widget(self._make_item(i, self.records[i]))
            lst.add_widget(MDCard(height=dp(1), size_hint_y=None, elevation=0,
                                  md_bg_color=[0,0,0,0.1]))
        self._displayed = end
        self._loading_more = False

    def _make_item(self, i, rec):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True,
                          padding=[dp(14), dp(8)], spacing=dp(4))
        row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        info = MDBoxLayout(orientation="vertical", adaptive_height=True)
        info.add_widget(MDLabel(text=rec.get("الاسم","بدون اسم"),
                                font_style="H6", adaptive_height=True))
        details = " | ".join(filter(None, [
            f"السن: {rec['السن']}" if rec.get("السن") else "",
            f"الهاتف: {rec['رقم الهاتف']}" if rec.get("رقم الهاتف") else "",
        ]))
        if details:
            info.add_widget(MDLabel(text=details, font_style="Caption",
                                    theme_text_color="Secondary", adaptive_height=True))
        row.add_widget(info)
        btns = MDBoxLayout(adaptive_size=True, spacing=dp(2))
        eb = MDIconButton(icon="pencil", theme_text_color="Primary")
        eb.bind(on_release=lambda x, idx=i: self.go_to_edit(idx))
        db = MDIconButton(icon="delete", theme_text_color="Error")
        db.bind(on_release=lambda x, idx=i: self._confirm_delete(idx))
        btns.add_widget(eb); btns.add_widget(db)
        row.add_widget(btns)
        box.add_widget(row)

        # عرض حقول الاختيار المتعدد
        for fd in self.fields:
            if fd["type"] == "multiselect":
                selected = parse_multi(rec.get(fd["name"], ""))
                if selected:
                    chips_row = MDBoxLayout(adaptive_height=True, spacing=dp(4), padding=[0, dp(2)])
                    chips_row.add_widget(MDLabel(text=f'{fd["name"]}: ',
                                                 font_style="Caption", adaptive_size=True,
                                                 theme_text_color="Secondary"))
                    for opt in selected:
                        try:
                            chip = MDChip(text=opt)
                            chips_row.add_widget(chip)
                        except Exception:
                            chips_row.add_widget(MDLabel(text=f"[{opt}]",
                                                         font_style="Caption", adaptive_size=True))
                    box.add_widget(chips_row)
        return box

    def on_scroll_y(self, sv, val):
        if val < 0.1 and not self._loading_more and self._displayed < len(self.records):
            self._loading_more = True
            self._refresh_list(append=True)

    # ── Add Form ──────────────────────────────────────────
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
        """إنشاء widget مناسب لنوع الحقل"""
        if fd["type"] == "text":
            tf = MDTextField(
                hint_text=fd["name"] + (" (مطلوب)" if fd.get("required") else ""),
                mode="rectangle",
                text=current_value or "",
            )
            tf.field_type = "text"
            return tf

        elif fd["type"] == "checkbox":
            container = MDBoxLayout(adaptive_height=True, spacing=dp(8),
                                    size_hint_y=None, height=dp(40))
            cb = MDCheckbox(active=(current_value == "true"),
                            size_hint=(None, None), size=(dp(32), dp(32)))
            lbl = MDLabel(text=fd["name"], adaptive_height=True)
            container.add_widget(cb)
            container.add_widget(lbl)
            container.checkbox = cb
            container.field_type = "checkbox"
            return container

        elif fd["type"] == "multiselect":
            container = MDBoxLayout(orientation="vertical", adaptive_height=True,
                                    spacing=dp(6), padding=[0, dp(4)])
            container.add_widget(MDLabel(text=fd["name"], font_style="Subtitle1",
                                         adaptive_height=True))
            selected = parse_multi(current_value)
            options = fd.get("options", [])
            cb_map = {}
            chips_box = MDBoxLayout(adaptive_height=True, spacing=dp(8))
            for opt in options:
                cb_row = MDBoxLayout(adaptive_size=True, spacing=dp(2))
                cb = MDCheckbox(active=(opt in selected),
                                size_hint=(None,None), size=(dp(28),dp(28)))
                cb_row.add_widget(cb)
                cb_row.add_widget(MDLabel(text=opt, font_style="Caption", adaptive_size=True))
                chips_box.add_widget(cb_row)
                cb_map[opt] = cb
            container.add_widget(chips_box)
            container.cb_map    = cb_map
            container.field_type = "multiselect"
            return container
        return None

    def _read_widget_value(self, widget):
        ft = getattr(widget, "field_type", None)
        if ft == "text":     return widget.text.strip()
        if ft == "checkbox": return "true" if widget.checkbox.active else "false"
        if ft == "multiselect":
            return serialize_multi([opt for opt, cb in widget.cb_map.items() if cb.active])
        return ""

    # ── Save / Update ─────────────────────────────────────
    def save_record(self):
        new_rec = {}
        for fd in self.fields:
            name = fd["name"]
            widget = self._add_widgets.get(name)
            val = self._read_widget_value(widget) if widget else ""
            if fd.get("required") and not val:
                self._snack(f"الحقل {name} مطلوب"); return
            new_rec[name] = val

        def _do():
            self.records.insert(0, new_rec); self._dirty = True
            ok = self.ftp.write_csv(self.records, self._field_names())
            if ok:
                self._dirty = False
                Clock.schedule_once(lambda dt: self._snack("تمت الاضافة بنجاح"), 0)
                Clock.schedule_once(lambda dt: self.go_to("home"), 0)
            else:
                self.records.pop(0); self._dirty = False
                Clock.schedule_once(lambda dt: self._show_no_ftp_dialog("فشل رفع الملف"), 0)
        self._require_ftp(_do)

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
        if self._editing_idx == -1: return
        old = dict(self.records[self._editing_idx])
        new_vals = {name: self._read_widget_value(w)
                    for name, w in self._edit_widgets.items()}

        def _do():
            for k, v in new_vals.items(): self.records[self._editing_idx][k] = v
            self._dirty = True
            ok = self.ftp.write_csv(self.records, self._field_names())
            if ok:
                self._dirty = False
                Clock.schedule_once(lambda dt: self._snack("تم التحديث بنجاح"), 0)
                Clock.schedule_once(lambda dt: self.go_to("home"), 0)
            else:
                self.records[self._editing_idx] = old; self._dirty = False
                Clock.schedule_once(lambda dt: self._show_no_ftp_dialog("فشل رفع الملف"), 0)
        self._require_ftp(_do)

    def _confirm_delete(self, idx: int):
        def _do(x):
            d.dismiss()
            def _exec():
                ok, msg = self.ftp.test()
                if not ok:
                    Clock.schedule_once(lambda dt: self._show_no_ftp_dialog(msg), 0); return
                self.records.pop(idx); self._dirty = True
                self.ftp.write_csv(self.records, self._field_names()); self._dirty = False
                Clock.schedule_once(lambda dt: (self._snack("تم الحذف"), self._refresh_list()), 0)
            threading.Thread(target=_exec, daemon=True).start()
        d = MDDialog(
            text="هل انت متاكد من حذف هذا السجل؟",
            buttons=[
                MDFlatButton(text="الغاء", on_release=lambda x: d.dismiss()),
                MDRaisedButton(text="حذف", md_bg_color="red", on_release=_do),
            ])
        d.open()

    # ── Search ────────────────────────────────────────────
    def do_search(self, query: str):
        lst = self.root.get_screen("search").ids.search_list
        lst.clear_widgets()
        if not query: return
        q = query.lower()
        for rec in self.records:
            if any(q in str(v).lower() for v in rec.values()):
                item = TwoLineAvatarIconListItem(
                    text=rec.get("الاسم",""),
                    secondary_text=f"السن: {rec.get('السن','')} | الهاتف: {rec.get('رقم الهاتف','')}",
                )
                lst.add_widget(item)

    # ── Fields Management ─────────────────────────────────
    def _refresh_fields_ui(self, *a):
        lst = self.root.get_screen("fields").ids.fields_list
        lst.clear_widgets()
        for fd in self.fields:
            name = fd["name"]
            tp   = fd.get("type","text")
            opts = fd.get("options",[])
            type_label = {"text":"نصي","checkbox":"اختيار","multiselect":"قائمة متعددة"}.get(tp, tp)
            secondary = type_label
            if tp == "multiselect" and opts:
                secondary += f" · {', '.join(opts[:3])}" + (" ..." if len(opts)>3 else "")
            item = TwoLineAvatarIconListItem(
                text=name,
                secondary_text=secondary + (" · أساسي" if name in BUILTIN else "")
            )
            if name not in BUILTIN:
                btn = IconRightWidget(icon="delete")
                btn.bind(on_release=lambda x, n=name: self._remove_field(n))
                item.add_widget(btn)
            lst.add_widget(item)

    def add_field(self):
        ids     = self.root.get_screen("fields").ids
        name    = ids.new_field_input.text.strip()
        ftype   = ids.field_type_input.text.strip().lower() or "text"
        options_raw = ids.field_options_input.text.strip()

        if not name:
            self._snack("أدخل اسم الحقل"); return
        if any(fd["name"] == name for fd in self.fields):
            self._snack("الحقل موجود بالفعل"); return
        if ftype not in ("text", "checkbox", "multiselect"):
            self._snack("النوع يجب أن يكون: text أو checkbox أو multiselect"); return
        if ftype == "multiselect":
            opts = [o.strip() for o in options_raw.split(",") if o.strip()]
            if len(opts) < 2:
                self._snack("أضف خيارين على الأقل مفصولة بفاصلة"); return
        else:
            opts = []

        new_fd = {"name": name, "type": ftype, "required": False}
        if opts: new_fd["options"] = opts
        self.fields.append(new_fd)
        for r in self.records: r.setdefault(name, "")
        self._save_fields()
        ids.new_field_input.text = ""
        ids.field_type_input.text = ""
        ids.field_options_input.text = ""
        self._refresh_fields_ui()

    def _remove_field(self, name: str):
        if name not in BUILTIN:
            self.fields = [fd for fd in self.fields if fd["name"] != name]
            for r in self.records: r.pop(name, None)
            self._save_fields(); self._refresh_fields_ui()

    # ── Settings ──────────────────────────────────────────
    def _load_settings_ui(self):
        ids = self.root.get_screen("settings").ids
        for k in ["host","port","user","password","directory","filename"]:
            getattr(ids, f"ftp_{k}").text = str(self.ftp_config.get(k,""))

    def save_settings(self):
        ids = self.root.get_screen("settings").ids
        self.ftp_config = {k: getattr(ids, f"ftp_{k}").text.strip()
                           for k in ["host","user","password","directory","filename"]}
        self.ftp_config["port"] = int(ids.ftp_port.text.strip() or 21)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.ftp_config, f, ensure_ascii=False, indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم حفظ الاعدادات")

    def test_connection(self):
        def _task():
            ok, msg = self.ftp.test()
            self._ftp_ok = ok
            Clock.schedule_once(lambda dt: self._snack(msg), 0)
            Clock.schedule_once(lambda dt: self._refresh_status_bars(), 0)
        threading.Thread(target=_task, daemon=True).start()


if __name__ == "__main__":
    ContactApp().run()
