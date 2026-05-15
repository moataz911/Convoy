import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
import arabic_reshaper  # فقط هذه المكتبة، بدون bidi

# دالة مساعدة لعرض النص العربي (بدون get_display)
def reshape_arabic(text):
    try:
        return arabic_reshaper.reshape(text)
    except:
        return text

class DataTable(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        self.add_row('الاسم', 'القيمة')  # رأس الجدول

    def add_row(self, name, value):
        label_name = Label(text=reshape_arabic(name), size_hint_y=None, height=40)
        label_value = Label(text=reshape_arabic(value), size_hint_y=None, height=40)
        self.add_widget(label_name)
        self.add_widget(label_value)
        self.height += 40

class ConvoyApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')
        
        # زر لجلب البيانات
        self.fetch_button = Button(text=reshape_arabic('جلب البيانات'), size_hint_y=None, height=50)
        self.fetch_button.bind(on_press=self.fetch_heavy_data)
        self.layout.add_widget(self.fetch_button)
        
        # منطقة عرض الجدول مع تمرير
        scroll = ScrollView()
        self.table = DataTable()
        scroll.add_widget(self.table)
        self.layout.add_widget(scroll)
        
        return self.layout
    
    def fetch_heavy_data(self, instance):
        # محاكاة جلب بيانات (قللنا العدد لتجنب crash الذاكرة)
        self.table.clear_widgets()
        # إعادة إضافة رأس الجدول
        self.table.add_row('الاسم', 'القيمة')
        
        # توليد 500 سجل فقط بدلاً من 5000 لتجنب استنزاف الذاكرة
        for i in range(1, 501):
            name = f"عنصر {i}"
            value = f"قيمة {i}"
            self.table.add_row(name, value)
        
        # يمكن إضافة رسالة تأكيد
        self.layout.add_widget(Label(text=reshape_arabic('تم تحميل البيانات!'), size_hint_y=None, height=30))

if __name__ == '__main__':
    ConvoyApp().run()
