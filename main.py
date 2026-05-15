import os
import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.text import LabelBase
from kivy.clock import Clock

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

# --- تسجيل الخط العربي ---
FONT_NAME = "CairoFont"

def find_font_path():
    if not os.path.isabs(__file__):
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        os.path.join(base_dir, "Cairo-Bold.ttf"),
        os.path.join(os.getcwd(), "Cairo-Bold.ttf"),
        "/system/fonts/Cairo-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def register_font():
    font_path = find_font_path()
    if font_path:
        try:
            LabelBase.register(name=FONT_NAME, fn_regular=font_path)
            print(f"Font registered from: {font_path}")
            return FONT_NAME
        except Exception as e:
            print(f"Font registration error: {e}")
    print("Cairo font not found, using default.")
    return "Roboto"

ARABIC_FONT = register_font()
def fix_arabic(text):
    if not text:
        return ""
    if not HAS_ARABIC:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        print(f"Arabic fixing error: {e}")
        return text


class DataTable(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        self.add_row(fix_arabic('الاسم'), fix_arabic('القيمة'))

    def add_row(self, name, value):
        label_name = Label(
            text=name,
            font_name=ARABIC_FONT,
            size_hint_y=None,
            height=40,
            halign='right',
            valign='middle'
        )
        label_name.bind(size=label_name.setter('text_size'))

        label_value = Label(
            text=value,
            font_name=ARABIC_FONT,
            size_hint_y=None,
            height=40,
            halign='right',
            valign='middle'
        )
        label_value.bind(size=label_value.setter('text_size'))

        self.add_widget(label_name)
        self.add_widget(label_value)


class ConvoyApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.fetch_button = Button(
            text=fix_arabic('جلب البيانات'),
            font_name=ARABIC_FONT,
            size_hint_y=None,
            height=50
        )
        self.fetch_button.bind(on_press=self.fetch_heavy_data)
        self.layout.add_widget(self.fetch_button)

        scroll = ScrollView()
        self.table = DataTable()
        scroll.add_widget(self.table)
        self.layout.add_widget(scroll)

        return self.layout

    def fetch_heavy_data(self, instance):
        self.table.clear_widgets()
        self.table.add_row(fix_arabic('الاسم'), fix_arabic('القيمة'))

        for i in range(1, 501):
            name = fix_arabic(f"عنصر {i}")
            value = fix_arabic(f"قيمة {i}")
            self.table.add_row(name, value)

        self.layout.add_widget(Label(
            text=fix_arabic('تم تحميل البيانات!'),
            font_name=ARABIC_FONT,
            size_hint_y=None,
            height=30
        ))


if __name__ == '__main__':
    ConvoyApp().run()
