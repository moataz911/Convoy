"""
FTP Contact Manager
مدير جهات الاتصال عبر FTP
مبني بـ Kivy + KivyMD لدعم الموبايل

تثبيت المكتبات:
    pip install kivy kivymd

للأندرويد: استخدم Buildozer
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
SYNC_INTERVAL = 15  # ثانية

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

<HomeScreen>:
    name: "home"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "مدير جهات الاتصال"
            right_action_items:
                [
                ["magnify", lambda x: app.go_to("search")],
                ["cog", lambda x: app.go_to("settings")],
                ]
            left_action_items: [["format-list-bulleted", lambda x: app.go_to("fields")]]
            elevation: 4
        MDBoxLayout:
            id: sync_bar
            size_hint_y: None
            height: dp(30)
            padding: dp(8), dp(2)
            spacing: dp(8)
            MDLabel:
                id: sync_label
                text: "جاري المزامنة..."
                font_size: "12sp"
                halign: "right"
                theme_text_color: "Secondary"
        ScrollView:
            MDList:
                id: record_list
        MDFloatingActionButton:
            icon: "plus"
            pos_hint: {"center_x": .5, "y": .02}
            elevation: 6
            on_release: app.go_to("add")

<AddScreen>:
    name: "add"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إضافة سجل جديد"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        ScrollView:
            MDBoxLayout:
                id: fields_box
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(10)
                size_hint_y: None
                height: self.minimum_height
        MDBoxLayout:
            size_hint_y: None
            height: dp(72)
            padding: dp(16), dp(8)
            spacing: dp(12)
            MDRaisedButton:
                text: "حفظ وإرسال"
                size_hint_x: 1
                on_release: app.save_record()

<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "البحث"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        MDBoxLayout:
            size_hint_y: None
            height: dp(72)
            padding: dp(16), dp(8)
            MDTextField:
                id: search_input
                hint_text: "ابحث باسم أو أي حقل..."
                on_text: app.do_search(self.text)
                mode: "rectangle"
        ScrollView:
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
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(10)
                size_hint_y: None
                height: self.minimum_height
                MDTextField:
                    id: ftp_host
                    hint_text: "عنوان الخادم (Host)"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_port
                    hint_text: "المنفذ (Port)"
                    input_filter: "int"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_user
                    hint_text: "اسم المستخدم"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_password
                    hint_text: "كلمة المرور"
                    password: True
                    mode: "rectangle"
                MDTextField:
                    id: ftp_directory
                    hint_text: "المجلد"
                    mode: "rectangle"
                MDTextField:
                    id: ftp_filename
                    hint_text: "اسم الملف (مثل: moja.csv)"
                    mode: "rectangle"
                MDRaisedButton:
                    text: "اختبار الاتصال"
                    on_release: app.test_connection()
                    size_hint_x: 1
                MDRaisedButton:
                    text: "حفظ الإعدادات"
                    on_release: app.save_settings()
                    size_hint_x: 1

<FieldsScreen>:
    name: "fields"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "إدارة الحقول"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        ScrollView:
            MDList:
                id: fields_list
        MDBoxLayout:
            size_hint_y: None
            height: dp(72)
            padding: dp(16), dp(8)
            spacing: dp(12)
            MDTextField:
                id: new_field_input
                hint_text: "اسم الحقل الجديد"
                mode: "rectangle"
            MDRaisedButton:
                text: "إضافة"
                on_release: app.add_field()
"""


# ─────────────────────────────────────────────
# FTP Manager
# ─────────────────────────────────────────────
class FTPManager:
    def __init__(self, config: dict):
        self.config = config
        self._lock = threading.Lock()

    def _connect(self) -> FTP:
        ftp = FTP()
        ftp.connect(self.config["host"], int(self.config["port"]))
        ftp.login(self.config["user"], self.config["password"])
        ftp.cwd(self.config["directory"])
        return ftp

    def read_csv(self) -> list[dict]:
        """اقرأ CSV من FTP وأرجع قائمة من القواميس"""
        with self._lock:
            try:
                buf = io.BytesIO()
                ftp = self._connect()
                ftp.retrbinary(f"RETR {self.config['filename']}", buf.write)
                ftp.quit()
                content = buf.getvalue().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(content))
                return list(reader)
            except error_perm:
                return []
            except Exception as e:
                raise e

    def write_csv(self, records: list[dict], fieldnames: list[str]):
        """اكتب قائمة السجلات كاملة إلى FTP"""
        with self._lock:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
            data = buf.getvalue().encode("utf-8-sig")
            ftp = self._connect()
            ftp.storbinary(f"STOR {self.config['filename']}", io.BytesIO(data))
            ftp.quit()

    def test(self) -> str:
        try:
            ftp = self._connect()
            files = ftp.nlst()
            ftp.quit()
            return f"✅ اتصال ناجح\nالملفات: {', '.join(files[:5])}"
        except Exception as e:
            return f"❌ فشل الاتصال: {e}"


# ─────────────────────────────────────────────
# Screens
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────
class ContactApp(MDApp):

    def build(self):
        self.title = "مدير جهات الاتصال"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Light"

        self._load_config()
        self._load_fields()

        self.ftp = FTPManager(self.ftp_config)
        self.records: list[dict] = []
        self._dirty = False  # هل يوجد تغييرات لم ترفع بعد؟

        root = Builder.load_string(KV)
        return root

    def on_start(self):
        self._load_settings_ui()
        self._refresh_fields_ui()
        # اقرأ البيانات من FTP في الخلفية
        threading.Thread(target=self._initial_load, daemon=True).start()
        # مزامنة تلقائية كل SYNC_INTERVAL ثانية
        Clock.schedule_interval(self._auto_sync, SYNC_INTERVAL)

    # ── Config ──────────────────────────────
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.ftp_config = json.load(f)
        else:
            self.ftp_config = DEFAULT_FTP_CONFIG.copy()

    def _load_fields(self):
        if os.path.exists(FIELDS_FILE):
            with open(FIELDS_FILE, "r", encoding="utf-8") as f:
                self.fields: list[str] = json.load(f)
        else:
            self.fields = ["الاسم", "رقم الهاتف"]
            self._save_fields()

    def _save_fields(self):
        with open(FIELDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fields, f, ensure_ascii=False)

    # ── Navigation ───────────────────────────
    def go_to(self, screen_name: str):
        sm: ScreenManager = self.root
        sm.transition = SlideTransition(direction="right" if screen_name == "home" else "left")
        sm.current = screen_name
        if screen_name == "add":
            self._build_add_form()
        elif screen_name == "search":
            self.root.get_screen("search").ids.search_list.clear_widgets()

    # ── Records ──────────────────────────────
    def _initial_load(self):
        try:
            self._set_sync_label("جاري تحميل البيانات...")
            data = self.ftp.read_csv()
            # دمج الحقول من CSV مع حقولنا المحددة
            if data:
                csv_fields = list(data[0].keys())
                for f in csv_fields:
                    if f and f not in self.fields:
                        self.fields.append(f)
                self._save_fields()
            self.records = data
            Clock.schedule_once(lambda dt: self._refresh_home_list(), 0)
            Clock.schedule_once(lambda dt: self._set_sync_label("آخر مزامنة: الآن"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._set_sync_label(f"خطأ: {e}"), 0)

    def _refresh_home_list(self):
        lst = self.root.get_screen("home").ids.record_list
        lst.clear_widgets()
        if not self.records:
            lst.add_widget(MDLabel(
                text="لا توجد سجلات بعد. اضغط + لإضافة جديد",
                halign="center",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(60),
            ))
            return
        first_field = self.fields[0] if self.fields else "الاسم"
        second_field = self.fields[1] if len(self.fields) > 1 else ""
        for i, rec in enumerate(self.records):
            primary = rec.get(first_field, "")
            secondary = rec.get(second_field, "") if second_field else ""
            # ملخص بقية الحقول
            extras = ", ".join(
                f"{k}: {v}" for k, v in rec.items()
                if k not in (first_field, second_field) and v
            )
            if extras:
                secondary = f"{secondary}  |  {extras}" if secondary else extras

            item = TwoLineAvatarIconListItem(
                text=primary,
                secondary_text=secondary,
            )
            del_btn = IconRightWidget(icon="delete")
            idx = i
            del_btn.bind(on_release=lambda x, n=idx: self._delete_record(n))
            item.add_widget(del_btn)
            lst.add_widget(item)

    def _build_add_form(self):
        box = self.root.get_screen("add").ids.fields_box
        box.clear_widgets()
        self._add_fields_widgets = {}
        for field in self.fields:
            tf = MDTextField(
                hint_text=field,
                mode="rectangle",
                size_hint_y=None,
                height=dp(56),
            )
            self._add_fields_widgets[field] = tf
            box.add_widget(tf)

    def save_record(self):
        rec = {}
        for field, widget in self._add_fields_widgets.items():
            rec[field] = widget.text.strip()

        # تحقق أن الحقل الأول ليس فارغاً
        first = self.fields[0] if self.fields else "الاسم"
        if not rec.get(first):
            self._snack(f"يرجى إدخال {first}")
            return

        self.records.append(rec)
        self._dirty = True
        # ارفع فوراً في الخلفية
        threading.Thread(target=self._upload_now, daemon=True).start()
        self._snack("تم الحفظ والإرسال ✅")
        self.go_to("home")
        Clock.schedule_once(lambda dt: self._refresh_home_list(), 0.2)

    def _delete_record(self, idx: int):
        if 0 <= idx < len(self.records):
            self.records.pop(idx)
            self._dirty = True
            threading.Thread(target=self._upload_now, daemon=True).start()
            self._refresh_home_list()
            self._snack("تم الحذف")

    # ── Upload ───────────────────────────────
    def _upload_now(self):
        try:
            self._set_sync_label("⬆ جاري الرفع...")
            self.ftp.write_csv(self.records, self.fields)
            self._dirty = False
            Clock.schedule_once(lambda dt: self._set_sync_label("✅ تمت المزامنة"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._set_sync_label(f"❌ {e}"), 0)

    def _auto_sync(self, dt):
        if self._dirty:
            threading.Thread(target=self._upload_now, daemon=True).start()
        else:
            threading.Thread(target=self._sync_from_ftp, daemon=True).start()

    def _sync_from_ftp(self):
        try:
            self._set_sync_label("🔄 مزامنة...")
            data = self.ftp.read_csv()
            self.records = data
            Clock.schedule_once(lambda dt: self._refresh_home_list(), 0)
            Clock.schedule_once(lambda dt: self._set_sync_label("✅ محدّث"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._set_sync_label(f"خطأ: {e}"), 0)

    def _set_sync_label(self, text: str):
        try:
            self.root.get_screen("home").ids.sync_label.text = text
        except Exception:
            pass

    # ── Search ───────────────────────────────
    def do_search(self, query: str):
        lst = self.root.get_screen("search").ids.search_list
        lst.clear_widgets()
        if not query:
            return
        q = query.lower()
        results = [
            r for r in self.records
            if any(q in str(v).lower() for v in r.values())
        ]
        if not results:
            lst.add_widget(MDLabel(
                text="لا نتائج",
                halign="center",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(60),
            ))
            return
        first_field = self.fields[0] if self.fields else "الاسم"
        second_field = self.fields[1] if len(self.fields) > 1 else ""
        for rec in results:
            primary = rec.get(first_field, "")
            secondary = "  |  ".join(
                f"{k}: {v}" for k, v in rec.items() if k != first_field and v
            )
            item = TwoLineAvatarIconListItem(
                text=primary,
                secondary_text=secondary,
            )
            lst.add_widget(item)

    # ── Fields Management ────────────────────
    def _refresh_fields_ui(self, *args):
        try:
            lst = self.root.get_screen("fields").ids.fields_list
        except Exception:
            return
        lst.clear_widgets()
        for i, field in enumerate(self.fields):
            item = TwoLineAvatarIconListItem(
                text=field,
                secondary_text="الحقل الأول (مطلوب)" if i == 0 else "حقل اختياري",
            )
            if i > 0:
                del_btn = IconRightWidget(icon="delete")
                name = field
                del_btn.bind(on_release=lambda x, n=name: self._remove_field(n))
                item.add_widget(del_btn)
            lst.add_widget(item)

    def add_field(self):
        inp = self.root.get_screen("fields").ids.new_field_input
        name = inp.text.strip()
        if not name:
            self._snack("أدخل اسم الحقل")
            return
        if name in self.fields:
            self._snack("الحقل موجود بالفعل")
            return
        self.fields.append(name)
        self._save_fields()
        inp.text = ""
        self._refresh_fields_ui()
        self._snack(f"تمت إضافة حقل: {name}")

    def _remove_field(self, name: str):
        if name in self.fields:
            self.fields.remove(name)
            self._save_fields()
            self._refresh_fields_ui()
            self._snack(f"تم حذف الحقل: {name}")

    # ── Settings ─────────────────────────────
    def _load_settings_ui(self):
        ids = self.root.get_screen("settings").ids
        ids.ftp_host.text = self.ftp_config.get("host", "")
        ids.ftp_port.text = str(self.ftp_config.get("port", 21))
        ids.ftp_user.text = self.ftp_config.get("user", "")
        ids.ftp_password.text = self.ftp_config.get("password", "")
        ids.ftp_directory.text = self.ftp_config.get("directory", "")
        ids.ftp_filename.text = self.ftp_config.get("filename", "moja.csv")

    def save_settings(self):
        ids = self.root.get_screen("settings").ids
        self.ftp_config = {
            "host": ids.ftp_host.text.strip(),
            "port": int(ids.ftp_port.text.strip() or 21),
            "user": ids.ftp_user.text.strip(),
            "password": ids.ftp_password.text.strip(),
            "directory": ids.ftp_directory.text.strip(),
            "filename": ids.ftp_filename.text.strip() or "moja.csv",
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.ftp_config, f, ensure_ascii=False, indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("تم حفظ الإعدادات ✅")
        self.go_to("home")

    def test_connection(self):
        ids = self.root.get_screen("settings").ids
        config = {
            "host": ids.ftp_host.text.strip(),
            "port": int(ids.ftp_port.text.strip() or 21),
            "user": ids.ftp_user.text.strip(),
            "password": ids.ftp_password.text.strip(),
            "directory": ids.ftp_directory.text.strip(),
            "filename": ids.ftp_filename.text.strip() or "moja.csv",
        }
        def _test():
            result = FTPManager(config).test()
            Clock.schedule_once(lambda dt: self._snack(result), 0)
        threading.Thread(target=_test, daemon=True).start()
        self._snack("⏳ جاري الاختبار...")

    # ── Helpers ──────────────────────────────
    def _snack(self, text: str):
        Snackbar(text=text, snackbar_x="8dp", snackbar_y="8dp", size_hint_x=0.95).open()


# ─────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # حجم نافذة يشبه الموبايل عند التشغيل على الكمبيوتر
    Window.size = (400, 750)
    ContactApp().run()
