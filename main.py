"""
FTP Contact Manager - Fixed Version
مدير جهات الاتصال عبر FTP - نسخة مصلحة
مبني بـ Kivy + KivyMD لدعم الموبايل
"""
import io
import csv
import json
import os
import threading
import time
from ftplib import FTP, error_perm
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.core.window import Window
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList, TwoLineAvatarIconListItem, IconRightWidget, IconLeftWidget
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.chip import MDChip
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.core.text import LabelBase

# --- تسجيل الخط العربي ---
FONT_PATH = "Cairo-Bold.ttf"
if not os.path.exists(FONT_PATH):
    alt_path = os.path.join(os.path.dirname(__file__), "Cairo-Bold.ttf")
    if os.path.exists(alt_path):
        FONT_PATH = alt_path
if os.path.exists(FONT_PATH):
    LabelBase.register(name="Arabic", fn_regular=FONT_PATH)

# ─────────────────────────────────────────────
# تعريف فئات الشاشات (يجب تعريفها قبل تحميل KV)
# ─────────────────────────────────────────────
class HomeScreen(Screen): pass
class AddScreen(Screen): pass
class SearchScreen(Screen): pass
class SettingsScreen(Screen): pass
class FieldsScreen(Screen): pass
class EditScreen(Screen): pass

# ─────────────────────────────────────────────
# إعدادات FTP الافتراضية
# ─────────────────────────────────────────────
DEFAULT_FTP_CONFIG = {
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
SYNC_INTERVAL = 15

# ─────────────────────────────────────────────
# KV Layout
# ─────────────────────────────────────────────
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
            id: sync_bar
            size_hint_y: None
            height: 0
            md_bg_color: app.theme_cls.primary_color
            MDLabel:
                id: sync_label
                text: ""
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                font_style: "Caption"
        MDScrollView:
            id: scroll_view
            on_scroll_y: app.on_scroll_y(self, self.scroll_y)
            MDList:
                id: record_list
                padding: dp(10)
                spacing: dp(10)
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.95, "bottom": 0.05}
        on_release: app.go_to("add")

<AddScreen>:
    name: "add"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إضافة جديد"
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
                hint_text: "ابحث بالاسم أو أي معلومة..."
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
            title: "إدارة الحقول"
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
                MDIconButton:
                    icon: "plus"
                    on_release: app.add_field()
            MDScrollView:
                MDList:
                    id: fields_list
"""

class FTPManager:
    def __init__(self, config: dict):
        self.config = config

    def _connect(self) -> FTP:
        ftp = FTP()
        ftp.connect(self.config["host"], self.config["port"], timeout=10)
        ftp.login(self.config["user"], self.config["password"])
        if self.config.get("directory"):
            ftp.cwd(self.config["directory"])
        return ftp

    def read_csv(self) -> list[dict]:
        try:
            ftp = self._connect()
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {self.config['filename']}", buf.write)
            ftp.quit()
            buf.seek(0)
            text = buf.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)
        except Exception as e:
            print(f"FTP Read Error: {e}")
            if os.path.exists(LOCAL_CACHE):
                with open(LOCAL_CACHE, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            return []

    def write_csv(self, records: list[dict], fieldnames: list[str]):
        try:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
            
            with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
                f.write(output.getvalue())
                
            ftp = self._connect()
            buf = io.BytesIO(output.getvalue().encode("utf-8"))
            ftp.storbinary(f"STOR {self.config['filename']}", buf)
            ftp.quit()
            return True
        except Exception as e:
            print(f"FTP Write Error: {e}")
            return False

    def test(self) -> str:
        try:
            ftp = self._connect()
            ftp.quit()
            return "تم الاتصال بنجاح ✅"
        except Exception as e:
            return f"فشل الاتصال: {str(e)}"

class ContactApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.records = []
        self.fields = ["الاسم", "السن", "رقم الهاتف"]
        self.ftp_config = DEFAULT_FTP_CONFIG
        self._dirty = False
        self._editing_idx = -1
        self._add_fields_widgets = {}
        self._edit_fields_widgets = {}
        
        self.page_size = 10
        self.current_displayed_count = 0
        self.is_loading_more = False

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(KV)

    def on_start(self):
        self._load_config()
        self._load_fields()
        self._initial_load()
        Clock.schedule_interval(self._auto_sync, SYNC_INTERVAL)

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
                    self.fields = json.load(f)
            except: pass

    def _save_fields(self):
        with open(FIELDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fields, f, ensure_ascii=False, indent=2)

    def go_to(self, screen_name: str):
        self.root.transition = SlideTransition(direction="left" if screen_name != "home" else "right")
        self.root.current = screen_name
        if screen_name == "settings":
            self._load_settings_ui()
        elif screen_name == "fields":
            self._refresh_fields_ui()
        elif screen_name == "add":
            self._build_add_form()
        elif screen_name == "home":
            self.current_displayed_count = 0
            self._refresh_home_list()

    def _initial_load(self):
        self._set_sync_label("⏳ جاري التحميل...")
        def _task():
            recs = self.ftp.read_csv()
            Clock.schedule_once(lambda dt: self._after_load(recs), 0)
        threading.Thread(target=_task, daemon=True).start()

    def _after_load(self, recs):
        self.records = recs
        self.current_displayed_count = 0
        self._refresh_home_list()
        self._set_sync_label("")

    def _refresh_home_list(self, append=False):
        lst = self.root.get_screen("home").ids.record_list
        if not append:
            lst.clear_widgets()
            self.current_displayed_count = 0
            
        if not self.records:
            if not append:
                lst.add_widget(MDLabel(text="لا توجد سجلات", halign="center", height=dp(60), size_hint_y=None))
            return

        start = self.current_displayed_count
        end = min(start + self.page_size, len(self.records))
        
        checkbox_fields = [f for f in self.fields if f not in ["الاسم", "السن", "رقم الهاتف"]]
        
        for i in range(start, end):
            rec = self.records[i]
            item_box = self._create_record_item(i, rec, checkbox_fields)
            lst.add_widget(item_box)
            lst.add_widget(MDCard(height=dp(1), size_hint_y=None, elevation=0, md_bg_color=[0,0,0,0.1]))
            
        self.current_displayed_count = end
        self.is_loading_more = False

    def _create_record_item(self, i, rec, checkbox_fields):
        item_box = MDBoxLayout(orientation="vertical", adaptive_height=True, padding=[dp(16), dp(8)], spacing=dp(4))
        
        top_row = MDBoxLayout(adaptive_height=True, spacing=dp(10))
        info_box = MDBoxLayout(orientation="vertical", adaptive_height=True)
        info_box.add_widget(MDLabel(text=rec.get("الاسم", "بدون اسم"), font_style="H6", adaptive_height=True))
        
        base_info = []
        if rec.get("السن"): base_info.append(f"السن: {rec['السن']}")
        if rec.get("رقم الهاتف"): base_info.append(f"الهاتف: {rec['رقم الهاتف']}")
        if base_info:
            info_box.add_widget(MDLabel(text=" | ".join(base_info), font_style="Caption", theme_text_color="Secondary", adaptive_height=True))
        
        top_row.add_widget(info_box)
        
        actions_box = MDBoxLayout(adaptive_size=True, spacing=dp(4))
        edit_btn = MDIconButton(icon="pencil", theme_text_color="Primary")
        edit_btn.bind(on_release=lambda x, idx=i: self.go_to_edit(idx))
        actions_box.add_widget(edit_btn)
        
        del_btn = MDIconButton(icon="delete", theme_text_color="Error")
        del_btn.bind(on_release=lambda x, idx=i: self._delete_record(idx))
        actions_box.add_widget(del_btn)
        
        top_row.add_widget(actions_box)
        item_box.add_widget(top_row)
        
        if checkbox_fields:
            chips_box = MDBoxLayout(adaptive_height=True, spacing=dp(8), padding=[0, dp(4)])
            for field in checkbox_fields:
                cb_row = MDBoxLayout(adaptive_size=True, spacing=dp(2))
                cb = MDCheckbox(active=rec.get(field, "") == field, size_hint=(None, None), size=(dp(32), dp(32)))
                cb.bind(active=lambda instance, value, r_idx=i, f_name=field: self._on_checkbox_active(r_idx, f_name, value))
                cb_row.add_widget(cb)
                cb_row.add_widget(MDLabel(text=field, font_style="Caption", adaptive_size=True))
                chips_box.add_widget(cb_row)
            item_box.add_widget(chips_box)
            
        return item_box

    def on_scroll_y(self, scrollview, value):
        if value < 0.1 and not self.is_loading_more and self.current_displayed_count < len(self.records):
            self.is_loading_more = True
            self._refresh_home_list(append=True)

    def _on_checkbox_active(self, record_idx, field_name, is_active):
        if 0 <= record_idx < len(self.records):
            self.records[record_idx][field_name] = field_name if is_active else ""
            self._dirty = True
            threading.Thread(target=self._upload_now, daemon=True).start()

    def _build_add_form(self):
        box = self.root.get_screen("add").ids.fields_box
        for w in list(box.children):
            if isinstance(w, MDTextField):
                box.remove_widget(w)
        
        self._add_fields_widgets = {}
        base_fields = ["الاسم", "السن", "رقم الهاتف"]
        for field in reversed(self.fields):
            if field in base_fields:
                is_required = field in ["الاسم", "السن"]
                tf = MDTextField(
                    hint_text=field + (" (مطلوب)" if is_required else " (اختياري)"),
                    mode="rectangle", required=is_required,
                    input_filter="int" if "السن" in field or "هاتف" in field else None
                )
                self._add_fields_widgets[field] = tf
                box.add_widget(tf, index=len(box.children))

    def save_record(self):
        new_rec = {}
        for field, widget in self._add_fields_widgets.items():
            val = widget.text.strip()
            if widget.required and not val:
                self._snack(f"الحقل {field} مطلوب")
                return
            new_rec[field] = val
        
        for field in self.fields:
            if field not in new_rec:
                new_rec[field] = ""
                
        self.records.insert(0, new_rec)
        self._dirty = True
        self._upload_now()
        self.go_to("home")
        self._snack("تمت الإضافة بنجاح")

    def go_to_edit(self, idx: int):
        self._editing_idx = idx
        rec = self.records[idx]
        self.go_to("edit")
        box = self.root.get_screen("edit").ids.edit_fields_box
        
        for w in list(box.children):
            if isinstance(w, MDTextField):
                box.remove_widget(w)
                
        self._edit_fields_widgets = {}
        base_fields = ["الاسم", "السن", "رقم الهاتف"]
        for field in reversed(self.fields):
            if field in base_fields:
                tf = MDTextField(
                    hint_text=field, mode="rectangle",
                    text=str(rec.get(field, "")),
                    input_filter="int" if "السن" in field or "هاتف" in field else None
                )
                self._edit_fields_widgets[field] = tf
                box.add_widget(tf, index=len(box.children))

    def update_record(self):
        if self._editing_idx == -1: return
        rec = self.records[self._editing_idx]
        for field, widget in self._edit_fields_widgets.items():
            rec[field] = widget.text.strip()
        self._dirty = True
        self._upload_now()
        self.go_to("home")
        self._snack("تم التحديث بنجاح")

    def _delete_record(self, idx: int):
        def _do_delete(x):
            self.records.pop(idx)
            self._dirty = True
            self._upload_now()
            self._refresh_home_list()
            dialog.dismiss()
        
        dialog = MDDialog(
            text="هل أنت متأكد من حذف هذا السجل؟",
            buttons=[
                MDFlatButton(text="إلغاء", on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(text="حذف", md_bg_color="red", on_release=_do_delete),
            ],
        )
        dialog.open()

    def _upload_now(self):
        if not self._dirty: return
        def _task():
            if self.ftp.write_csv(self.records, self.fields):
                self._dirty = False
                Clock.schedule_once(lambda dt: self._set_sync_label("✅ تم المزامنة"), 0)
                Clock.schedule_once(lambda dt: self._set_sync_label(""), 3)
        threading.Thread(target=_task, daemon=True).start()

    def _auto_sync(self, dt):
        if not self._dirty:
            threading.Thread(target=self._sync_from_ftp, daemon=True).start()

    def _sync_from_ftp(self):
        recs = self.ftp.read_csv()
        if recs and recs != self.records:
            self.records = recs
            Clock.schedule_once(lambda dt: self._refresh_home_list(), 0)

    def _set_sync_label(self, text: str):
        lbl = self.root.get_screen("home").ids.sync_label
        bar = self.root.get_screen("home").ids.sync_bar
        lbl.text = text
        bar.height = dp(20) if text else 0

    def do_search(self, query: str):
        lst = self.root.get_screen("search").ids.search_list
        lst.clear_widgets()
        if not query: return
        q = query.lower()
        results = [r for r in self.records if any(q in str(v).lower() for v in r.values())]
        
        for rec in results[:20]:
            primary = rec.get("الاسم", "")
            secondary = f"السن: {rec.get('السن', '')} | الهاتف: {rec.get('رقم الهاتف', '')}"
            item = TwoLineAvatarIconListItem(text=primary, secondary_text=secondary)
            lst.add_widget(item)

    def _refresh_fields_ui(self, *args):
        lst = self.root.get_screen("fields").ids.fields_list
        lst.clear_widgets()
        for field in self.fields:
            is_base = field in ["الاسم", "السن", "رقم الهاتف"]
            item = TwoLineAvatarIconListItem(text=field, secondary_text="أساسي" if is_base else "إضافي")
            if not is_base:
                del_btn = IconRightWidget(icon="delete")
                del_btn.bind(on_release=lambda x, f=field: self._remove_field(f))
                item.add_widget(del_btn)
            lst.add_widget(item)

    def add_field(self):
        inp = self.root.get_screen("fields").ids.new_field_input
        name = inp.text.strip()
        if name and name not in self.fields:
            self.fields.append(name)
            for r in self.records: r[name] = ""
            self._save_fields()
            inp.text = ""
            self._refresh_fields_ui()

    def _remove_field(self, name: str):
        if name in self.fields and name not in ["الاسم", "السن", "رقم الهاتف"]:
            self.fields.remove(name)
            for r in self.records: r.pop(name, None)
            self._save_fields()
            self._refresh_fields_ui()

    def _load_settings_ui(self):
        ids = self.root.get_screen("settings").ids
        for key in ["host", "port", "user", "password", "directory", "filename"]:
            getattr(ids, f"ftp_{key}").text = str(self.ftp_config.get(key, ""))

    def save_settings(self):
        ids = self.root.get_screen("settings").ids
        self.ftp_config = {k: getattr(ids, f"ftp_{k}").text.strip() for k in ["host", "user", "password", "directory", "filename"]}
        self.ftp_config["port"] = int(ids.ftp_port.text or 21)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.ftp_config, f, ensure_ascii=False, indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم الحفظ ✅")

    def test_connection(self):
        def _test():
            res = self.ftp.test()
            Clock.schedule_once(lambda dt: self._snack(res), 0)
        threading.Thread(target=_test, daemon=True).start()

    def _snack(self, text: str):
        Snackbar(text=text).open()

if __name__ == "__main__":
    ContactApp().run()
