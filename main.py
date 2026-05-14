import arabic_reshaper
from bidi.algorithm import get_display
import os
import time
import threading

from kivy.config import Config
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout

# -------------------------------------------------------------------
# 1. إعدادات اللغة العربية والخطوط
# -------------------------------------------------------------------
FONT_FILENAME = "Cairo-Bold.ttf" 
current_directory = os.path.dirname(os.path.abspath(__file__))
ARABIC_FONT = os.path.join(current_directory, FONT_FILENAME)

if not os.path.exists(ARABIC_FONT):
    print(f"CRITICAL WARNING: Arabic font file NOT FOUND at: {ARABIC_FONT}")
    ARABIC_FONT = "Roboto"

def render_arabic(text):
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        print(f"Error rendering Arabic text: {e}")
        return text

# -------------------------------------------------------------------
# 2. تصميم الواجهات باستخدام لغة KV (أفضل وأسرع أداءً لـ RecycleView)
# -------------------------------------------------------------------
KV = '''
<DataItem>:
    orientation: "vertical"
    padding: dp(15)
    spacing: dp(5)
    size_hint_y: None
    height: dp(85)
    md_bg_color: 0.95, 0.95, 0.95, 1
    radius: [15,]
    
    MDLabel:
        text: root.title
        font_name: app.arabic_font
        theme_text_color: "Primary"
        halign: "right"
        font_style: "H6"
    
    MDLabel:
        text: root.subtitle
        font_name: app.arabic_font
        theme_text_color: "Secondary"
        halign: "right"

<DataScreen>:
    MDBoxLayout:
        orientation: "vertical"
        
        # شريط العنوان العلوي (مخصص لدعم العربية بشكل مثالي)
        MDBoxLayout:
            size_hint_y: None
            height: dp(56)
            md_bg_color: app.theme_cls.primary_color
            padding: dp(10)
            
            MDIconButton:
                icon: "logout"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                pos_hint: {"center_y": 0.5}
                on_release: app.logout()
                
            MDLabel:
                text: app.render_arabic("قائمة البيانات الضخمة (RecycleView)")
                font_name: app.arabic_font
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                halign: "right"
                font_style: "H6"
                pos_hint: {"center_y": 0.5}

        # أداة RecycleView لعرض ملايين البيانات بدون تجميد
        RecycleView:
            id: data_list
            viewclass: 'DataItem'
            RecycleBoxLayout:
                default_size: None, dp(85)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(10)
                padding: dp(15)
'''

Builder.load_string(KV)

# -------------------------------------------------------------------
# 3. الفئات البرمجية للواجهات
# -------------------------------------------------------------------
class DataItem(MDBoxLayout):
    """عنصر واحد في القائمة (بطاقة بيانات)"""
    title = StringProperty()
    subtitle = StringProperty()

class LoginScreen(Screen):
    """شاشة تسجيل الدخول"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = MDBoxLayout(
            orientation="vertical", spacing=dp(20), padding=dp(30),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            size_hint_y=None, adaptive_height=True
        )

        title_label = MDLabel(
            text=render_arabic("تطبيق القافلة (Convoy)"), halign="center",
            theme_text_color="Primary", font_style="H4",
            size_hint_y=None, height=dp(50), font_name=ARABIC_FONT
        )

        self.phone_input = MDTextField(
            hint_text=render_arabic("رقم الهاتف"), icon_right="phone", mode="rectangle",
            size_hint_x=1, input_filter="int", font_name=ARABIC_FONT, font_name_hint_text=ARABIC_FONT
        )

        self.password_input = MDTextField(
            hint_text=render_arabic("كلمة المرور"), icon_right="eye-off", mode="rectangle",
            size_hint_x=1, password=True, font_name=ARABIC_FONT, font_name_hint_text=ARABIC_FONT
        )

        self.login_button = MDRaisedButton(
            text=render_arabic("تسجيل الدخول وجلب البيانات"), pos_hint={"center_x": 0.5},
            size_hint_x=1, height=dp(50), font_name=ARABIC_FONT,
            on_release=self.start_login_process
        )

        self.status_label = MDLabel(
            text="", halign="center", theme_text_color="Error",
            font_name=ARABIC_FONT, size_hint_y=None, height=dp(30)
        )

        layout.add_widget(title_label)
        layout.add_widget(self.phone_input)
        layout.add_widget(self.password_input)
        layout.add_widget(self.login_button)
        layout.add_widget(self.status_label)
        self.add_widget(layout)

    def start_login_process(self, instance):
        phone = self.phone_input.text.strip()
        password = self.password_input.text.strip()

        if not phone or not password:
            self.status_label.theme_text_color = "Error"
            self.status_label.text = render_arabic("الرجاء إدخال جميع البيانات")
            return

        self.status_label.theme_text_color = "Primary"
        self.status_label.text = render_arabic("جاري جلب آلاف السجلات...")
        self.login_button.disabled = True
        
        # تشغيل خيط منفصل لجلب البيانات
        threading.Thread(target=self.fetch_heavy_data, daemon=True).start()

    def fetch_heavy_data(self):
        """محاكاة جلب 5000 سجل من السيرفر"""
        try:
            time.sleep(2) # محاكاة وقت الاتصال بالإنترنت
            
            huge_data_list = []
            # توليد 5000 سجل بيانات كمثال للتجربة
            for i in range(1, 5001):
                # نطبق اللغة العربية هنا قبل إرسالها للـ RecycleView لضمان الأداء
                huge_data_list.append({
                    "title": render_arabic(f"سجل شحنة رقم #{i}"),
                    "subtitle": render_arabic(f"الحالة: قيد التوصيل - العميل: أحمد {i}")
                })

            # نعود للخيط الرئيسي لتحديث الواجهة (يمنع الانهيار)
            Clock.schedule_once(lambda dt: self.on_data_success(huge_data_list))

        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_data_error("حدث خطأ في الاتصال"))

    def on_data_success(self, data):
        self.status_label.text = ""
        self.login_button.disabled = False
        self.phone_input.text = ""
        self.password_input.text = ""
        # إرسال البيانات للشاشة الأخرى والانتقال إليها
        MDApp.get_running_app().show_data_screen(data)

    def on_data_error(self, error_message):
        self.status_label.theme_text_color = "Error"
        self.status_label.text = render_arabic(error_message)
        self.login_button.disabled = False

class DataScreen(Screen):
    """شاشة عرض البيانات الضخمة"""
    pass

# -------------------------------------------------------------------
# 4. التطبيق الرئيسي (إدارة الشاشات)
# -------------------------------------------------------------------
class ConvoyApp(MDApp):
    arabic_font = ARABIC_FONT

    def render_arabic(self, text):
        return render_arabic(text)

    def build(self):
        Window.softinput_mode = "below_target"
        self.theme_cls.primary_palette = "Blue"
        
        # إعداد مدير الشاشات
        self.sm = ScreenManager(transition=FadeTransition())
        
        self.login_screen = LoginScreen(name="login")
        self.data_screen = DataScreen(name="data")
        
        self.sm.add_widget(self.login_screen)
        self.sm.add_widget(self.data_screen)
        
        return self.sm

    def show_data_screen(self, data):
        # تغذية الـ RecycleView بالبيانات
        self.data_screen.ids.data_list.data = data
        # الانتقال للشاشة
        self.sm.current = "data"

    def logout(self):
        # تفريغ البيانات للعودة لتسجيل الدخول
        self.data_screen.ids.data_list.data = []
        self.sm.current = "login"

if __name__ == "__main__":
    ConvoyApp().run()
