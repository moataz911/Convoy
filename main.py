import os
import sys
import threading
import functools

# Fix __file__ issue early
if not os.path.isabs(__file__):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_STORAGE_DIR = os.path.join(SCRIPT_DIR, "contacts_data")
os.makedirs(DEFAULT_STORAGE_DIR, exist_ok=True)

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.core.text import LabelBase
from kivy.metrics import sp
from kivy.clock import Clock
from ftplib import FTP
import io
import csv
import json

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _reshaper = arabic_reshaper.ArabicReshaper(configuration={
        'delete_harakat': True,
        'support_ligatures': True,
        'reshape_arabic_digits': False
    })
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

# --- تسجيل الخط ---
FONT_NAME = "CairoFont"

def _register_font():
    candidates = [
        os.path.join(SCRIPT_DIR, "Cairo-Bold.ttf"),
        os.path.join(os.getcwd(), "Cairo-Bold.ttf"),
        "/system/fonts/NotoSansArabic-Regular.ttf",
        "/system/fonts/DroidSansArabic.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                LabelBase.register(name=FONT_NAME, fn_regular=path)
                print(f"Font loaded: {path}")
                return FONT_NAME
            except Exception as e:
                print(f"Font error: {e}")
    return "Roboto"

ARABIC_FONT = _register_font()

# --- دالة تصحيح النص العربي مع cache ---
@functools.lru_cache(maxsize=2048)
def fix_arabic(text):
    if not text or not HAS_ARABIC:
        return text or ""
    try:
        return get_display(_reshaper.reshape(text))
    except Exception:
        return text

# --- إعدادات التخزين ---
CONFIG_FILE = os.path.join(DEFAULT_STORAGE_DIR, "config.json")

DEFAULT_CONFIG = {
    "storage_mode": "local",
    "local_directory": DEFAULT_STORAGE_DIR,
    "local_filename": "contacts.csv",
    "ftp_host": "mediarouter",
    "ftp_port": 21,
    "ftp_user": "mmk",
    "ftp_password": "4d6F6174617@",
    "ftp_directory": "/Kingston-09511F45_usb1_1",
    "ftp_filename": "moja.csv"
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
    except Exception as e:
        print(f"Config load error: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Config save error: {e}")
        return False

def save_data_local(data, local_dir, local_filename):
    try:
        os.makedirs(local_dir, exist_ok=True)
        path = os.path.join(local_dir, local_filename)
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerows(data)
        return True
    except Exception as e:
        print(f"Local save error: {e}")
        return False

def save_data_ftp(data, host, port, user, pwd, directory, filename):
    try:
        ftp = FTP()
        ftp.connect(host, port, timeout=10)
        ftp.login(user, pwd)
        ftp.cwd(directory)
        content = "\n".join(",".join(str(c) for c in row) for row in data)
        ftp.storbinary(f"STOR {filename}", io.BytesIO(content.encode("utf-8-sig")))
        ftp.quit()
        return True
    except Exception as e:
        print(f"FTP save error: {e}")
        return False

def load_data_local(local_dir, filename):
    data = []
    try:
        path = os.path.join(local_dir, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8-sig') as f:
                for row in csv.reader(f):
                    if row and len(row) >= 3:
                        data.append(row)
    except Exception as e:
        print(f"Local load error: {e}")
    return data

def load_data_ftp(host, port, user, pwd, directory, filename):
    data = []
    try:
        ftp = FTP()
        ftp.connect(host, port, timeout=10)
        ftp.login(user, pwd)
        ftp.cwd(directory)
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", buf.write)
        for row in csv.reader(io.StringIO(buf.getvalue().decode("utf-8-sig"))):
            if row and len(row) >= 3:
                data.append(row)
        ftp.quit()
    except Exception as e:
        print(f"FTP load error: {e}")
    return data

def load_data(config):
    if config.get("storage_mode") == "ftp":
        data = load_data_ftp(
            config["ftp_host"], config["ftp_port"],
            config["ftp_user"], config["ftp_password"],
            config["ftp_directory"], config["ftp_filename"]
        )
        if data:
            save_data_local(data, config["local_directory"], "backup_" + config["local_filename"])
        else:
            data = load_data_local(config["local_directory"], "backup_" + config["local_filename"])
    else:
        data = load_data_local(config["local_directory"], config["local_filename"])
    return data

def save_data(data, config, on_done=None):
    """حفظ في خيط منفصل لعدم تجميد الواجهة"""
    def _save():
        if config.get("storage_mode") == "ftp":
            ok = save_data_ftp(
                data[:], config["ftp_host"], config["ftp_port"],
                config["ftp_user"], config["ftp_password"],
                config["ftp_directory"], config["ftp_filename"]
            )
            if ok:
                save_data_local(data[:], config["local_directory"], "backup_" + config["local_filename"])
        else:
            ok = save_data_local(data[:], config["local_directory"], config["local_filename"])
        if on_done:
            Clock.schedule_once(lambda dt: on_done(ok), 0)
    threading.Thread(target=_save, daemon=True).start()


# --- صف جهة اتصال قابل لإعادة الاستخدام ---
class ContactRow(RecycleDataViewBehavior, BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 60
        self.spacing = 5
        self._contact_idx = None
        self._app = None

        self.info_label = Label(
            font_name=ARABIC_FONT,
            font_size=int(sp(13)),
            size_hint_x=0.55,
            halign='right',
            valign='middle'
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        self.add_widget(self.info_label)

        self.check_container = BoxLayout(size_hint_x=0.45, spacing=2, orientation='vertical')
        self.add_widget(self.check_container)

    def refresh_view_attrs(self, rv, index, data):
        self._contact_idx = data.get('original_idx', index)
        self._app = data.get('app')
        self.info_label.text = data.get('display_text', '')
        self._build_checkboxes(data)
        return super().refresh_view_attrs(rv, index, data)

    def _build_checkboxes(self, data):
        self.check_container.clear_widgets()
        fields = data.get('fields', [])
        checked = data.get('checked', [])
        app = data.get('app')

        if not fields:
            lbl = Label(
                text=fix_arabic("أضف حقول من إدارة الحقول"),
                font_name=ARABIC_FONT,
                font_size=int(sp(10)),
                halign='right'
            )
            self.check_container.add_widget(lbl)
            return

        for fi, fname in enumerate(fields):
            row = BoxLayout(size_hint_y=None, height=25, spacing=3)
            is_checked = fi < len(checked) and checked[fi]
            cb = CheckBox(size_hint_x=0.25, active=is_checked)
            cb.contact_idx = self._contact_idx
            cb.field_idx = fi + 3
            cb.field_name = fname
            if app:
                cb.bind(active=app.on_checkbox_change)
            lbl = Label(
                text=fix_arabic(fname),
                font_name=ARABIC_FONT,
                font_size=int(sp(11)),
                size_hint_x=0.75,
                halign='right'
            )
            row.add_widget(lbl)
            row.add_widget(cb)
            self.check_container.add_widget(row)


class ContactsRecycleView(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = RecycleBoxLayout(
            orientation='vertical',
            default_size=(None, 60),
            default_size_hint=(1, None),
            size_hint_y=None
        )
        layout.bind(minimum_height=layout.setter('height'))
        self.add_widget(layout)
        self.viewclass = 'ContactRow'


# --- التطبيق الرئيسي ---
class ContactsApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = fix_arabic("تسجيل قوافل مرسال")

    def build(self):
        self.config_data = load_config()
        self.contacts_data = load_data(self.config_data)
        self.checkbox_fields = []
        self.filtered_contacts = []
        self.search_active = False
        self._search_event = None

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)

        # شريط الإعدادات
        settings_bar = BoxLayout(size_hint_y=None, height=48, spacing=5)
        self.storage_local_btn = Button(
            text=fix_arabic("تخزين محلي"), font_name=ARABIC_FONT, font_size=int(sp(12)),
            size_hint_x=0.33,
            background_color=(0.2, 0.6, 0.2, 1) if self.config_data.get("storage_mode") == "local" else (0.45, 0.45, 0.45, 1)
        )
        self.storage_local_btn.bind(on_press=self.show_local_settings)

        self.storage_ftp_btn = Button(
            text=fix_arabic("تخزين FTP"), font_name=ARABIC_FONT, font_size=int(sp(12)),
            size_hint_x=0.33,
            background_color=(0.2, 0.6, 0.2, 1) if self.config_data.get("storage_mode") == "ftp" else (0.45, 0.45, 0.45, 1)
        )
        self.storage_ftp_btn.bind(on_press=self.show_ftp_settings)

        fields_btn = Button(
            text=fix_arabic("إدارة الحقول"), font_name=ARABIC_FONT,
            font_size=int(sp(12)), size_hint_x=0.34
        )
        fields_btn.bind(on_press=self.show_fields_management)

        settings_bar.add_widget(self.storage_local_btn)
        settings_bar.add_widget(self.storage_ftp_btn)
        settings_bar.add_widget(fields_btn)
        root.add_widget(settings_bar)

        # شريط البحث
        search_bar = BoxLayout(size_hint_y=None, height=48, spacing=5)
        self.search_input = TextInput(
            hint_text=fix_arabic("ابحث عن اسم..."),
            font_name=ARABIC_FONT, font_size=int(sp(14)),
            multiline=False, size_hint_x=0.85, padding=[10, 12, 10, 12]
        )
        self.search_input.bind(text=self.on_search_text)
        clear_btn = Button(
            text=fix_arabic("مسح"), font_name=ARABIC_FONT,
            font_size=int(sp(13)), size_hint_x=0.15
        )
        clear_btn.bind(on_press=self.clear_search)
        search_bar.add_widget(self.search_input)
        search_bar.add_widget(clear_btn)
        root.add_widget(search_bar)

        # منطقة الإدخال
        input_bar = BoxLayout(size_hint_y=None, height=56, spacing=5)
        inp_kwargs = dict(multiline=False, font_name=ARABIC_FONT,
                         font_size=int(sp(14)), padding=[10, 12, 10, 12],
                         size_hint_y=1, write_tab=False)
        self.name_input = TextInput(hint_text=fix_arabic("الاسم"), size_hint_x=0.35, **inp_kwargs)
        self.age_input  = TextInput(hint_text=fix_arabic("السن"), input_filter='int', size_hint_x=0.15, **inp_kwargs)
        self.phone_input= TextInput(hint_text=fix_arabic("الهاتف"), input_filter='int', size_hint_x=0.2, **inp_kwargs)
        add_btn = Button(
            text=fix_arabic("إضافة"), font_name=ARABIC_FONT,
            font_size=int(sp(15)), size_hint_x=0.3
        )
        add_btn.bind(on_press=self.add_contact)
        for w in [self.name_input, self.age_input, self.phone_input, add_btn]:
            input_bar.add_widget(w)
        root.add_widget(input_bar)

        # شريط الحالة
        self.status_label = Label(
            text=fix_arabic("جاهز"), font_name=ARABIC_FONT,
            size_hint_y=None, height=28, font_size=int(sp(12))
        )
        root.add_widget(self.status_label)

        self.storage_label = Label(
            text=fix_arabic(self._storage_info()), font_name=ARABIC_FONT,
            size_hint_y=None, height=26, font_size=int(sp(10))
        )
        root.add_widget(self.storage_label)

        self.fields_label = Label(
            text=fix_arabic("الحقول: لا توجد حقول"), font_name=ARABIC_FONT,
            size_hint_y=None, height=26, font_size=int(sp(11))
        )
        root.add_widget(self.fields_label)

        # القائمة الرئيسية
        self.rv = ContactsRecycleView()
        root.add_widget(self.rv)

        self._refresh_list()
        return root

    # --- بناء بيانات RecycleView ---
    def _make_rv_data(self, contacts):
        data = []
        for i, item in enumerate(contacts):
            if self.search_active:
                try:
                    orig_idx = self.contacts_data.index(item)
                except ValueError:
                    orig_idx = i
            else:
                orig_idx = i

            while len(item) < len(self.checkbox_fields) + 3:
                item.append("")

            name_fixed = fix_arabic(item[0])
            display = f"{item[2]} - {item[1]} سنة - {name_fixed}"
            checked = [str(item[fi + 3]) == fn
                       for fi, fn in enumerate(self.checkbox_fields)]

            data.append({
                'display_text': display,
                'original_idx': orig_idx,
                'fields': list(self.checkbox_fields),
                'checked': checked,
                'app': self,
            })
        return data

    def _refresh_list(self, *args):
        contacts = self.filtered_contacts if self.search_active else self.contacts_data
        self.rv.data = self._make_rv_data(contacts)

    # --- بحث مع تأخير (debounce 300ms) ---
    def on_search_text(self, instance, value):
        if self._search_event:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda dt: self._do_search(value), 0.3)

    def _do_search(self, value):
        text = value.strip().lower()
        if not text:
            self.search_active = False
            self._refresh_list()
            return
        self.search_active = True
        self.filtered_contacts = [
            c for c in self.contacts_data
            if c and text in str(c[0]).lower()
        ]
        self._refresh_list()
        self.status_label.text = fix_arabic(f"نتائج البحث: {len(self.filtered_contacts)}")

    def clear_search(self, instance):
        self.search_input.text = ""
        self.search_active = False
        self._refresh_list()

    # --- Checkbox ---
    def on_checkbox_change(self, checkbox, value):
        try:
            idx = checkbox.contact_idx
            self.contacts_data[idx][checkbox.field_idx] = checkbox.field_name if value else ""
            save_data(self.contacts_data, self.config_data)
            status = fix_arabic("✓ تم التحديث") if value else fix_arabic("تم الإلغاء")
            self.status_label.text = f"{self.contacts_data[idx][0]}: {checkbox.field_name} - {status}"
        except Exception as e:
            print(f"Checkbox error: {e}")

    # --- إضافة جهة اتصال ---
    def add_contact(self, instance):
        name = self.name_input.text.strip()
        age  = self.age_input.text.strip()
        phone= self.phone_input.text.strip()
        if name and age and phone:
            self.contacts_data.append([name, age, phone] + [""] * len(self.checkbox_fields))
            save_data(self.contacts_data, self.config_data,
                      on_done=lambda ok: setattr(self.status_label, 'text',
                                                  fix_arabic(f"✓ تمت إضافة: {name}")))
            self.name_input.text = self.age_input.text = self.phone_input.text = ""
            self.search_input.text = ""
            self.search_active = False
            self._refresh_list()
        else:
            self.status_label.text = fix_arabic("أدخل الاسم والسن والهاتف")

    # --- معلومات التخزين ---
    def _storage_info(self):
        if self.config_data.get("storage_mode") == "ftp":
            return f"FTP: {self.config_data['ftp_host']} - {self.config_data['ftp_directory']}"
        return f"Local: {self.config_data['local_directory']}"

    def _update_storage_btns(self):
        mode = self.config_data.get("storage_mode", "local")
        green, grey = (0.2, 0.6, 0.2, 1), (0.45, 0.45, 0.45, 1)
        self.storage_local_btn.background_color = green if mode == "local" else grey
        self.storage_ftp_btn.background_color   = green if mode == "ftp"   else grey

    # --- إعدادات التخزين المحلي ---
    def show_local_settings(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        fields = {
            fix_arabic("المجلد المحلي"): ("local_directory", self.config_data["local_directory"]),
            fix_arabic("اسم الملف"):    ("local_filename",  self.config_data["local_filename"]),
        }
        inputs = {}
        for lbl_txt, (key, val) in fields.items():
            row = BoxLayout(size_hint_y=None, height=50, spacing=10)
            row.add_widget(Label(text=lbl_txt, size_hint_x=0.35, font_name=ARABIC_FONT, font_size=int(sp(12))))
            ti = TextInput(text=str(val), multiline=False, size_hint_x=0.65)
            inputs[key] = ti
            row.add_widget(ti)
            grid.add_widget(row)

        scroll.add_widget(grid)
        content.add_widget(scroll)

        btn_row = BoxLayout(size_hint_y=None, height=50, spacing=10)
        ok_btn  = Button(text=fix_arabic("تفعيل"), font_name=ARABIC_FONT, font_size=int(sp(14)))
        tst_btn = Button(text=fix_arabic("اختبار"), font_name=ARABIC_FONT, font_size=int(sp(14)))
        can_btn = Button(text=fix_arabic("إلغاء"), font_name=ARABIC_FONT, font_size=int(sp(14)))
        btn_row.add_widget(ok_btn); btn_row.add_widget(tst_btn); btn_row.add_widget(can_btn)
        content.add_widget(btn_row)

        popup = Popup(title=fix_arabic("إعدادات التخزين المحلي"), content=content, size_hint=(0.95, 0.75))

        def activate(_):
            self.config_data["local_directory"] = inputs["local_directory"].text.strip()
            self.config_data["local_filename"]  = inputs["local_filename"].text.strip()
            self.config_data["storage_mode"]    = "local"
            save_config(self.config_data)
            self.contacts_data = load_data(self.config_data)
            self._refresh_list()
            self.storage_label.text = fix_arabic(self._storage_info())
            self._update_storage_btns()
            self.status_label.text = fix_arabic("✓ تم تفعيل التخزين المحلي")
            popup.dismiss()

        def test(_):
            d = inputs["local_directory"].text.strip()
            try:
                os.makedirs(d, exist_ok=True)
                self.status_label.text = fix_arabic("✓ المجلد صحيح")
            except Exception as e:
                self.status_label.text = fix_arabic(f"✗ خطأ: {e}")

        ok_btn.bind(on_press=activate)
        tst_btn.bind(on_press=test)
        can_btn.bind(on_press=popup.dismiss)
        popup.open()

    # --- إعدادات FTP ---
    def show_ftp_settings(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        fields = {
            "FTP Host":               ("ftp_host",      self.config_data["ftp_host"]),
            "FTP Port":               ("ftp_port",      str(self.config_data["ftp_port"])),
            fix_arabic("المستخدم"):   ("ftp_user",      self.config_data["ftp_user"]),
            fix_arabic("كلمة المرور"):("ftp_password",  self.config_data["ftp_password"]),
            fix_arabic("مجلد FTP"):   ("ftp_directory", self.config_data["ftp_directory"]),
            fix_arabic("الملف"):      ("ftp_filename",  self.config_data["ftp_filename"]),
        }
        inputs = {}
        for lbl_txt, (key, val) in fields.items():
            row = BoxLayout(size_hint_y=None, height=50, spacing=10)
            row.add_widget(Label(text=lbl_txt, size_hint_x=0.35, font_name=ARABIC_FONT, font_size=int(sp(12))))
            ti = TextInput(text=str(val), multiline=False, size_hint_x=0.65)
            inputs[key] = ti
            row.add_widget(ti)
            grid.add_widget(row)

        scroll.add_widget(grid)
        content.add_widget(scroll)

        btn_row = BoxLayout(size_hint_y=None, height=50, spacing=10)
        ok_btn  = Button(text=fix_arabic("تفعيل"),  font_name=ARABIC_FONT, font_size=int(sp(14)))
        tst_btn = Button(text=fix_arabic("اختبار"), font_name=ARABIC_FONT, font_size=int(sp(14)))
        can_btn = Button(text=fix_arabic("إلغاء"),  font_name=ARABIC_FONT, font_size=int(sp(14)))
        btn_row.add_widget(ok_btn); btn_row.add_widget(tst_btn); btn_row.add_widget(can_btn)
        content.add_widget(btn_row)

        popup = Popup(title=fix_arabic("إعدادات FTP"), content=content, size_hint=(0.95, 0.9))

        def activate(_):
            self.config_data["ftp_host"]      = inputs["ftp_host"].text.strip()
            self.config_data["ftp_port"]      = int(inputs["ftp_port"].text or 21)
            self.config_data["ftp_user"]      = inputs["ftp_user"].text.strip()
            self.config_data["ftp_password"]  = inputs["ftp_password"].text.strip()
            self.config_data["ftp_directory"] = inputs["ftp_directory"].text.strip()
            self.config_data["ftp_filename"]  = inputs["ftp_filename"].text.strip()
            self.config_data["storage_mode"]  = "ftp"
            save_config(self.config_data)
            self.contacts_data = load_data(self.config_data)
            self._refresh_list()
            self.storage_label.text = fix_arabic(self._storage_info())
            self._update_storage_btns()
            self.status_label.text = fix_arabic("✓ تم تفعيل FTP")
            popup.dismiss()

        def test(_):
            try:
                ftp = FTP()
                ftp.connect(inputs["ftp_host"].text.strip(), int(inputs["ftp_port"].text or 21), timeout=10)
                ftp.login(inputs["ftp_user"].text.strip(), inputs["ftp_password"].text.strip())
                ftp.cwd(inputs["ftp_directory"].text.strip())
                ftp.quit()
                self.status_label.text = fix_arabic("✓ اتصال FTP ناجح")
            except Exception as e:
                self.status_label.text = fix_arabic(f"✗ خطأ: {e}")

        ok_btn.bind(on_press=activate)
        tst_btn.bind(on_press=test)
        can_btn.bind(on_press=popup.dismiss)
        popup.open()

    # --- إدارة الحقول ---
    def show_fields_management(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(
            text=fix_arabic(f"الحقول الموجودة: ({len(self.checkbox_fields)})"),
            font_name=ARABIC_FONT, size_hint_y=None, height=30, font_size=int(sp(13))
        ))

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        field_inputs = []
        for field in self.checkbox_fields:
            row = BoxLayout(size_hint_y=None, height=50, spacing=8)
            ti = TextInput(text=field, multiline=False, size_hint_x=0.8)
            del_btn = Button(text=fix_arabic("حذف"), size_hint_x=0.2, font_name=ARABIC_FONT, font_size=int(sp(12)))
            row.add_widget(ti); row.add_widget(del_btn)
            grid.add_widget(row)
            field_inputs.append((ti, del_btn, row, grid))

        scroll.add_widget(grid)
        content.add_widget(scroll)

        new_row = BoxLayout(size_hint_y=None, height=50, spacing=8)
        new_input = TextInput(hint_text=fix_arabic("اسم الحقل الجديد"), multiline=False, size_hint_x=0.8)
        add_btn = Button(text=fix_arabic("إضافة"), size_hint_x=0.2, font_name=ARABIC_FONT, font_size=int(sp(12)))
        new_row.add_widget(new_input); new_row.add_widget(add_btn)
        content.add_widget(new_row)

        btn_row = BoxLayout(size_hint_y=None, height=50, spacing=10)
        save_btn = Button(text=fix_arabic("حفظ"),  font_name=ARABIC_FONT, font_size=int(sp(14)))
        can_btn  = Button(text=fix_arabic("إلغاء"), font_name=ARABIC_FONT, font_size=int(sp(14)))
        btn_row.add_widget(save_btn); btn_row.add_widget(can_btn)
        content.add_widget(btn_row)

        popup = Popup(title=fix_arabic("إدارة الحقول"), content=content, size_hint=(0.92, 0.88))

        def add_field(_):
            name = new_input.text.strip()
            if name and name not in self.checkbox_fields:
                self.checkbox_fields.append(name)
                for c in self.contacts_data:
                    while len(c) < len(self.checkbox_fields) + 3:
                        c.append("")
                save_data(self.contacts_data, self.config_data)
                new_input.text = ""
                self.fields_label.text = fix_arabic(f"الحقول: {', '.join(self.checkbox_fields)}")
                self.status_label.text = fix_arabic(f"✓ تم إضافة: {name}")
                self._refresh_list()

        def save_fields(_):
            new = [ti.text.strip() for ti, *_ in field_inputs if ti.text.strip()]
            self.checkbox_fields = new
            self.fields_label.text = fix_arabic(
                f"الحقول: {', '.join(new)}" if new else "الحقول: لا توجد حقول"
            )
            save_data(self.contacts_data, self.config_data)
            self._refresh_list()
            popup.dismiss()

        def del_field(btn, ti, row, g):
            name = ti.text
            if name in self.checkbox_fields:
                self.checkbox_fields.remove(name)
            g.remove_widget(row)

        for ti, del_btn, row, g in field_inputs:
            del_btn.bind(on_press=lambda b, t=ti, r=row, gr=g: del_field(b, t, r, gr))

        add_btn.bind(on_press=add_field)
        save_btn.bind(on_press=save_fields)
        can_btn.bind(on_press=popup.dismiss)
        popup.open()


if __name__ == "__main__":
    ContactsApp().run()
