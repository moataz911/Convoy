import os
import sys

# Fix __file__ issue early
if not os.path.isabs(__file__):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Create default storage directory
DEFAULT_STORAGE_DIR = os.path.join(SCRIPT_DIR, "contacts_data")
os.makedirs(DEFAULT_STORAGE_DIR, exist_ok=True)

import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.core.text import LabelBase
from kivy.metrics import sp
from ftplib import FTP
import io
import csv
import json
import shutil

try:
    import arabic_reshaper
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

# --- إعدادات الخط العربي الذكي ---
FONT_NAME = "ArabicFont"
FONT_PATH = os.path.join(SCRIPT_DIR, "noto_arabic.ttf")

CONFIG_FILE = os.path.join(DEFAULT_STORAGE_DIR, "config.json")
CONTACTS_FILE = os.path.join(DEFAULT_STORAGE_DIR, "contacts.csv")

def download_font():
    """تنزيل خط Noto Sans Arabic"""
    if os.path.exists(FONT_PATH) and os.path.getsize(FONT_PATH) > 100000:
        return True
    
    url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf"
    try:
        print(f"Downloading Noto Sans Arabic...")
        response = requests.get(url, timeout=20, stream=True)
        if response.status_code == 200:
            with open(FONT_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Download successful.")
            return True
    except Exception as e:
        print(f"Download failed: {e}")
    return False

def register_fonts():
    success = download_font()
    if success and os.path.exists(FONT_PATH):
        try:
            LabelBase.register(name=FONT_NAME, fn_regular=FONT_PATH)
            return FONT_NAME
        except Exception as e:
            print(f"Font registration error: {e}")
    
    system_fonts = [
        "/system/fonts/NotoSansArabic-Regular.ttf",
        "/system/fonts/DroidSansArabic.ttf"
    ]
    for font in system_fonts:
        if os.path.exists(font):
            try:
                LabelBase.register(name=FONT_NAME, fn_regular=font)
                return FONT_NAME
            except:
                continue
    return "Roboto"

ARABIC_FONT = register_fonts()

def fix_arabic(text):
    """تصحيح وتشكيل النصوص العربية"""
    if not text:
        return ""
    if not HAS_ARABIC:
        return text
    
    try:
        configuration = {
            'delete_harakat': True,
            'support_ligatures': True,
            'reshape_arabic_digits': False
        }
        reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
        reshaped_text = reshaper.reshape(text)
        return reshaped_text[::-1]
    except Exception as e:
        print(f"Arabic fixing error: {e}")
        return text

# --- إعدادات التخزين الافتراضية ---
DEFAULT_CONFIG = {
    "storage_mode": "local",  # "local" أو "ftp"
    # Local storage settings
    "local_directory": DEFAULT_STORAGE_DIR,
    "local_filename": "contacts.csv",
    # FTP settings
    "ftp_host": "mediarouter",
    "ftp_port": 21,
    "ftp_user": "mmk",
    "ftp_password": "4d6F6174617@",
    "ftp_directory": "/Kingston-09511F45_usb1_1",
    "ftp_filename": "moja.csv"
}

def load_config():
    """تحميل الإعدادات من الملف"""
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
    """حفظ الإعدادات في الملف"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Config save error: {e}")
        return False

def save_data_local(data, local_dir, local_filename):
    """حفظ البيانات محلياً"""
    try:
        os.makedirs(local_dir, exist_ok=True)
        contacts_file = os.path.join(local_dir, local_filename)
        
        with open(contacts_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            for row in data:
                writer.writerow(row)
        print(f"Data saved locally to {contacts_file}")
        return True
    except Exception as e:
        print(f"Local save error: {e}")
        return False

def save_data_ftp(data, ftp_host, ftp_port, ftp_user, ftp_pass, ftp_dir, ftp_filename):
    """حفظ البيانات على FTP"""
    try:
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port)
        ftp.login(ftp_user, ftp_pass)
        ftp.cwd(ftp_dir)
        
        content = ""
        for row in data:
            content += ",".join(str(cell) for cell in row) + "\n"
        
        ftp.storbinary(f"STOR {ftp_filename}", io.BytesIO(content.encode("utf-8-sig")))
        ftp.quit()
        print(f"Data saved to FTP: {ftp_host}:{ftp_dir}/{ftp_filename}")
        return True
    except Exception as e:
        print(f"FTP save error: {e}")
        return False

def load_data_local(local_dir, local_filename):
    """تحميل البيانات من ملف محلي"""
    data = []
    try:
        contacts_file = os.path.join(local_dir, local_filename)
        if os.path.exists(contacts_file):
            with open(contacts_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and len(row) >= 3:
                        data.append(row)
            print(f"Loaded {len(data)} contacts from {contacts_file}")
    except Exception as e:
        print(f"Local load error: {e}")
    
    return data

def load_data_ftp(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_dir, ftp_filename):
    """تحميل البيانات من FTP"""
    data = []
    try:
        print(f"Attempting to load from FTP: {ftp_host}...")
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port)
        ftp.login(ftp_user, ftp_pass)
        ftp.cwd(ftp_dir)
        
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {ftp_filename}", buffer.write)
        content = buffer.getvalue().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        for row in reader:
            if row and len(row) >= 3:
                data.append(row)
        ftp.quit()
        print(f"Loaded {len(data)} contacts from FTP")
    except Exception as e:
        print(f"FTP load error: {e}")
    
    return data

def load_data(config):
    """تحميل البيانات بناءً على نوع التخزين"""
    storage_mode = config.get("storage_mode", "local")
    
    if storage_mode == "ftp":
        print("Loading from FTP...")
        data = load_data_ftp(
            config["ftp_host"],
            config["ftp_port"],
            config["ftp_user"],
            config["ftp_password"],
            config["ftp_directory"],
            config["ftp_filename"]
        )
        # Backup locally if FTP load succeeded
        if data:
            save_data_local(data, config["local_directory"], "backup_" + config["local_filename"])
        else:
            # If FTP load failed, try local backup
            print("FTP load failed, trying local backup...")
            data = load_data_local(config["local_directory"], "backup_" + config["local_filename"])
    else:
        print("Loading from local storage...")
        data = load_data_local(config["local_directory"], config["local_filename"])
    
    return data

def save_data(data, config):
    """حفظ البيانات بناءً على نوع التخزين"""
    storage_mode = config.get("storage_mode", "local")
    
    success = False
    
    if storage_mode == "ftp":
        print("Saving to FTP...")
        success = save_data_ftp(
            data,
            config["ftp_host"],
            config["ftp_port"],
            config["ftp_user"],
            config["ftp_password"],
            config["ftp_directory"],
            config["ftp_filename"]
        )
        if success:
            # Also backup locally
            save_data_local(data, config["local_directory"], "backup_" + config["local_filename"])
    else:
        print("Saving to local storage...")
        success = save_data_local(data, config["local_directory"], config["local_filename"])
    
    return success

class ContactsApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = fix_arabic("تسجيل قوافل مرسال")
    
    def build(self):
        print("Building app...")
        self.config_data = load_config()
        self.contacts_data = load_data(self.config_data)
        self.checkbox_fields = []  # Empty by default
        self.filtered_contacts = []  # For search results
        self.search_active = False
        
        self.root_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # شريط الإعدادات
        settings_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        
        storage_local_btn = Button(
            text=fix_arabic("تخزين محلي"),
            font_name=ARABIC_FONT,
            font_size=int(sp(13)),
            size_hint_x=0.33,
            background_color=(0.2, 0.6, 0.2, 1) if self.config_data.get("storage_mode") == "local" else (0.5, 0.5, 0.5, 1)
        )
        storage_local_btn.bind(on_press=self.show_local_settings)
        self.storage_local_btn = storage_local_btn
        
        storage_ftp_btn = Button(
            text=fix_arabic("تخزين FTP"),
            font_name=ARABIC_FONT,
            font_size=int(sp(13)),
            size_hint_x=0.33,
            background_color=(0.2, 0.6, 0.2, 1) if self.config_data.get("storage_mode") == "ftp" else (0.5, 0.5, 0.5, 1)
        )
        storage_ftp_btn.bind(on_press=self.show_ftp_settings)
        self.storage_ftp_btn = storage_ftp_btn
        
        fields_btn = Button(
            text=fix_arabic("إدارة الحقول"),
            font_name=ARABIC_FONT,
            font_size=int(sp(13)),
            size_hint_x=0.34
        )
        fields_btn.bind(on_press=self.show_fields_management)
        
        settings_layout.add_widget(storage_local_btn)
        settings_layout.add_widget(storage_ftp_btn)
        settings_layout.add_widget(fields_btn)
        self.root_layout.add_widget(settings_layout)

        # منطقة البحث
        search_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        self.search_input = TextInput(
            hint_text=fix_arabic("ابحث عن اسم..."),
            font_name=ARABIC_FONT,
            font_size=int(sp(14)),
            multiline=False,
            size_hint_x=0.85
        )
        self.search_input.bind(text=self.on_search_text)
        
        clear_search_btn = Button(
            text=fix_arabic("مسح"),
            font_name=ARABIC_FONT,
            font_size=int(sp(13)),
            size_hint_x=0.15
        )
        clear_search_btn.bind(on_press=self.clear_search)
        
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(clear_search_btn)
        self.root_layout.add_widget(search_layout)

        # منطقة الإدخال
        input_area_height = 60
        input_layout = BoxLayout(size_hint_y=None, height=input_area_height, spacing=5)
        font_size_input = int(sp(15))
        
        text_input_kwargs = {
            "multiline": False,
            "font_name": ARABIC_FONT,
            "font_size": font_size_input,
            "padding": [10, (input_area_height - font_size_input * 1.5) / 2, 10, 0],
            "write_tab": False
        }
        
        self.name_input = TextInput(hint_text=fix_arabic("الاسم"), size_hint_x=0.35, **text_input_kwargs)
        self.age_input = TextInput(hint_text=fix_arabic("السن"), input_filter='int', size_hint_x=0.15, **text_input_kwargs)
        self.phone_input = TextInput(hint_text=fix_arabic("الهاتف"), input_filter='int', size_hint_x=0.2, **text_input_kwargs)
        
        add_btn = Button(
            text=fix_arabic("إضافة"),
            font_name=ARABIC_FONT,
            size_hint_x=0.3,
            font_size=int(sp(16))
        )
        add_btn.bind(on_press=self.add_contact)
        
        input_layout.add_widget(self.name_input)
        input_layout.add_widget(self.age_input)
        input_layout.add_widget(self.phone_input)
        input_layout.add_widget(add_btn)
        self.root_layout.add_widget(input_layout)

        self.status_label = Label(
            text=fix_arabic("جاهز"),
            font_name=ARABIC_FONT,
            size_hint_y=None,
            height=30,
            font_size=int(sp(13))
        )
        self.root_layout.add_widget(self.status_label)

        storage_info = self.get_storage_info()
        self.storage_label = Label(
            text=fix_arabic(storage_info),
            font_name=ARABIC_FONT,
            size_hint_y=None,
            height=30,
            font_size=int(sp(11))
        )
        self.root_layout.add_widget(self.storage_label)

        self.fields_label = Label(
            text=fix_arabic(f"الحقول: {', '.join(self.checkbox_fields) if self.checkbox_fields else 'لا توجد حقول'}"),
            font_name=ARABIC_FONT,
            size_hint_y=None,
            height=30,
            font_size=int(sp(12))
        )
        self.root_layout.add_widget(self.fields_label)

        self.scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        self.root_layout.add_widget(self.scroll)

        self.build_list()
        print("App ready!")
        return self.root_layout

    def on_search_text(self, instance, value):
        """معالجة البحث عن الأسماء"""
        search_text = value.strip().lower()
        
        if not search_text:
            self.search_active = False
            self.build_list()
            return
        
        self.search_active = True
        self.filtered_contacts = []
        
        for contact in self.contacts_data:
            if contact and len(contact) >= 1:
                contact_name = str(contact[0]).lower()
                if search_text in contact_name:
                    self.filtered_contacts.append(contact)
        
        self.build_list()
        result_count = len(self.filtered_contacts)
        self.status_label.text = fix_arabic(f"نتائج البحث: {result_count}")

    def clear_search(self, instance):
        """مسح البحث"""
        self.search_input.text = ""
        self.search_active = False
        self.build_list()

    def update_storage_buttons(self):
        """تحديث ألوان أزرار التخزين"""
        storage_mode = self.config_data.get("storage_mode", "local")
        
        if storage_mode == "local":
            self.storage_local_btn.background_color = (0.2, 0.6, 0.2, 1)
            self.storage_ftp_btn.background_color = (0.5, 0.5, 0.5, 1)
        else:
            self.storage_local_btn.background_color = (0.5, 0.5, 0.5, 1)
            self.storage_ftp_btn.background_color = (0.2, 0.6, 0.2, 1)

    def get_storage_info(self):
        """الحصول على معلومات التخزين الحالية"""
        storage_mode = self.config_data.get("storage_mode", "local")
        if storage_mode == "ftp":
            return f"🔗 FTP: {self.config_data['ftp_host']} - {self.config_data['ftp_directory']}"
        else:
            return f"📁 Local: {self.config_data['local_directory']}"

    def build_list(self):
        """بناء قائمة جهات الاتصال"""
        self.list_layout.clear_widgets()
        size_list_font = int(sp(14))
        
        # Use filtered contacts if search is active, otherwise use all contacts
        contacts_to_display = self.filtered_contacts if self.search_active else self.contacts_data
        
        if not contacts_to_display:
            empty_label = Label(
                text=fix_arabic("لا توجد جهات اتصال"),
                font_name=ARABIC_FONT,
                size_hint_y=None,
                height=50,
                font_size=int(sp(14))
            )
            self.list_layout.add_widget(empty_label)
            return
        
        for i, item in enumerate(contacts_to_display):
            # Get the original index in the main contacts_data
            if self.search_active:
                original_idx = self.contacts_data.index(item)
            else:
                original_idx = i
            
            # التأكد من أن الصف يحتوي على عدد كافٍ من الحقول
            while len(item) < len(self.checkbox_fields) + 3:
                item.append("")
            
            row = BoxLayout(size_hint_y=None, height=60, spacing=5)
            
            # معلومات جهة الاتصال
            name_fixed = fix_arabic(item[0])
            age_raw = str(item[1])
            phone_raw = str(item[2])
            display_text = f"{phone_raw} - {age_raw} سنة - {name_fixed}"
            
            lbl = Label(
                text=display_text,
                font_name=ARABIC_FONT,
                size_hint_x=0.5,
                font_size=size_list_font,
                halign='right',
                valign='middle'
            )
            lbl.bind(size=lbl.setter('text_size'))
            row.add_widget(lbl)

            # صناديق الاختيار
            checkbox_container = BoxLayout(size_hint_x=0.5, spacing=2, orientation='vertical')
            
            if self.checkbox_fields:
                for field_idx, field_name in enumerate(self.checkbox_fields):
                    field_layout = BoxLayout(size_hint_y=None, height=25, spacing=3)
                    
                    # Check if the field value matches the checkbox name
                    is_checked = str(item[field_idx + 3]) == field_name
                    
                    checkbox = CheckBox(size_hint_x=0.2, active=is_checked)
                    field_label = Label(
                        text=fix_arabic(field_name),
                        font_name=ARABIC_FONT,
                        font_size=int(sp(12)),
                        size_hint_x=0.8,
                        halign='right'
                    )
                    
                    checkbox.contact_idx = original_idx
                    checkbox.field_idx = field_idx + 3
                    checkbox.field_name = field_name
                    checkbox.bind(active=self.on_checkbox_change)
                    
                    field_layout.add_widget(field_label)
                    field_layout.add_widget(checkbox)
                    checkbox_container.add_widget(field_layout)
            else:
                # Show message if no fields are added
                no_fields_label = Label(
                    text=fix_arabic("أضف حقول من إدارة الحقول"),
                    font_name=ARABIC_FONT,
                    font_size=int(sp(11)),
                    halign='right',
                    size_hint_x=1
                )
                checkbox_container.add_widget(no_fields_label)
            
            row.add_widget(checkbox_container)
            self.list_layout.add_widget(row)

    def on_checkbox_change(self, checkbox, value):
        """تحديث حالة الاختيار"""
        try:
            idx = checkbox.contact_idx
            field_idx = checkbox.field_idx
            field_name = checkbox.field_name
            
            # Store the field name if checked, empty string if unchecked
            self.contacts_data[idx][field_idx] = field_name if value else ""
            
            save_data(self.contacts_data, self.config_data)
            
            contact_name = self.contacts_data[idx][0]
            status = fix_arabic("✓ تم التحديث") if value else fix_arabic("☐ تم الإلغاء")
            self.status_label.text = f"{contact_name}: {field_name} - {status}"
        except Exception as e:
            print(f"Checkbox change error: {e}")
            self.status_label.text = fix_arabic("خطأ في التحديث")

    def show_local_settings(self, instance):
        """عرض نافذة إعدادات التخزين المحلي"""
        try:
            popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            
            scroll = ScrollView()
            input_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
            input_layout.bind(minimum_height=input_layout.setter('height'))
            
            # Local storage fields
            local_fields = {
                fix_arabic("المجلد المحلي"): ("local_directory", self.config_data["local_directory"]),
                fix_arabic("اسم الملف"): ("local_filename", self.config_data["local_filename"])
            }
            
            local_inputs = {}
            for label_text, (key, value) in local_fields.items():
                row = BoxLayout(size_hint_y=None, height=50, spacing=10)
                label = Label(text=label_text, size_hint_x=0.3, font_name=ARABIC_FONT, font_size=int(sp(12)))
                text_input = TextInput(text=str(value), multiline=False, size_hint_x=0.7)
                local_inputs[key] = text_input
                row.add_widget(label)
                row.add_widget(text_input)
                input_layout.add_widget(row)
            
            scroll.add_widget(input_layout)
            popup_content.add_widget(scroll)
            
            # Buttons
            button_layout = BoxLayout(size_hint_y=0.15, spacing=10)
            
            activate_btn = Button(text=fix_arabic("تفعيل"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            test_btn = Button(text=fix_arabic("اختبار"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            cancel_btn = Button(text=fix_arabic("إلغاء"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            
            button_layout.add_widget(activate_btn)
            button_layout.add_widget(test_btn)
            button_layout.add_widget(cancel_btn)
            popup_content.add_widget(button_layout)
            
            popup = Popup(
                title=fix_arabic("إعدادات التخزين المحلي"),
                content=popup_content,
                size_hint=(0.95, 0.8)
            )
            
            def activate_local(btn):
                try:
                    self.config_data["local_directory"] = local_inputs["local_directory"].text.strip()
                    self.config_data["local_filename"] = local_inputs["local_filename"].text.strip()
                    self.config_data["storage_mode"] = "local"
                    
                    save_config(self.config_data)
                    
                    # Reload data
                    self.contacts_data = load_data(self.config_data)
                    self.build_list()
                    self.storage_label.text = fix_arabic(self.get_storage_info())
                    self.update_storage_buttons()
                    
                    self.status_label.text = fix_arabic("✓ تم تفعيل التخزين المحلي")
                    popup.dismiss()
                except Exception as e:
                    print(f"Activate local error: {e}")
                    self.status_label.text = fix_arabic(f"خطأ: {e}")
            
            def test_local(btn):
                try:
                    local_dir = local_inputs["local_directory"].text.strip()
                    print(f"Testing local directory: {local_dir}...")
                    if not os.path.exists(local_dir):
                        os.makedirs(local_dir, exist_ok=True)
                    self.status_label.text = fix_arabic("✓ المجلد المحلي صحيح")
                except Exception as e:
                    print(f"Test error: {e}")
                    self.status_label.text = fix_arabic(f"✗ خطأ: {e}")
            
            activate_btn.bind(on_press=activate_local)
            test_btn.bind(on_press=test_local)
            cancel_btn.bind(on_press=popup.dismiss)
            
            popup.open()
        except Exception as e:
            print(f"Local settings error: {e}")
            self.status_label.text = fix_arabic("خطأ في فتح الإعدادات")

    def show_ftp_settings(self, instance):
        """عرض نافذة إعدادات FTP"""
        try:
            popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            
            scroll = ScrollView()
            input_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
            input_layout.bind(minimum_height=input_layout.setter('height'))
            
            # FTP fields
            ftp_fields = {
                "FTP Host": ("ftp_host", self.config_data["ftp_host"]),
                "FTP Port": ("ftp_port", str(self.config_data["ftp_port"])),
                fix_arabic("اسم المستخدم"): ("ftp_user", self.config_data["ftp_user"]),
                fix_arabic("كلمة المرور"): ("ftp_password", self.config_data["ftp_password"]),
                fix_arabic("مجلد FTP"): ("ftp_directory", self.config_data["ftp_directory"]),
                fix_arabic("اسم ملف FTP"): ("ftp_filename", self.config_data["ftp_filename"])
            }
            
            ftp_inputs = {}
            for label_text, (key, value) in ftp_fields.items():
                row = BoxLayout(size_hint_y=None, height=50, spacing=10)
                label = Label(text=label_text, size_hint_x=0.3, font_name=ARABIC_FONT, font_size=int(sp(12)))
                text_input = TextInput(text=str(value), multiline=False, size_hint_x=0.7)
                ftp_inputs[key] = text_input
                row.add_widget(label)
                row.add_widget(text_input)
                input_layout.add_widget(row)
            
            scroll.add_widget(input_layout)
            popup_content.add_widget(scroll)
            
            # Buttons
            button_layout = BoxLayout(size_hint_y=0.15, spacing=10)
            
            activate_btn = Button(text=fix_arabic("تفعيل"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            test_btn = Button(text=fix_arabic("اختبار"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            cancel_btn = Button(text=fix_arabic("إلغاء"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            
            button_layout.add_widget(activate_btn)
            button_layout.add_widget(test_btn)
            button_layout.add_widget(cancel_btn)
            popup_content.add_widget(button_layout)
            
            popup = Popup(
                title=fix_arabic("إعدادات FTP"),
                content=popup_content,
                size_hint=(0.95, 0.95)
            )
            
            def activate_ftp(btn):
                try:
                    self.config_data["ftp_host"] = ftp_inputs["ftp_host"].text.strip()
                    try:
                        self.config_data["ftp_port"] = int(ftp_inputs["ftp_port"].text)
                    except:
                        self.config_data["ftp_port"] = 21
                    self.config_data["ftp_user"] = ftp_inputs["ftp_user"].text.strip()
                    self.config_data["ftp_password"] = ftp_inputs["ftp_password"].text.strip()
                    self.config_data["ftp_directory"] = ftp_inputs["ftp_directory"].text.strip()
                    self.config_data["ftp_filename"] = ftp_inputs["ftp_filename"].text.strip()
                    self.config_data["storage_mode"] = "ftp"
                    
                    save_config(self.config_data)
                    
                    # Reload data
                    self.contacts_data = load_data(self.config_data)
                    self.build_list()
                    self.storage_label.text = fix_arabic(self.get_storage_info())
                    self.update_storage_buttons()
                    
                    self.status_label.text = fix_arabic("✓ تم تفعيل تخزين FTP")
                    popup.dismiss()
                except Exception as e:
                    print(f"Activate FTP error: {e}")
                    self.status_label.text = fix_arabic(f"خطأ: {e}")
            
            def test_ftp(btn):
                try:
                    ftp_host = ftp_inputs["ftp_host"].text.strip()
                    try:
                        ftp_port = int(ftp_inputs["ftp_port"].text)
                    except:
                        ftp_port = 21
                    ftp_user = ftp_inputs["ftp_user"].text.strip()
                    ftp_pass = ftp_inputs["ftp_password"].text.strip()
                    ftp_dir = ftp_inputs["ftp_directory"].text.strip()
                    
                    print(f"Testing FTP connection to {ftp_host}:{ftp_port}...")
                    ftp = FTP()
                    ftp.connect(ftp_host, ftp_port)
                    ftp.login(ftp_user, ftp_pass)
                    ftp.cwd(ftp_dir)
                    ftp.quit()
                    self.status_label.text = fix_arabic("✓ اتصال FTP ناجح")
                except Exception as e:
                    print(f"FTP test error: {e}")
                    self.status_label.text = fix_arabic(f"✗ خطأ FTP: {e}")
            
            activate_btn.bind(on_press=activate_ftp)
            test_btn.bind(on_press=test_ftp)
            cancel_btn.bind(on_press=popup.dismiss)
            
            popup.open()
        except Exception as e:
            print(f"FTP settings error: {e}")
            self.status_label.text = fix_arabic("خطأ في فتح إعدادات FTP")

    def show_fields_management(self, instance):
        """عرض نافذة إدارة الحقول"""
        try:
            popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            
            scroll = ScrollView()
            fields_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
            fields_layout.bind(minimum_height=fields_layout.setter('height'))
            
            field_inputs = []
            for field in self.checkbox_fields:
                row = BoxLayout(size_hint_y=None, height=50, spacing=10)
                text_input = TextInput(text=field, multiline=False, size_hint_x=0.8)
                delete_btn = Button(text=fix_arabic("حذف"), size_hint_x=0.2, font_name=ARABIC_FONT, font_size=int(sp(12)))
                
                row.add_widget(text_input)
                row.add_widget(delete_btn)
                fields_layout.add_widget(row)
                field_inputs.append((text_input, delete_btn, row, fields_layout))
            
            scroll.add_widget(fields_layout)
            popup_content.add_widget(Label(
                text=fix_arabic(f"الحقول الموجودة: ({len(self.checkbox_fields)})"),
                font_name=ARABIC_FONT,
                size_hint_y=None,
                height=30,
                font_size=int(sp(13))
            ))
            popup_content.add_widget(scroll)
            
            new_field_row = BoxLayout(size_hint_y=None, height=50, spacing=10)
            new_field_input = TextInput(hint_text=fix_arabic("اسم الحقل الجديد"), multiline=False, size_hint_x=0.8)
            add_field_btn = Button(text=fix_arabic("إضافة"), size_hint_x=0.2, font_name=ARABIC_FONT, font_size=int(sp(12)))
            
            new_field_row.add_widget(new_field_input)
            new_field_row.add_widget(add_field_btn)
            popup_content.add_widget(new_field_row)
            
            button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
            save_btn = Button(text=fix_arabic("حفظ"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            cancel_btn = Button(text=fix_arabic("إلغاء"), font_name=ARABIC_FONT, font_size=int(sp(14)))
            
            button_layout.add_widget(save_btn)
            button_layout.add_widget(cancel_btn)
            popup_content.add_widget(button_layout)
            
            popup = Popup(
                title=fix_arabic("إدارة الحقول"),
                content=popup_content,
                size_hint=(0.9, 0.9)
            )
            
            def add_new_field(btn):
                new_field = new_field_input.text.strip()
                if new_field and new_field not in self.checkbox_fields:
                    self.checkbox_fields.append(new_field)
                    for contact in self.contacts_data:
                        while len(contact) < len(self.checkbox_fields) + 3:
                            contact.append("")
                    save_data(self.contacts_data, self.config_data)
                    new_field_input.text = ""
                    self.status_label.text = fix_arabic(f"✓ تم إضافة الحقل: {new_field}")
                    self.fields_label.text = fix_arabic(f"الحقول: {', '.join(self.checkbox_fields)}")
                    self.build_list()
                else:
                    self.status_label.text = fix_arabic("الحقل موجود بالفعل أو فارغ")
            
            def save_fields(btn):
                new_fields = []
                for field_input, _, _, _ in field_inputs:
                    if field_input.text.strip():
                        new_fields.append(field_input.text.strip())
                
                if new_fields or len(self.checkbox_fields) == 0:
                    self.checkbox_fields = new_fields
                    self.fields_label.text = fix_arabic(f"الحقول: {', '.join(self.checkbox_fields) if self.checkbox_fields else 'لا توجد حقول'}")
                    self.status_label.text = fix_arabic("✓ تم تحديث الحقول")
                    save_data(self.contacts_data, self.config_data)
                    self.build_list()
                
                popup.dismiss()
            
            def delete_field(delete_btn, field_input, row, fields_layout):
                field_name = field_input.text
                if field_name in self.checkbox_fields:
                    self.checkbox_fields.remove(field_name)
                fields_layout.remove_widget(row)
            
            for text_input, delete_btn, row, fields_layout in field_inputs:
                delete_btn.bind(on_press=lambda btn, ti=text_input, r=row, fl=fields_layout: delete_field(btn, ti, r, fl))
            
            add_field_btn.bind(on_press=add_new_field)
            save_btn.bind(on_press=save_fields)
            cancel_btn.bind(on_press=popup.dismiss)
            
            popup.open()
        except Exception as e:
            print(f"Fields management error: {e}")
            self.status_label.text = fix_arabic("خطأ في إدارة الحقول")

    def add_contact(self, instance):
        """إضافة جهة اتصال جديدة"""
        try:
            name = self.name_input.text.strip()
            age = self.age_input.text.strip()
            phone = self.phone_input.text.strip()
            
            if name and age and phone:
                # Now: Name, Age, Phone, Field1, Field2, ...
                new_contact = [name, age, phone] + [""] * len(self.checkbox_fields)
                self.contacts_data.append(new_contact)
                save_data(self.contacts_data, self.config_data)
                self.name_input.text = ""
                self.age_input.text = ""
                self.phone_input.text = ""
                self.status_label.text = fix_arabic(f"✓ تمت إضافة: {name}")
                self.search_input.text = ""
                self.build_list()
            else:
                self.status_label.text = fix_arabic("الرجاء إدخال الاسم والسن والهاتف")
        except Exception as e:
            print(f"Add contact error: {e}")
            self.status_label.text = fix_arabic("خطأ في إضافة جهة الاتصال")

if __name__ == "__main__":
    print("=" * 50)
    print("تطبيق تسجيل قوافل مرسال")
    print("=" * 50)
    print(f"Config: {CONFIG_FILE}")
    print("=" * 50)
    
    try:
        app = ContactsApp()
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()