
"""
FTP Contact Manager — Arabic Edition
تسجيل قوافل مرسال — نظام إدارة السجلات عبر FTP
متوافق مع Kivy 2.3.1 (تم التعديل ليتوافق مع منطق py.py)
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

# ══════════════════════════════════════════════════════════════════
#  Kivy imports (بدلاً من KivyMD)
# ══════════════════════════════════════════════════════════════════
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
from kivy.clock import Clock
from kivy.resources import resource_add_path, resource_find

# ══════════════════════════════════════════════════════════════════
#  FTP Functions from py.py (adapted)
# ══════════════════════════════════════════════════════════════════

# --- إعدادات التخزين الافتراضية ---
DEFAULT_CONFIG = {
    "storage_mode": "local",  # "local" أو "ftp"
    # Local storage settings
    "local_directory": os.path.join(os.path.dirname(os.path.abspath(__file__)), "contacts_data"),
    "local_filename": "contacts.csv",
    # FTP settings
    "ftp_host": "mediarouter",
    "ftp_port": 21,
    "ftp_user": "mmk",
    "ftp_password": "4d6F6174617@",
    "ftp_directory": "/Kingston-09511F45_usb1_1",
    "ftp_filename": "moja.csv"
}

CONFIG_FILE = "ftp_config.json"
LOCAL_CACHE = "local_cache.csv"
FIELDS_FILE = "fields_config.json"

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
        ftp.connect(ftp_host, ftp_port, timeout=15)
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
                    if row:
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
        ftp.connect(ftp_host, ftp_port, timeout=15)
        ftp.login(ftp_user, ftp_pass)
        ftp.cwd(ftp_dir)
        
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {ftp_filename}", buffer.write)
        content = buffer.getvalue().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        for row in reader:
            if row:
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

# ══════════════════════════════════════════════════════════════════
#  App Class (adapted from py.py and main.py)
# ══════════════════════════════════════════════════════════════════
class ContactApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = ar("تسجيل قوافل مرسال")
        self.config_data = load_config()
        self.contacts_data = [] # Will be loaded on start
        self.custom_fields = [] # List of custom field names
        self.filtered_contacts = []
        self.search_active = False
        self.popup_instance = None # To manage active popups

    def build(self):
        print("Building app...")
        self._register_arabic_fonts()

        self.root_layout = BoxLayout(orientation='vertical', padding=sp(10), spacing=sp(10))

        # Settings Bar
        settings_layout = BoxLayout(size_hint_y=None, height=sp(50), spacing=sp(5))
        
        self.storage_local_btn = Button(
            text=ar("تخزين محلي"),
            font_name="ArabicF",
            font_size=sp(13),
            size_hint_x=0.33,
            background_color=(0.2, 0.6, 0.2, 1) if self.config_data.get("storage_mode") == "local" else (0.5, 0.5, 0.5, 1)
        )
        self.storage_local_btn.bind(on_press=self.show_local_settings)
        
        self.storage_ftp_btn = Button(
            text=ar("تخزين FTP"),
            font_name="ArabicF",
            font_size=sp(13),
            size_hint_x=0.33,
            background_color=(0.2, 0.6, 0.2, 1) if self.config_data.get("storage_mode") == "ftp" else (0.5, 0.5, 0.5, 1)
        )
        self.storage_ftp_btn.bind(on_press=self.show_ftp_settings)
        
        fields_btn = Button(
            text=ar("إدارة الحقول"),
            font_name="ArabicF",
            font_size=sp(13),
            size_hint_x=0.34
        )
        fields_btn.bind(on_press=self.show_fields_management)
        
        settings_layout.add_widget(self.storage_local_btn)
        settings_layout.add_widget(self.storage_ftp_btn)
        settings_layout.add_widget(fields_btn)
        self.root_layout.add_widget(settings_layout)

        # Search Area
        search_layout = BoxLayout(size_hint_y=None, height=sp(50), spacing=sp(5))
        self.search_input = TextInput(
            hint_text=ar("ابحث عن اسم..."),
            font_name="ArabicF",
            font_size=sp(14),
            multiline=False,
            size_hint_x=0.85,
            halign='right',
            base_direction='rtl'
        )
        self.search_input.bind(text=self.on_search_text)
        
        clear_search_btn = Button(
            text=ar("مسح"),
            font_name="ArabicF",
            font_size=sp(13),
            size_hint_x=0.15
        )
        clear_search_btn.bind(on_press=self.clear_search)
        
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(clear_search_btn)
        self.root_layout.add_widget(search_layout)

        # Input Area (Name, Age, Phone + Add Button)
        input_area_height = sp(60)
        input_layout = BoxLayout(size_hint_y=None, height=input_area_height, spacing=sp(5))
        font_size_input = sp(15)
        
        text_input_kwargs = {
            "multiline": False,
            "font_name": "ArabicF",
            "font_size": font_size_input,
            "padding": [sp(10), (input_area_height - font_size_input * 1.5) / 2, sp(10), 0],
            "write_tab": False,
            "halign": 'right',
            "base_direction": 'rtl'
        }
        
        self.name_input = TextInput(hint_text=ar("الاسم"), size_hint_x=0.35, **text_input_kwargs)
        self.age_input = TextInput(hint_text=ar("السن"), input_filter='int', size_hint_x=0.15, **text_input_kwargs)
        self.phone_input = TextInput(hint_text=ar("الهاتف"), input_filter='int', size_hint_x=0.2, **text_input_kwargs)
        
        add_btn = Button(
            text=ar("إضافة"),
            font_name="ArabicF",
            size_hint_x=0.3,
            font_size=sp(16)
        )
        add_btn.bind(on_press=self.add_contact)
        
        input_layout.add_widget(self.name_input)
        input_layout.add_widget(self.age_input)
        input_layout.add_widget(self.phone_input)
        input_layout.add_widget(add_btn)
        self.root_layout.add_widget(input_layout)

        self.status_label = Label(
            text=ar("جاهز"),
            font_name="ArabicF",
            size_hint_y=None,
            height=sp(30),
            font_size=sp(13),
            halign='right'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        self.root_layout.add_widget(self.status_label)

        self.storage_label = Label(
            text=ar(self.get_storage_info()),
            font_name="ArabicF",
            size_hint_y=None,
            height=sp(30),
            font_size=sp(11),
            halign='right'
        )
        self.storage_label.bind(size=self.storage_label.setter('text_size'))
        self.root_layout.add_widget(self.storage_label)

        self.fields_label = Label(
            text=ar(f"الحقول: {', '.join(self.custom_fields) if self.custom_fields else 'لا توجد حقول'}"),
            font_name="ArabicF",
            size_hint_y=None,
            height=sp(30),
            font_size=sp(12),
            halign='right'
        )
        self.fields_label.bind(size=self.fields_label.setter('text_size'))
        self.root_layout.add_widget(self.fields_label)

        self.scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, spacing=sp(5), size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        self.root_layout.add_widget(self.scroll)

        Clock.schedule_once(self.on_start_load, 0)
        print("App ready!")
        return self.root_layout

    def _register_arabic_fonts(self):
        """
        يسجّل الخطوط العربية.
        """
        _HERE = os.path.dirname(os.path.abspath(__file__))
        resource_add_path(_HERE)
        font_registered = False
        for font_file in ["Amiri-Regular.ttf", "Cairo-Bold.ttf", "noto_arabic.ttf"]:
            path = resource_find(font_file)
            if path:
                try:
                    LabelBase.register(name="ArabicF", fn_regular=path, fn_bold=path)
                    print(f"[Font] Arabic font registered: {path}")
                    font_registered = True
                    break
                except Exception as e:
                    print(f"[Font] Failed to register {font_file}: {e}")
        if not font_registered:
            print(f"[Font] WARNING: No Arabic font found in {_HERE}. Using default.")
            # Fallback to a generic font if no specific Arabic font is found
            LabelBase.register(name="ArabicF", fn_regular="Roboto", fn_bold="RobotoBold")

    def on_start_load(self, dt):
        self.contacts_data = load_data(self.config_data)
        self._load_custom_fields()
        self.build_list()
        self.update_storage_buttons()
        self.storage_label.text = ar(self.get_storage_info())
        self.fields_label.text = ar(f"الحقول: {', '.join(self.custom_fields) if self.custom_fields else 'لا توجد حقول'}")

    def _load_custom_fields(self):
        if os.path.exists(FIELDS_FILE):
            try:
                with open(FIELDS_FILE, 'r', encoding='utf-8') as f:
                    self.custom_fields = json.load(f)
            except Exception as e:
                print(f"Error loading custom fields: {e}")
        else:
            self.custom_fields = []

    def _save_custom_fields(self):
        try:
            with open(FIELDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.custom_fields, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving custom fields: {e}")

    def on_search_text(self, instance, value):
        search_text = value.strip().lower()
        
        if not search_text:
            self.search_active = False
            self.build_list()
            return
        
        self.search_active = True
        self.filtered_contacts = []
        
        for contact in self.contacts_data:
            if contact and len(contact) >= 1:
                # Search across all fields in the list
                for field_value in contact:
                    if search_text in str(field_value).lower():
                        self.filtered_contacts.append(contact)
                        break # Found in one field, move to next contact
        
        self.build_list()
        result_count = len(self.filtered_contacts)
        self.status_label.text = ar(f"نتائج البحث: {result_count}")

    def clear_search(self, instance):
        self.search_input.text = ""
        self.search_active = False
        self.build_list()

    def update_storage_buttons(self):
        storage_mode = self.config_data.get("storage_mode", "local")
        
        if storage_mode == "local":
            self.storage_local_btn.background_color = (0.2, 0.6, 0.2, 1)
            self.storage_ftp_btn.background_color = (0.5, 0.5, 0.5, 1)
        else:
            self.storage_local_btn.background_color = (0.5, 0.5, 0.5, 1)
            self.storage_ftp_btn.background_color = (0.2, 0.6, 0.2, 1)

    def get_storage_info(self):
        storage_mode = self.config_data.get("storage_mode", "local")
        if storage_mode == "ftp":
            return f"🔗 FTP: {self.config_data['ftp_host']} - {self.config_data['ftp_directory']}"
        else:
            return f"📁 Local: {self.config_data['local_directory']}"

    def build_list(self):
        self.list_layout.clear_widgets()
        size_list_font = sp(14)
        
        contacts_to_display = self.filtered_contacts if self.search_active else self.contacts_data
        
        if not contacts_to_display:
            empty_label = Label(
                text=ar("لا توجد جهات اتصال"),
                font_name="ArabicF",
                size_hint_y=None,
                height=sp(50),
                font_size=sp(14),
                halign='right'
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.list_layout.add_widget(empty_label)
            return
        
        for i, item in enumerate(contacts_to_display):
            original_idx = self.contacts_data.index(item) if self.search_active else i
            
            # Ensure the row has enough fields for Name, Age, Phone + Custom Fields
            expected_len = 3 + len(self.custom_fields)
            while len(item) < expected_len:
                item.append("")
            
            row = BoxLayout(size_hint_y=None, height=sp(100), spacing=sp(5), orientation='vertical', padding=sp(5))
            
            # Main Contact Info (Name, Age, Phone)
            main_info_layout = BoxLayout(size_hint_y=None, height=sp(40), spacing=sp(5))
            name_fixed = ar(item[0]) if len(item) > 0 else ar("غير معروف")
            age_raw = str(item[1]) if len(item) > 1 else ""
            phone_raw = str(item[2]) if len(item) > 2 else ""
            display_text = f"{phone_raw} - {age_raw} سنة - {name_fixed}"
            
            lbl = Label(
                text=display_text,
                font_name="ArabicF",
                size_hint_x=0.7,
                font_size=size_list_font,
                halign='right',
                valign='middle'
            )
            lbl.bind(size=lbl.setter('text_size'))
            main_info_layout.add_widget(lbl)

            edit_btn = Button(
                text=ar("تعديل"),
                font_name="ArabicF",
                size_hint_x=0.15,
                font_size=sp(12)
            )
            edit_btn.bind(on_press=lambda btn, idx=original_idx: self.edit_contact(idx))
            main_info_layout.add_widget(edit_btn)

            delete_btn = Button(
                text=ar("حذف"),
                font_name="ArabicF",
                size_hint_x=0.15,
                font_size=sp(12),
                background_color=(0.8, 0.2, 0.2, 1)
            )
            delete_btn.bind(on_press=lambda btn, idx=original_idx: self.delete_contact(idx))
            main_info_layout.add_widget(delete_btn)

            row.add_widget(main_info_layout)

            # Custom Fields (Checkboxes)
            if self.custom_fields:
                custom_fields_layout = GridLayout(cols=2, spacing=sp(5), size_hint_y=None, height=sp(50))
                for field_idx, field_name in enumerate(self.custom_fields):
                    # The actual data for custom fields starts at index 3
                    data_idx = field_idx + 3
                    is_checked = (len(item) > data_idx and str(item[data_idx]) == field_name)
                    
                    field_box = BoxLayout(size_hint_y=None, height=sp(25), spacing=sp(3))
                    checkbox = CheckBox(size_hint_x=None, width=sp(30), active=is_checked)
                    field_label = Label(
                        text=ar(field_name),
                        font_name="ArabicF",
                        font_size=sp(12),
                        halign='right',
                        valign='middle',
                        size_hint_x=1
                    )
                    field_label.bind(size=field_label.setter('text_size'))
                    
                    checkbox.contact_idx = original_idx
                    checkbox.field_data_idx = data_idx # Index in the contact list for this field
                    checkbox.field_name = field_name # The name of the custom field
                    checkbox.bind(active=self.on_checkbox_change)
                    
                    field_box.add_widget(field_label)
                    field_box.add_widget(checkbox)
                    custom_fields_layout.add_widget(field_box)
                row.add_widget(custom_fields_layout)
            
            self.list_layout.add_widget(row)

    def on_checkbox_change(self, checkbox, value):
        try:
            idx = checkbox.contact_idx
            field_data_idx = checkbox.field_data_idx
            field_name = checkbox.field_name
            
            # Update the contact list directly
            if len(self.contacts_data[idx]) <= field_data_idx:
                # Extend the list if necessary
                while len(self.contacts_data[idx]) <= field_data_idx:
                    self.contacts_data[idx].append("")

            self.contacts_data[idx][field_data_idx] = field_name if value else ""
            
            # Save data asynchronously
            threading.Thread(target=lambda: save_data(self.contacts_data, self.config_data), daemon=True).start()
            
            contact_name = self.contacts_data[idx][0]
            status = ar("✓ تم التحديث") if value else ar("☐ تم الإلغاء")
            self.status_label.text = f"{contact_name}: {field_name} - {status}"
        except Exception as e:
            print(f"Checkbox change error: {e}")
            self.status_label.text = ar("خطأ في التحديث")

    def add_contact(self, instance):
        name = self.name_input.text.strip()
        age = self.age_input.text.strip()
        phone = self.phone_input.text.strip()

        if not name:
            self.show_popup(ar("خطأ"), ar("الاسم لا يمكن أن يكون فارغاً."))
            return

        new_contact = [name, age, phone]
        # Add empty strings for custom fields
        for _ in self.custom_fields:
            new_contact.append("")

        self.contacts_data.insert(0, new_contact)
        self.name_input.text = ""
        self.age_input.text = ""
        self.phone_input.text = ""
        self.build_list()
        self.status_label.text = ar("تمت إضافة جهة اتصال جديدة.")
        threading.Thread(target=lambda: save_data(self.contacts_data, self.config_data), daemon=True).start()

    def edit_contact(self, idx):
        contact = self.contacts_data[idx]
        
        content = BoxLayout(orientation='vertical', spacing=sp(10), padding=sp(10))
        
        # Main fields
        name_input = TextInput(hint_text=ar("الاسم"), text=contact[0], multiline=False, font_name="ArabicF", halign='right', base_direction='rtl')
        age_input = TextInput(hint_text=ar("السن"), text=contact[1], input_filter='int', multiline=False, font_name="ArabicF", halign='right', base_direction='rtl')
        phone_input = TextInput(hint_text=ar("الهاتف"), text=contact[2], input_filter='int', multiline=False, font_name="ArabicF", halign='right', base_direction='rtl')
        
        content.add_widget(Label(text=ar("الاسم"), font_name="ArabicF", halign='right', size_hint_y=None, height=sp(30)))
        content.add_widget(name_input)
        content.add_widget(Label(text=ar("السن"), font_name="ArabicF", halign='right', size_hint_y=None, height=sp(30)))
        content.add_widget(age_input)
        content.add_widget(Label(text=ar("الهاتف"), font_name="ArabicF", halign='right', size_hint_y=None, height=sp(30)))
        content.add_widget(phone_input)

        # Custom fields
        custom_field_inputs = []
        for field_idx, field_name in enumerate(self.custom_fields):
            data_idx = field_idx + 3
            field_value = contact[data_idx] if len(contact) > data_idx else ""
            input_field = TextInput(hint_text=ar(field_name), text=field_value, multiline=False, font_name="ArabicF", halign='right', base_direction='rtl')
            content.add_widget(Label(text=ar(field_name), font_name="ArabicF", halign='right', size_hint_y=None, height=sp(30)))
            content.add_widget(input_field)
            custom_field_inputs.append(input_field)

        save_btn = Button(text=ar("حفظ التعديلات"), font_name="ArabicF", size_hint_y=None, height=sp(40))
        cancel_btn = Button(text=ar("إلغاء"), font_name="ArabicF", size_hint_y=None, height=sp(40))

        popup = Popup(
            title=ar("تعديل جهة اتصال"),
            content=content,
            size_hint=(0.9, 0.9),
            auto_dismiss=False
        )

        def save_edits(instance):
            contact[0] = name_input.text.strip()
            contact[1] = age_input.text.strip()
            contact[2] = phone_input.text.strip()
            for i, input_field in enumerate(custom_field_inputs):
                data_idx = i + 3
                if len(contact) <= data_idx:
                    while len(contact) <= data_idx:
                        contact.append("")
                contact[data_idx] = input_field.text.strip()

            self.build_list()
            self.status_label.text = ar("تم تحديث جهة الاتصال.")
            threading.Thread(target=lambda: save_data(self.contacts_data, self.config_data), daemon=True).start()
            popup.dismiss()

        save_btn.bind(on_press=save_edits)
        cancel_btn.bind(on_press=popup.dismiss)

        button_layout = BoxLayout(size_hint_y=None, height=sp(40), spacing=sp(10))
        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)

        popup.open()
        self.popup_instance = popup

    def delete_contact(self, idx):
        def confirm_delete(instance):
            self.contacts_data.pop(idx)
            self.build_list()
            self.status_label.text = ar("تم حذف جهة الاتصال.")
            threading.Thread(target=lambda: save_data(self.contacts_data, self.config_data), daemon=True).start()
            popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing=sp(10), padding=sp(10))
        content.add_widget(Label(text=ar("هل أنت متأكد من حذف جهة الاتصال هذه؟"), font_name="ArabicF", halign='center'))
        
        button_layout = BoxLayout(size_hint_y=None, height=sp(40), spacing=sp(10))
        confirm_btn = Button(text=ar("نعم"), font_name="ArabicF")
        cancel_btn = Button(text=ar("إلغاء"), font_name="ArabicF")
        button_layout.add_widget(confirm_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)

        popup = Popup(
            title=ar("تأكيد الحذف"),
            content=content,
            size_hint=(0.7, 0.4),
            auto_dismiss=False
        )
        confirm_btn.bind(on_press=confirm_delete)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()
        self.popup_instance = popup

    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=sp(10), padding=sp(10))
        content.add_widget(Label(text=message, font_name="ArabicF", halign='center'))
        close_btn = Button(text=ar("حسناً"), font_name="ArabicF", size_hint_y=None, height=sp(40))
        content.add_widget(close_btn)

        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.7, 0.4),
            auto_dismiss=False
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
        self.popup_instance = popup

    def show_local_settings(self, instance):
        if self.popup_instance and self.popup_instance.is_open: return

        popup_content = BoxLayout(orientation='vertical', spacing=sp(10), padding=sp(10))
        
        scroll = ScrollView()
        input_layout = GridLayout(cols=1, spacing=sp(10), size_hint_y=None)
        input_layout.bind(minimum_height=input_layout.setter('height'))
        
        local_fields = {
            ar("المجلد المحلي"): ("local_directory", self.config_data["local_directory"]),
            ar("اسم الملف"): ("local_filename", self.config_data["local_filename"])
        }
        
        local_inputs = {}
        for label_text, (key, value) in local_fields.items():
            row = BoxLayout(size_hint_y=None, height=sp(50), spacing=sp(10))
            label = Label(text=label_text, size_hint_x=0.3, font_name="ArabicF", font_size=sp(12), halign='right')
            label.bind(size=label.setter('text_size'))
            text_input = TextInput(text=str(value), multiline=False, size_hint_x=0.7, font_name="ArabicF", halign='right', base_direction='rtl')
            local_inputs[key] = text_input
            row.add_widget(label)
            row.add_widget(text_input)
            input_layout.add_widget(row)
        
        scroll.add_widget(input_layout)
        popup_content.add_widget(scroll)
        
        button_layout = BoxLayout(size_hint_y=None, height=sp(40), spacing=sp(10))
        
        activate_btn = Button(text=ar("تفعيل"), font_name="ArabicF", font_size=sp(14))
        test_btn = Button(text=ar("اختبار"), font_name="ArabicF", font_size=sp(14))
        cancel_btn = Button(text=ar("إلغاء"), font_name="ArabicF", font_size=sp(14))
        
        button_layout.add_widget(activate_btn)
        button_layout.add_widget(test_btn)
        button_layout.add_widget(cancel_btn)
        popup_content.add_widget(button_layout)
        
        popup = Popup(
            title=ar("إعدادات التخزين المحلي"),
            content=popup_content,
            size_hint=(0.95, 0.8),
            auto_dismiss=False
        )
        
        def activate_local(btn):
            try:
                self.config_data["local_directory"] = local_inputs["local_directory"].text.strip()
                self.config_data["local_filename"] = local_inputs["local_filename"].text.strip()
                self.config_data["storage_mode"] = "local"
                
                save_config(self.config_data)
                
                self.contacts_data = load_data(self.config_data)
                self.build_list()
                self.storage_label.text = ar(self.get_storage_info())
                self.update_storage_buttons()
                
                self.status_label.text = ar("✓ تم تفعيل التخزين المحلي")
                popup.dismiss()
            except Exception as e:
                print(f"Activate local error: {e}")
                self.status_label.text = ar(f"خطأ: {e}")
        
        def test_local(btn):
            try:
                local_dir = local_inputs["local_directory"].text.strip()
                print(f"Testing local directory: {local_dir}...")
                os.makedirs(local_dir, exist_ok=True)
                self.status_label.text = ar("✓ المجلد المحلي صحيح")
            except Exception as e:
                print(f"Test error: {e}")
                self.status_label.text = ar(f"✗ خطأ: {e}")
        
        activate_btn.bind(on_press=activate_local)
        test_btn.bind(on_press=test_local)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
        self.popup_instance = popup

    def show_ftp_settings(self, instance):
        if self.popup_instance and self.popup_instance.is_open: return

        popup_content = BoxLayout(orientation='vertical', spacing=sp(10), padding=sp(10))
        
        scroll = ScrollView()
        input_layout = GridLayout(cols=1, spacing=sp(10), size_hint_y=None)
        input_layout.bind(minimum_height=input_layout.setter('height'))
        
        ftp_fields = {
            "FTP Host": ("ftp_host", self.config_data["ftp_host"]),
            "FTP Port": ("ftp_port", str(self.config_data["ftp_port"])),
            ar("اسم المستخدم"): ("ftp_user", self.config_data["ftp_user"]),
            ar("كلمة المرور"): ("ftp_password", self.config_data["ftp_password"]),
            ar("مجلد FTP"): ("ftp_directory", self.config_data["ftp_directory"]),
            ar("اسم ملف FTP"): ("ftp_filename", self.config_data["ftp_filename"])
        }
        
        ftp_inputs = {}
        for label_text, (key, value) in ftp_fields.items():
            row = BoxLayout(size_hint_y=None, height=sp(50), spacing=sp(10))
            label = Label(text=label_text, size_hint_x=0.3, font_name="ArabicF", font_size=sp(12), halign='right')
            label.bind(size=label.setter('text_size'))
            text_input = TextInput(text=str(value), multiline=False, size_hint_x=0.7, font_name="ArabicF", halign='right', base_direction='rtl')
            ftp_inputs[key] = text_input
            row.add_widget(label)
            row.add_widget(text_input)
            input_layout.add_widget(row)
        
        scroll.add_widget(input_layout)
        popup_content.add_widget(scroll)
        
        button_layout = BoxLayout(size_hint_y=None, height=sp(40), spacing=sp(10))
        
        activate_btn = Button(text=ar("تفعيل"), font_name="ArabicF", font_size=sp(14))
        test_btn = Button(text=ar("اختبار"), font_name="ArabicF", font_size=sp(14))
        cancel_btn = Button(text=ar("إلغاء"), font_name="ArabicF", font_size=sp(14))
        
        button_layout.add_widget(activate_btn)
        button_layout.add_widget(test_btn)
        button_layout.add_widget(cancel_btn)
        popup_content.add_widget(button_layout)
        
        popup = Popup(
            title=ar("إعدادات FTP"),
            content=popup_content,
            size_hint=(0.95, 0.95),
            auto_dismiss=False
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
                
                self.contacts_data = load_data(self.config_data)
                self.build_list()
                self.storage_label.text = ar(self.get_storage_info())
                self.update_storage_buttons()
                
                self.status_label.text = ar("✓ تم تفعيل تخزين FTP")
                popup.dismiss()
            except Exception as e:
                print(f"Activate FTP error: {e}")
                self.status_label.text = ar(f"خطأ: {e}")
        
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
                ftp_filename = ftp_inputs["ftp_filename"].text.strip()

                # Test connection in a separate thread
                def _test_connection():
                    try:
                        ftp = FTP()
                        ftp.connect(ftp_host, ftp_port, timeout=15)
                        ftp.login(ftp_user, ftp_pass)
                        ftp.cwd(ftp_dir)
                        ftp.quit()
                        Clock.schedule_once(lambda dt: self.status_label.text = ar("✓ اتصال FTP ناجح"), 0)
                    except Exception as e:
                        Clock.schedule_once(lambda dt: self.status_label.text = ar(f"✗ فشل اتصال FTP: {e}"), 0)
                
                threading.Thread(target=_test_connection, daemon=True).start()

            except Exception as e:
                print(f"Test FTP error: {e}")
                self.status_label.text = ar(f"خطأ في اختبار FTP: {e}")
        
        activate_btn.bind(on_press=activate_ftp)
        test_btn.bind(on_press=test_ftp)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
        self.popup_instance = popup

    def show_fields_management(self, instance):
        if self.popup_instance and self.popup_instance.is_open: return

        popup_content = BoxLayout(orientation='vertical', spacing=sp(10), padding=sp(10))
        
        new_field_input = TextInput(hint_text=ar("اسم الحقل الجديد"), multiline=False, font_name="ArabicF", halign='right', base_direction='rtl')
        add_field_btn = Button(text=ar("إضافة حقل"), font_name="ArabicF", size_hint_y=None, height=sp(40))
        
        fields_list_layout = GridLayout(cols=1, spacing=sp(5), size_hint_y=None)
        fields_list_layout.bind(minimum_height=fields_list_layout.setter('height'))
        fields_scroll = ScrollView()
        fields_scroll.add_widget(fields_list_layout)

        def update_fields_list():
            fields_list_layout.clear_widgets()
            for i, field_name in enumerate(self.custom_fields):
                field_row = BoxLayout(size_hint_y=None, height=sp(40), spacing=sp(5))
                field_label = Label(text=ar(field_name), font_name="ArabicF", halign='right', valign='middle')
                field_label.bind(size=field_label.setter('text_size'))
                delete_btn = Button(text=ar("حذف"), font_name="ArabicF", size_hint_x=None, width=sp(60), background_color=(0.8, 0.2, 0.2, 1))
                delete_btn.bind(on_press=lambda btn, idx=i: delete_field(idx))
                field_row.add_widget(field_label)
                field_row.add_widget(delete_btn)
                fields_list_layout.add_widget(field_row)

        def add_field(instance):
            field_name = new_field_input.text.strip()
            if field_name and field_name not in self.custom_fields:
                self.custom_fields.append(field_name)
                self._save_custom_fields()
                update_fields_list()
                new_field_input.text = ""
                self.fields_label.text = ar(f"الحقول: {', '.join(self.custom_fields) if self.custom_fields else 'لا توجد حقول'}")
                self.build_list() # Rebuild main list to reflect new fields
            else:
                self.show_popup(ar("خطأ"), ar("اسم الحقل فارغ أو موجود بالفعل."))

        def delete_field(idx):
            del self.custom_fields[idx]
            self._save_custom_fields()
            update_fields_list()
            self.fields_label.text = ar(f"الحقول: {', '.join(self.custom_fields) if self.custom_fields else 'لا توجد حقول'}")
            self.build_list() # Rebuild main list to reflect removed fields

        add_field_btn.bind(on_press=add_field)

        popup_content.add_widget(new_field_input)
        popup_content.add_widget(add_field_btn)
        popup_content.add_widget(Label(text=ar("الحقول المضافة:"), font_name="ArabicF", halign='right', size_hint_y=None, height=sp(30)))
        popup_content.add_widget(fields_scroll)

        close_btn = Button(text=ar("إغلاق"), font_name="ArabicF", size_hint_y=None, height=sp(40))
        close_btn.bind(on_press=lambda btn: popup.dismiss())
        popup_content.add_widget(close_btn)

        popup = Popup(
            title=ar("إدارة الحقول المخصصة"),
            content=popup_content,
            size_hint=(0.9, 0.9),
            auto_dismiss=False
        )
        popup.open()
        self.popup_instance = popup
        update_fields_list()


if __name__ == "__main__":
    ContactApp().run()
