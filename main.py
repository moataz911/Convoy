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
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.core.text import LabelBase

# --- تسجيل الخط العربي ---
# نحاول العثور على الخط في المجلد الحالي لضمان التوافق مع Buildozer
FONT_PATH = "Cairo-Bold.ttf"
if not os.path.exists(FONT_PATH):
    # محاولة مسار بديل إذا كان الكود في مكان مختلف
    alt_path = os.path.join(os.path.dirname(__file__), "Cairo-Bold.ttf")
    if os.path.exists(alt_path):
        FONT_PATH = alt_path

if os.path.exists(FONT_PATH):
    LabelBase.register(name="Arabic", fn_regular=FONT_PATH)
else:
    print(f"Warning: Font file {FONT_PATH} not found. Arabic text might not display correctly.")

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
    EditScreen:

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
                pos_hint: {"center_x": .5}
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
                
<EditScreen>:
    name: "edit"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "تعديل السجل"
            left_action_items: [["arrow-right", lambda x: app.go_to("home")]]
            elevation: 4
        ScrollView:
            MDBoxLayout:
                id: edit_fields_box
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
                text: "تحديث البيانات"
                size_hint_x: 1
                pos_hint: {"center_x": .5}
                on_release: app.update_record()
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

class EditScreen(Screen):
    pass


# ─────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────
class ContactApp(MDApp):

    def build(self):
        if os.path.exists(FONT_PATH):
            self.theme_cls.font_styles["H1"] = ["Arabic", 96, False, 0.15]
            self.theme_cls.font_styles["H2"] = ["Arabic", 60, False, 0.15]
            self.theme_cls.font_styles["H3"] = ["Arabic", 48, False, 0.15]
            self.theme_cls.font_styles["H4"] = ["Arabic", 34, False, 0.15]
            self.theme_cls.font_styles["H5"] = ["Arabic", 24, False, 0.15]
            self.theme_cls.font_styles["H6"] = ["Arabic", 20, False, 0.15]
            self.theme_cls.font_styles["Subtitle1"] = ["Arabic", 16, False, 0.15]
            self.theme_cls.font_styles["Subtitle2"] = ["Arabic", 14, False, 0.15]
            self.theme_cls.font_styles["Body1"] = ["Arabic", 16, False, 0.15]
            self.theme_cls.font_styles["Body2"] = ["Arabic", 14, False, 0.15]
            self.theme_cls.font_styles["Button"] = ["Arabic", 14, True, 0.15]
            self.theme_cls.font_styles["Caption"] = ["Arabic", 12, False, 0.15]
            self.theme_cls.font_styles["Overline"] = ["Arabic", 10, False, 0.15]

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
            self.fields = ["الاسم", "السن", "رقم الهاتف"]
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
        elif screen_name == "edit":
            # سيتم بناؤه عبر go_to_edit
            pass
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
            err_msg = str(e)
            Clock.schedule_once(lambda dt: self._set_sync_label(f"خطأ: {err_msg}"), 0)

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
        # الحقول التي ستظهر كـ Checkbox (أي حقل بعد الاسم والسن ورقم الهاتف)
        checkbox_fields = [f for f in self.fields if f not in ["الاسم", "السن", "رقم الهاتف"]]
        
        for i, rec in enumerate(self.records):
            # إنشاء حاوية للسجل
            item_box = MDBoxLayout(
                orientation="vertical",
                adaptive_height=True,
                padding=[dp(16), dp(8)],
                spacing=dp(4)
            )
            
            # السطر الأول: الاسم والمعلومات الأساسية + زر الحذف
            top_row = MDBoxLayout(adaptive_height=True, spacing=dp(10))
            
            info_box = MDBoxLayout(orientation="vertical", adaptive_height=True)
            primary_text = rec.get("الاسم", "بدون اسم")
            info_box.add_widget(MDLabel(text=primary_text, font_style="H6", adaptive_height=True))
            
            base_info = []
            if rec.get("السن"): base_info.append(f"السن: {rec['السن']}")
            if rec.get("رقم الهاتف"): base_info.append(f"الهاتف: {rec['رقم الهاتف']}")
            if base_info:
                info_box.add_widget(MDLabel(text=" | ".join(base_info), font_style="Caption", theme_text_color="Secondary", adaptive_height=True))
            
            top_row.add_widget(info_box)
            
            # أزرار الإجراءات (تعديل وحذف)
            actions_box = MDBoxLayout(adaptive_size=True, spacing=dp(4))
            
            edit_btn = MDIconButton(icon="pencil", theme_text_color="Primary")
            idx = i
            edit_btn.bind(on_release=lambda x, n=idx: self.go_to_edit(n))
            actions_box.add_widget(edit_btn)
            
            del_btn = MDIconButton(icon="delete", theme_text_color="Error")
            del_btn.bind(on_release=lambda x, n=idx: self._delete_record(n))
            actions_box.add_widget(del_btn)
            
            top_row.add_widget(actions_box)
            
            item_box.add_widget(top_row)
            
            # السطر الثاني: Checkboxes للحقول الإضافية
            if checkbox_fields:
                chips_box = MDBoxLayout(adaptive_height=True, spacing=dp(8), padding=[0, dp(4)])
                for field in checkbox_fields:
                    cb_row = MDBoxLayout(adaptive_size=True, spacing=dp(2))
                    # الـ checkbox يكون مفعل إذا كانت القيمة المخزنة تساوي اسم الحقل
                    cb = MDCheckbox(
                        active=rec.get(field, "") == field,
                        size_hint=(None, None),
                        size=(dp(32), dp(32))
                    )
                    # ربط التغيير بحفظ البيانات
                    cb.bind(active=lambda instance, value, r_idx=i, f_name=field: self._on_checkbox_active(r_idx, f_name, value))
                    
                    cb_row.add_widget(cb)
                    cb_row.add_widget(MDLabel(text=field, font_style="Caption", adaptive_size=True))
                    chips_box.add_widget(cb_row)
                item_box.add_widget(chips_box)
            
            # إضافة فاصل
            lst.add_widget(item_box)
            lst.add_widget(MDCard(height=dp(1), size_hint_y=None, elevation=0, md_bg_color=[0,0,0,0.1]))

    def _on_checkbox_active(self, record_idx, field_name, is_active):
        if 0 <= record_idx < len(self.records):
            # عندما يتم تفعيل الـ checkbox يتم تخزين اسم الحقل، وعند إلغائه يتم مسح القيمة
            self.records[record_idx][field_name] = field_name if is_active else ""
            self._dirty = True
            # لا نحتاج لتحديث الواجهة بالكامل، فقط نرفع التغييرات في الخلفية
            threading.Thread(target=self._upload_now, daemon=True).start()

    def _build_add_form(self):
        box = self.root.get_screen("add").ids.fields_box
        box.clear_widgets()
        self._add_fields_widgets = {}
        # إظهار الحقول الأساسية فقط في شاشة الإضافة (الاسم، السن، الهاتف)
        # أما بقية الحقول فستكون Checkboxes في القائمة الرئيسية
        base_fields = ["الاسم", "السن", "رقم الهاتف"]
        for field in self.fields:
            if field in base_fields:
                is_required = field in ["الاسم", "السن"]
                tf = MDTextField(
                    hint_text=field + (" (مطلوب)" if is_required else " (اختياري)"),
                    mode="rectangle",
                    size_hint_y=None,
                    height=dp(56),
                    required=is_required,
                    helper_text="هذا الحقل مطلوب" if is_required else "",
                    helper_text_mode="on_error",
                    input_filter="int" if "السن" in field or "هاتف" in field or "رقم" in field else None
                )
                self._add_fields_widgets[field] = tf
                box.add_widget(tf)

    def save_record(self):
        rec = {}
        # التحقق من الحقول المطلوبة (الاسم والسن)
        name_val = self._add_fields_widgets.get("الاسم").text.strip() if self._add_fields_widgets.get("الاسم") else ""
        age_val = self._add_fields_widgets.get("السن").text.strip() if self._add_fields_widgets.get("السن") else ""
        
        if not name_val:
            self._snack("يرجى إدخال الاسم")
            return
        if not age_val:
            self._snack("يرجى إدخال السن")
            return

        for field, widget in self._add_fields_widgets.items():
            rec[field] = widget.text.strip()

        # تهيئة بقية الحقول (Checkboxes) كقيم فارغة
        for field in self.fields:
            if field not in rec:
                rec[field] = ""

        self.records.append(rec)
        self._dirty = True
        # ارفع فوراً في الخلفية
        threading.Thread(target=self._upload_now, daemon=True).start()
        self._snack("تم الحفظ والإرسال ✅")
        self.go_to("home")
        Clock.schedule_once(lambda dt: self._refresh_home_list(), 0.2)

    def go_to_edit(self, idx: int):
        if not (0 <= idx < len(self.records)):
            return
        
        self._editing_idx = idx
        rec = self.records[idx]
        
        box = self.root.get_screen("edit").ids.edit_fields_box
        box.clear_widgets()
        self._edit_fields_widgets = {}
        
        # إظهار الحقول الأساسية فقط للتعديل (الاسم، السن، الهاتف)
        base_fields = ["الاسم", "السن", "رقم الهاتف"]
        for field in self.fields:
            if field in base_fields:
                is_required = field in ["الاسم", "السن"]
                tf = MDTextField(
                    hint_text=field + (" (مطلوب)" if is_required else " (اختياري)"),
                    text=str(rec.get(field, "")),
                    mode="rectangle",
                    size_hint_y=None,
                    height=dp(56),
                    required=is_required,
                    helper_text="هذا الحقل مطلوب" if is_required else "",
                    helper_text_mode="on_error",
                    input_filter="int" if "السن" in field or "هاتف" in field or "رقم" in field else None
                )
                self._edit_fields_widgets[field] = tf
                box.add_widget(tf)
        
        self.go_to("edit")

    def update_record(self):
        idx = getattr(self, "_editing_idx", -1)
        if not (0 <= idx < len(self.records)):
            return

        # التحقق من الحقول المطلوبة (الاسم والسن)
        name_val = self._edit_fields_widgets.get("الاسم").text.strip() if self._edit_fields_widgets.get("الاسم") else ""
        age_val = self._edit_fields_widgets.get("السن").text.strip() if self._edit_fields_widgets.get("السن") else ""
        
        if not name_val:
            self._snack("يرجى إدخال الاسم")
            return
        if not age_val:
            self._snack("يرجى إدخال السن")
            return

        # تحديث البيانات في القائمة
        for field, widget in self._edit_fields_widgets.items():
            self.records[idx][field] = widget.text.strip()

        self._dirty = True
        # ارفع فوراً في الخلفية
        threading.Thread(target=self._upload_now, daemon=True).start()
        self._snack("تم تحديث البيانات ✅")
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
            err_msg = str(e)
            Clock.schedule_once(lambda dt: self._set_sync_label(f"❌ {err_msg}"), 0)

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
            err_msg = str(e)
            Clock.schedule_once(lambda dt: self._set_sync_label(f"خطأ: {err_msg}"), 0)

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
            is_base = field in ["الاسم", "السن", "رقم الهاتف"]
            is_required = field in ["الاسم", "السن"]
            
            status_text = "حقل أساسي (مطلوب)" if is_required else ("حقل أساسي (اختياري)" if is_base else "حقل إضافي (Checkbox)")
            
            item = TwoLineAvatarIconListItem(
                text=field,
                secondary_text=status_text,
            )
            if not is_base:
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
        if name in ["الاسم", "السن", "رقم الهاتف"]:
            self._snack("لا يمكن حذف الحقول الأساسية")
            return
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
        try:
            # محاولة الطريقة القياسية لـ KivyMD 1.1.x
            Snackbar(text=text, snackbar_x="8dp", snackbar_y="8dp", size_hint_x=0.95).open()
        except TypeError:
            # إصلاح لـ KivyMD 1.2.0+ حيث لا يقبل text في __init__
            snackbar = Snackbar(snackbar_x="8dp", snackbar_y="8dp", size_hint_x=0.95)
            snackbar.text = text
            snackbar.open()


# ─────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # عند التشغيل على الكمبيوتر، يمكننا ترك الحجم مرناً أو تعيين حجم افتراضي
    # لكن على الموبايل سيتكيف تلقائياً مع حجم الشاشة
    ContactApp().run()
