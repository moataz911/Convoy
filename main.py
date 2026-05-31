# -*- coding: utf-8 -*-
"""
FTP Files Viewer — Arabic Edition
عارض ملفات FTP — تسجيل قوافل مرسال
قراءة فقط — كل الملفات كتبويبات في الأسفل
متوافق مع KivyMD 1.2.0 + Kivy 2.3.1
"""
import io, csv, json, os, re, threading, sys
from functools import lru_cache
from ftplib import FTP

# ══════════════════════════════════════════════════════════════════
#  UTF-8 enforcement
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
#  Arabic text support
# ══════════════════════════════════════════════════════════════════
try:
    import arabic_reshaper as _ext_reshaper
    from bidi.algorithm import get_display as _ext_bidi
    _ARABIC_OK = True
except ImportError:
    _ext_reshaper = None
    _ext_bidi     = None
    _ARABIC_OK    = False

_AR_FORMS = {
    '\u0621': ('\uFE80', None, None, None),
    '\u0622': ('\uFE81', '\uFE82', None, None),
    '\u0623': ('\uFE83', '\uFE84', None, None),
    '\u0624': ('\uFE85', '\uFE86', None, None),
    '\u0625': ('\uFE87', '\uFE88', None, None),
    '\u0626': ('\uFE89', '\uFE8A', '\uFE8B', '\uFE8C'),
    '\u0627': ('\uFE8D', '\uFE8E', None, None),
    '\u0628': ('\uFE8F', '\uFE90', '\uFE91', '\uFE92'),
    '\u0629': ('\uFE93', '\uFE94', None, None),
    '\u062A': ('\uFE95', '\uFE96', '\uFE97', '\uFE98'),
    '\u062B': ('\uFE99', '\uFE9A', '\uFE9B', '\uFE9C'),
    '\u062C': ('\uFE9D', '\uFE9E', '\uFE9F', '\uFEA0'),
    '\u062D': ('\uFEA1', '\uFEA2', '\uFEA3', '\uFEA4'),
    '\u062E': ('\uFEA5', '\uFEA6', '\uFEA7', '\uFEA8'),
    '\u062F': ('\uFEA9', '\uFEAA', None, None),
    '\u0630': ('\uFEAB', '\uFEAC', None, None),
    '\u0631': ('\uFEAD', '\uFEAE', None, None),
    '\u0632': ('\uFEAF', '\uFEB0', None, None),
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
    '\u0648': ('\uFEED', '\uFEEE', None, None),
    '\u0649': ('\uFEEF', '\uFEF0', None, None),
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
    chars = list(text); n = len(chars); out = []; i = 0
    while i < n:
        ch = chars[i]
        if ch == '\u0644' and i+1 < n and chars[i+1] in _LAM_ALEF:
            prev_conn = i > 0 and chars[i-1] in _AR_FORMS and chars[i-1] not in _AR_DISC
            lig = _LAM_ALEF[chars[i+1]]
            out.append(lig[1] if prev_conn else lig[0]); i += 2; continue
        if ch not in _AR_FORMS:
            out.append(ch); i += 1; continue
        f = _AR_FORMS[ch]
        pc = i > 0 and chars[i-1] in _AR_FORMS and chars[i-1] not in _AR_DISC
        nc = ch not in _AR_DISC and i+1 < n and chars[i+1] in _AR_FORMS
        if pc and nc:   out.append(f[3] or f[1] or f[0])
        elif pc:        out.append(f[1] or f[0])
        elif nc:        out.append(f[2] or f[0])
        else:           out.append(f[0])
        i += 1
    return ''.join(out)

def _ar_bidi_inline(text):
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
        result.append(run_text[::-1] if is_rtl else run_text)
    return ''.join(result)

@lru_cache(maxsize=4096)
def ar(text: str) -> str:
    if not text: return text
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
    def _replace(m):
        s = m.group(1)
        if any('\u0600' <= c <= '\u06FF' for c in s):
            return f'"{ar(s)}"'
        return m.group(0)
    return re.sub(r'"([^"\n]*)"', _replace, kv)

# ══════════════════════════════════════════════════════════════════
#  Font registration
# ══════════════════════════════════════════════════════════════════
from kivy.core.text import LabelBase
_HERE = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════════
#  Kivy / KivyMD imports
# ══════════════════════════════════════════════════════════════════
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.selectioncontrol import MDCheckbox

# ══════════════════════════════════════════════════════════════════
#  Screen classes
# ══════════════════════════════════════════════════════════════════
class HomeScreen(Screen): pass
class SettingsScreen(Screen): pass

# ══════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════
DEFAULT_FTP = {
    "host": "mediarouter", "port": 21, "user": "mmk",
    "password": "4d6F6174617@",
    "directory": "/Kingston-09511F45_usb1_1",
}
CONFIG_FILE = "ftp_config.json"

# ══════════════════════════════════════════════════════════════════
#  KV layout
# ══════════════════════════════════════════════════════════════════
KV = """
ScreenManager:
    HomeScreen:
    SettingsScreen:

<HomeScreen>:
    name: "home"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "\u062a\u0633\u062c\u064a\u0644 \u0642\u0648\u0627\u0641\u0644 \u0645\u0631\u0633\u0627\u0644"
            right_action_items: [["refresh", lambda x: app.refresh_all_files()], ["cog", lambda x: app.go_to("settings")]]
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
            MDList:
                id: record_list
                padding: [dp(8), dp(6)]
                spacing: dp(6)
        MDBoxLayout:
            id: tab_bar_container
            size_hint_y: None
            height: dp(56)
            md_bg_color: 0.0, 0.588, 0.533, 1
            padding: [dp(4), dp(4)]
            ScrollView:
                do_scroll_x: True
                do_scroll_y: False
                bar_width: 0
                MDBoxLayout:
                    id: tab_bar
                    orientation: "horizontal"
                    adaptive_width: True
                    spacing: dp(4)

<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "\u0625\u0639\u062f\u0627\u062f\u0627\u062a FTP"
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
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(10)
                    MDRaisedButton:
                        text: "\u062d\u0641\u0638"
                        on_release: app.save_settings()
                    MDFlatButton:
                        text: "\u0627\u062e\u062a\u0628\u0627\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644"
                        on_release: app.test_connection()
"""

# ══════════════════════════════════════════════════════════════════
#  Helper
# ══════════════════════════════════════════════════════════════════
def _rlbl(**kw):
    lbl = MDLabel(**kw)
    lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
    return lbl

# ══════════════════════════════════════════════════════════════════
#  FTP Manager  (قراءة فقط)
# ══════════════════════════════════════════════════════════════════
class FTPManager:
    def __init__(self, cfg):
        self.cfg = cfg

    def _connect(self):
        ftp = FTP()
        ftp.connect(host=str(self.cfg.get("host","")),
                    port=int(self.cfg.get("port",21)), timeout=15)
        ftp.login(user=str(self.cfg.get("user","")),
                  passwd=str(self.cfg.get("password","")))
        ftp.set_pasv(True)
        d = str(self.cfg.get("directory","")).strip()
        if d: ftp.cwd(d)
        return ftp

    def _close(self, ftp):
        try:    ftp.quit()
        except Exception:
            try: ftp.close()
            except Exception: pass

    def test(self):
        ftp = None
        try:
            ftp = self._connect(); ftp.pwd()
            return True, "\u062a\u0645 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0646\u062c\u0627\u062d"
        except Exception as e:
            return False, f"\u0641\u0634\u0644 \u0627\u0644\u0627\u062a\u0635\u0627\u0644: {e}"
        finally:
            if ftp: self._close(ftp)

    def list_files(self):
        """يُعيد قائمة مرتبة بجميع ملفات CSV في مجلد FTP."""
        ftp = None
        try:
            ftp = self._connect()
            return sorted(f for f in ftp.nlst() if f.lower().endswith(".csv"))
        except Exception as e:
            print(f"[FTP List] {e}"); return []
        finally:
            if ftp: self._close(ftp)

    def read_csv_by_name(self, filename):
        """يقرأ ملف CSV محدد من FTP ويُعيد قائمة السجلات."""
        ftp = None
        try:
            ftp = self._connect()
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", buf.write)
            raw = buf.getvalue()
            self._close(ftp); ftp = None
            text = None
            for enc in ("utf-8-sig", "utf-8", "windows-1256"):
                try:    text = raw.decode(enc); break
                except: pass
            if text is None: text = raw.decode("utf-8", errors="replace")
            return list(csv.DictReader(io.StringIO(text)))
        except Exception as e:
            print(f"[FTP Read {filename}] {e}"); return []
        finally:
            if ftp: self._close(ftp)

# ══════════════════════════════════════════════════════════════════
#  App
# ══════════════════════════════════════════════════════════════════
class ContactApp(MDApp):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.ftp_config  = dict(DEFAULT_FTP)
        self.files_data  = {}       # filename -> list[dict]
        self.active_file = None
        self._ftp_ok     = False
        self._checking   = False
        self._loading    = False

    # ── Build ──────────────────────────────────────────────────
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style     = "Light"
        self._register_arabic_fonts()
        return Builder.load_string(_ar_in_kv(KV))

    def _register_arabic_fonts(self):
        from kivy.resources import resource_add_path, resource_find
        resource_add_path(self.directory)
        for font_file in ["Amiri-Regular.ttf", "Cairo-Bold.ttf"]:
            path = resource_find(font_file)
            if not path:
                c = os.path.join(self.directory, font_file)
                if os.path.exists(c): path = c
            if path:
                try:
                    for fn in ["Roboto","RobotoMedium","RobotoBold","RobotoLight","ArabicF"]:
                        LabelBase.register(name=fn, fn_regular=path, fn_bold=path)
                    print(f"[Font] {path}"); break
                except Exception as e:
                    print(f"[Font] {e}")

    def on_start(self):
        self._load_config()
        Clock.schedule_interval(self._periodic_check, 10)
        Clock.schedule_once(lambda dt: self._load_all_ftp_files(), 0.5)
        Clock.schedule_interval(self._auto_refresh, 60)

    # ── Config ─────────────────────────────────────────────────
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try: self.ftp_config = json.load(open(CONFIG_FILE, encoding="utf-8"))
            except Exception: pass
        self.ftp = FTPManager(self.ftp_config)

    # ── Navigation ─────────────────────────────────────────────
    def go_to(self, name):
        self.root.transition = SlideTransition(
            direction="left" if name != "home" else "right")
        self.root.current = name
        if name == "settings": self._load_settings_ui()

    # ── FTP Status ─────────────────────────────────────────────
    def _periodic_check(self, dt):
        if self._checking: return
        self._checking = True
        prev = self._ftp_ok
        def _bg():
            ok, _ = self.ftp.test()
            def _ui(dt2):
                self._ftp_ok = ok; self._checking = False
                if prev and not ok:
                    self._snack("\u0627\u0646\u0642\u0637\u0639 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0633\u064a\u0631\u0641\u0631 FTP")
                self._update_status_bar()
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def _update_status_bar(self):
        try:
            bar = self.root.get_screen("home").ids.ftp_status_bar
            lbl = self.root.get_screen("home").ids.ftp_status_label
            bar.height = 0 if self._ftp_ok else dp(30)
            lbl.text   = "" if self._ftp_ok else ar("\u063a\u064a\u0631 \u0645\u062a\u0635\u0644 \u0628\u0633\u064a\u0631\u0641\u0631 FTP")
        except Exception: pass

    # ── Load All Files ─────────────────────────────────────────
    def _load_all_ftp_files(self):
        if self._loading: return
        self._loading = True
        def _bg():
            files  = self.ftp.list_files()
            result = {f: self.ftp.read_csv_by_name(f) for f in files}
            def _ui(dt):
                self._loading = False; self._ftp_ok = bool(files)
                self.files_data = result
                self._update_status_bar()
                if not files:
                    self._show_empty_state(); return
                if self.active_file not in files:
                    self.active_file = files[0]
                self._render_tabs()
                self._show_tab(self.active_file)
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_bg, daemon=True).start()

    def refresh_all_files(self):
        self._snack("\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u062f\u064a\u062b...")
        self._loading = False
        self._load_all_ftp_files()

    def _auto_refresh(self, dt):
        if not self._loading:
            self._load_all_ftp_files()

    # ── Tabs ───────────────────────────────────────────────────
    def _render_tabs(self):
        try:
            tab_bar = self.root.get_screen("home").ids.tab_bar
            tab_bar.clear_widgets()
            for fname in self.files_data.keys():
                is_active = (fname == self.active_file)
                if is_active:
                    btn = MDRaisedButton(
                        text=fname, size_hint=(None, 1), width=dp(140),
                        md_bg_color=(1, 1, 1, 1),
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                    )
                else:
                    btn = MDFlatButton(
                        text=fname, size_hint=(None, 1), width=dp(140),
                        theme_text_color="Custom",
                        text_color=(1, 1, 1, 0.85),
                    )
                btn.bind(on_release=lambda x, f=fname: self._select_tab(f))
                tab_bar.add_widget(btn)
        except Exception as e:
            print(f"[Tabs] {e}")

    def _select_tab(self, filename):
        self.active_file = filename
        self._render_tabs()
        self._show_tab(filename)

    # ── Records Display (Read-Only) ────────────────────────────
    def _show_tab(self, filename):
        try:
            lst = self.root.get_screen("home").ids.record_list
            lst.clear_widgets()
            records = self.files_data.get(filename, [])
            if not records:
                lst.add_widget(_rlbl(
                    text=ar("\u0644\u0627 \u062a\u0648\u062c\u062f \u0633\u062c\u0644\u0627\u062a \u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u0645\u0644\u0641"),
                    halign="center", height=dp(70), size_hint_y=None))
                return
            for rec in records:
                lst.add_widget(self._make_view_item(rec))
                lst.add_widget(MDCard(height=dp(1), size_hint_y=None,
                                      elevation=0, md_bg_color=[0,0,0,.08]))
        except Exception as e:
            print(f"[ShowTab] {e}")

    def _make_view_item(self, rec):
        """صف عرض قراءة فقط: checkbox تم (يسار) + الاسم (يمين)."""
        box = MDBoxLayout(orientation="horizontal", adaptive_height=True,
                          padding=[dp(14), dp(10)], spacing=dp(12))
        tam_val = rec.get("\u062a\u0645", "false")   # "تم"
        cb = MDCheckbox(active=(tam_val == "true"),
                        size_hint=(None, None), size=(dp(28), dp(28)),
                        disabled=True)
        name_text = rec.get("\u0627\u0644\u0627\u0633\u0645", "") or "\u0628\u062f\u0648\u0646 \u0627\u0633\u0645"
        lbl = _rlbl(text=ar(name_text), font_style="H6",
                    adaptive_height=True, halign="right")
        box.add_widget(cb)
        box.add_widget(lbl)
        return box

    def _show_empty_state(self):
        try:
            lst = self.root.get_screen("home").ids.record_list
            lst.clear_widgets()
            lst.add_widget(_rlbl(
                text=ar("\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u0644\u0641\u0627\u062a CSV \u0639\u0644\u0649 \u0627\u0644\u0633\u064a\u0631\u0641\u0631"),
                halign="center", height=dp(80), size_hint_y=None))
            self.root.get_screen("home").ids.tab_bar.clear_widgets()
        except Exception as e:
            print(f"[EmptyState] {e}")

    # ── Snackbar ───────────────────────────────────────────────
    def _snack(self, text):
        has_orig = any('\u0600' <= c <= '\u06FF' for c in (text or ''))
        msg = ar(text) if has_orig else str(text or '')
        if not msg: return
        def _show(dt):
            try:
                from kivy.core.window import Window
                from kivy.uix.boxlayout import BoxLayout
                from kivy.graphics import Color, RoundedRectangle
                from kivy.animation import Animation
                W = Window.width * 0.88; H = dp(52)
                X = Window.width * 0.06; Y = dp(24)
                box = BoxLayout(size_hint=(None,None), size=(W,H), pos=(X,Y),
                                padding=(dp(14), dp(8)))
                with box.canvas.before:
                    Color(0.12, 0.12, 0.12, 0.92)
                    rr = RoundedRectangle(size=(W,H), pos=(X,Y),
                                         radius=[dp(8),dp(8),dp(8),dp(8)])
                box.bind(pos=lambda i,v: setattr(rr,'pos',v))
                box.bind(size=lambda i,v: setattr(rr,'size',v))
                from kivymd.uix.label import MDLabel as _ML
                lbl = _ML(text=msg, halign='center', valign='middle',
                          theme_text_color='Custom', text_color=(1,1,1,1),
                          font_style='Body1', size_hint=(1,1))
                lbl.bind(size=lambda i,v: setattr(i,'text_size',v))
                box.add_widget(lbl)
                box.opacity = 0
                Window.add_widget(box, index=0)
                Animation(opacity=1, duration=0.2).start(box)
                def _remove(dt):
                    def _done(*_):
                        try: Window.remove_widget(box)
                        except: pass
                    anim = Animation(opacity=0, duration=0.2)
                    anim.bind(on_complete=_done); anim.start(box)
                Clock.schedule_once(_remove, 3)
            except Exception as e:
                print(f'[Snack] {e}')
        Clock.schedule_once(_show, 0)

    def _dlg(self, title, text, buttons=None):
        if buttons is None:
            btn = MDFlatButton(text=ar("\u062d\u0633\u0646\u0627\u064b"))
            d   = MDDialog(title=title, text=text, buttons=[btn])
            btn.bind(on_release=lambda x: d.dismiss())
        else:
            d = MDDialog(title=title, text=text, buttons=buttons)
        d.open(); return d

    # ── Settings ───────────────────────────────────────────────
    def _load_settings_ui(self):
        ids = self.root.get_screen("settings").ids
        for k in ["host","port","user","password","directory"]:
            getattr(ids, f"ftp_{k}").text = str(self.ftp_config.get(k,""))

    def save_settings(self):
        ids = self.root.get_screen("settings").ids
        self.ftp_config = {k: getattr(ids, f"ftp_{k}").text.strip()
                           for k in ["host","user","password","directory"]}
        self.ftp_config["port"] = int(ids.ftp_port.text.strip() or 21)
        with open(CONFIG_FILE,"w",encoding="utf-8") as _f:
            json.dump(self.ftp_config, _f, ensure_ascii=False, indent=2)
        self.ftp = FTPManager(self.ftp_config)
        self._snack("\u062a\u0645 \u062d\u0641\u0638 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u2713")

    def test_connection(self):
        self._snack("\u062c\u0627\u0631\u064a \u0627\u062e\u062a\u0628\u0627\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644...")
        def _bg():
            ok, msg = self.ftp.test()
            self._ftp_ok = ok
            Clock.schedule_once(lambda dt: self._snack(msg), 0)
            Clock.schedule_once(lambda dt: self._update_status_bar(), 0)
        threading.Thread(target=_bg, daemon=True).start()


if __name__ == "__main__":
    ContactApp().run()
