# يجب تثبيت المكتبات التالية ليعمل هذا الكود:
# pip install kivy kivymd arabic-reshaper python-bidi

from kivy.config import Config
# محاكاة حجم شاشة الموبايل أثناء الاختبار على الكمبيوتر
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.core.window import Window
from kivy.metrics import dp

import arabic_reshaper
from bidi.algorithm import get_display

# --- إعداد الخط العربي ---
# ضع اسم ملف الخط الذي ستقوم بتحميله هنا
ARABIC_FONT = "Cairo-Bold.ttf" 

def render_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

class ConvoyApp(MDApp):
    def build(self):
        Window.softinput_mode = "below_target"
        
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        screen = MDScreen()

        layout = MDBoxLayout(
            orientation="vertical",
            spacing=dp(20),
            padding=dp(30),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            size_hint_y=None,
            adaptive_height=True
        )

        # 1. عنوان التطبيق (تم إضافة font_name)
        title_label = MDLabel(
            text=render_arabic("تطبيق القافلة (Convoy)"),
            halign="center",
            theme_text_color="Primary",
            font_style="H4",
            size_hint_y=None,
            height=dp(50),
            font_name=ARABIC_FONT  # ربط الخط
        )

        # 2. حقل إدخال رقم الهاتف (تم إضافة font_name_hint_text و font_name)
        self.phone_input = MDTextField(
            hint_text=render_arabic("رقم الهاتف"),
            icon_right="phone",
            mode="rectangle",
            size_hint_x=1,
            input_filter="int",
            font_name=ARABIC_FONT,
            font_name_hint_text=ARABIC_FONT # لضمان ظهور النص الإرشادي بشكل صحيح
        )

        # 3. حقل إدخال كلمة المرور
        self.password_input = MDTextField(
            hint_text=render_arabic("كلمة المرور"),
            icon_right="eye-off",
            mode="rectangle",
            size_hint_x=1,
            password=True,
            font_name=ARABIC_FONT,
            font_name_hint_text=ARABIC_FONT
        )

        # 4. زر الدخول (تم إضافة font_name)
        login_button = MDRaisedButton(
            text=render_arabic("تسجيل الدخول"),
            pos_hint={"center_x": 0.5},
            size_hint_x=1,
            height=dp(50),
            font_name=ARABIC_FONT, # ربط الخط
            on_release=self.on_login_click
        )

        layout.add_widget(title_label)
        layout.add_widget(self.phone_input)
        layout.add_widget(self.password_input)
        layout.add_widget(login_button)

        screen.add_widget(layout)
        return screen

    def on_login_click(self, instance):
        print("Phone:", self.phone_input.text)
        print("Password:", self.password_input.text)

if __name__ == "__main__":
    ConvoyApp().run()
