import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict
from fpdf import FPDF
import tempfile
import time

# إعداد الصفحة
st.set_page_config(
    page_title="نظام حضور وانصراف الموظفين",
    page_icon="👥",
    layout="wide"
)

# تخصيص CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2c3e50;
        padding: 1rem;
    }
    .stButton > button {
        width: 100%;
        font-weight: bold;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #ffeaa7;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #bee5eb;
        margin: 10px 0;
    }
    .status-present {
        color: #28a745;
        font-weight: bold;
    }
    .status-absent {
        color: #007bff;
        font-weight: bold;
    }
    .status-old-present {
        color: #fd7e14;
        font-weight: bold;
    }
    /* تحسين أداء الجداول */
    .stDataFrame {
        font-size: 0.9em;
    }
    /* تخصيص حقول الإدخال */
    .stTextInput > div > div > input {
        font-size: 16px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

class EmployeeAttendanceSystem:
    def __init__(self):
        # كلمة السر للإدارة
        self.admin_password = "a2cf1543"
        
        # إنشاء مجلد البيانات إذا لم يكن موجوداً
        if not os.path.exists('data'):
            os.makedirs('data')
        
        # تحميل البيانات - استخدام cache لتحسين الأداء
        self.load_data_cached()
    
    @st.cache_resource(ttl=300)  # تخزين في الذاكرة لمدة 5 دقائق
    def load_data_cached(_self):
        """تحميل البيانات مع التخزين المؤقت"""
        return _self._load_data()
    
    def _load_data(self):
        """تحميل البيانات الفعلي"""
        data_dict = {
            'employees': {},
            'attendance': defaultdict(lambda: defaultdict(list))
        }
        
        try:
            with open('data/employees.json', 'r', encoding='utf-8') as f:
                data_dict['employees'] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data_dict['employees'] = {}
        
        try:
            with open('data/attendance.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                data_dict['attendance'] = self.convert_old_data(old_data)
        except (FileNotFoundError, json.JSONDecodeError):
            data_dict['attendance'] = defaultdict(lambda: defaultdict(list))
        
        return data_dict
    
    def get_data(self):
        """الحصول على البيانات المحدثة"""
        if 'cached_data' not in st.session_state:
            st.session_state.cached_data = self.load_data_cached()
        
        # تحديث البيانات كل دقيقة
        current_time = time.time()
        if 'last_update_time' not in st.session_state:
            st.session_state.last_update_time = current_time
        
        # تحديث البيانات إذا مرت أكثر من 60 ثانية
        if current_time - st.session_state.last_update_time > 60:
            st.session_state.cached_data = self.load_data_cached()
            st.session_state.last_update_time = current_time
        
        return st.session_state.cached_data
    
    @property
    def employees(self):
        """الحصول على بيانات الموظفين"""
        data = self.get_data()
        return data['employees']
    
    @property
    def attendance(self):
        """الحصول على بيانات الحضور"""
        data = self.get_data()
        return data['attendance']
    
    def convert_old_data(self, old_data):
        """تحويل البيانات القديمة إلى الهيكل الجديد"""
        new_data = defaultdict(lambda: defaultdict(list))
        for date, employees in old_data.items():
            for emp_id, records in employees.items():
                if isinstance(records, dict):
                    if 'check_in' in records:
                        new_data[date][emp_id].append({
                            'check_in': records['check_in'],
                            'check_out': records.get('check_out', '')
                        })
                elif isinstance(records, list):
                    for record in records:
                        if 'check_in' in record:
                            new_data[date][emp_id].append({
                                'check_in': record['check_in'],
                                'check_out': record.get('check_out', '')
                            })
        return new_data
    
    def save_data(self):
        """حفظ البيانات في الملفات"""
        with open('data/employees.json', 'w', encoding='utf-8') as f:
            json.dump(self.employees, f, indent=4, ensure_ascii=False)
        
        with open('data/attendance.json', 'w', encoding='utf-8') as f:
            normal_dict = {date: dict(employees) for date, employees in self.attendance.items()}
            json.dump(normal_dict, f, indent=4, ensure_ascii=False)
        
        # تحديث البيانات المخزنة مؤقتاً
        st.session_state.cached_data = self._load_data()
        st.session_state.last_update_time = time.time()
    
    def calculate_hourly_rate(self, monthly_salary):
        """حساب سعر الساعة من الراتب الشهري"""
        return round(monthly_salary / 26, 2) if monthly_salary else 0
    
    def calculate_salary(self, hourly_rate, hours):
        """حساب الراتب من سعر الساعة وعدد الساعات"""
        return round(hourly_rate * hours, 2) if hourly_rate and hours else 0
    
    def has_open_checkin(self, emp_id):
        """التحقق من وجود حضور مفتوح (بدون انصراف) للموظف"""
        for date in self.attendance:
            if emp_id in self.attendance[date]:
                for record in self.attendance[date][emp_id]:
                    if record.get('check_in') and not record.get('check_out'):
                        return True, date
        return False, None

def main():
    # تهيئة النظام
    if 'system' not in st.session_state:
        st.session_state.system = EmployeeAttendanceSystem()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
    if 'employee_status_checked' not in st.session_state:
        st.session_state.employee_status_checked = False
    
    if 'current_emp_id' not in st.session_state:
        st.session_state.current_emp_id = ""
    
    system = st.session_state.system
    
    # صفحة الرئيسية (تسجيل الدخول)
    if not st.session_state.logged_in:
        show_login_page(system)
    else:
        if st.session_state.is_admin:
            show_admin_page(system)
        else:
            show_employee_page(system)

def show_login_page(system):
    """عرض صفحة تسجيل الدخول"""
    st.markdown("<h1 class='main-header'>نظام حضور وانصراف الموظفين</h1>", unsafe_allow_html=True)
    
    # استخدام أعمدة لعرض واجهة الدخول
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### دخول كموظف")
        
        # استخدام callback لتحديث الحالة
        if 'temp_emp_id' not in st.session_state:
            st.session_state.temp_emp_id = ""
        
        # إنشاء حقل الإدخال مع callback
        emp_id = st.text_input(
            "كود الموظف", 
            key="emp_login_id",
            value=st.session_state.temp_emp_id
        )
        
        # تحديث القيمة في session_state
        st.session_state.temp_emp_id = emp_id
        
        # عند تغيير الحقل، نتحقق من الحالة
        if emp_id != st.session_state.get('last_emp_id', ''):
            st.session_state.last_emp_id = emp_id
            st.session_state.employee_status_checked = False
        
        # عرض حالة الموظف تلقائياً إذا كان الكود صحيحاً
        if emp_id:
            show_employee_status_auto(system, emp_id)
        
        # زر الدخول
        if st.button("دخول كموظف", type="primary", use_container_width=True, key="emp_login_btn"):
            if emp_id in system.employees:
                st.session_state.logged_in = True
                st.session_state.is_admin = False
                st.session_state.current_emp_id = emp_id
                st.rerun()
            else:
                st.error("كود الموظف غير مسجل")
    
    with col2:
        st.markdown("### دخول كمدير")
        admin_pass = st.text_input("كلمة السر", type="password", key="admin_pass")
        
        if st.button("دخول كمدير", type="secondary", use_container_width=True):
            if admin_pass == system.admin_password:
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("كلمة السر غير صحيحة")

def show_employee_status_auto(system, emp_id):
    """عرض حالة الموظف تلقائياً"""
    if emp_id:
        # التحقق السريع من وجود الموظف
        employees_dict = system.employees
        
        if emp_id in employees_dict:
            emp_name = employees_dict[emp_id]['name']
            
            # استخدام spinner أثناء تحميل حالة الحضور
            with st.spinner("جاري التحقق من حالة الحضور..."):
                # التحقق من حالة الموظف
                has_open, open_date = system.has_open_checkin(emp_id)
                today = datetime.now().strftime('%Y-%m-%d')
                
                # عرض معلومات الموظف
                st.markdown(f"**الاسم:** {emp_name}")
                
                if has_open:
                    if open_date == today:
                        # متحضر اليوم
                        st.markdown('<div class="success-box">'
                                   '<strong>الحالة:</strong> <span class="status-present">متحضر اليوم</span><br>'
                                   '<strong>التاريخ:</strong> ' + open_date +
                                   '</div>', unsafe_allow_html=True)
                        
                        # زر الانصراف
                        col1, col2 = st.columns([3, 1])
                        with col2:
                            if st.button("تسجيل الانصراف", type="primary", key="auto_checkout"):
                                check_out_employee_auto(system, emp_id, open_date)
                    else:
                        # متحضر من يوم سابق
                        st.markdown('<div class="warning-box">'
                                   '<strong>الحالة:</strong> <span class="status-old-present">متحضر من يوم سابق</span><br>'
                                   '<strong>التاريخ:</strong> ' + open_date +
                                   '</div>', unsafe_allow_html=True)
                        
                        # زر الانصراف
                        col1, col2 = st.columns([3, 1])
                        with col2:
                            if st.button("تسجيل الانصراف", type="primary", key="auto_checkout_old"):
                                check_out_employee_auto(system, emp_id, open_date)
                else:
                    # منصرف
                    st.markdown('<div class="info-box">'
                               '<strong>الحالة:</strong> <span class="status-absent">منصرف</span>' +
                               '</div>', unsafe_allow_html=True)
                    
                    # زر الحضور
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        if st.button("تسجيل الحضور", type="primary", key="auto_checkin"):
                            check_in_employee_auto(system, emp_id)
        else:
            st.warning("⚠️ كود الموظف غير مسجل")

def check_in_employee_auto(system, emp_id):
    """تسجيل الحضور تلقائياً"""
    with st.spinner("جاري تسجيل الحضور..."):
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        system.attendance[today][emp_id].append({
            'check_in': now,
            'check_out': ''
        })
        
        system.save_data()
        
        # إظهار رسالة نجاح وإعادة التحميل
        success_msg = st.success("✅ تم تسجيل الحضور بنجاح")
        time.sleep(1)  # تأخير قصير لرؤية الرسالة
        success_msg.empty()
        st.rerun()

def check_out_employee_auto(system, emp_id, open_date):
    """تسجيل الانصراف تلقائياً"""
    with st.spinner("جاري تسجيل الانصراف..."):
        found_record = None
        
        if open_date in system.attendance and emp_id in system.attendance[open_date]:
            for record in reversed(system.attendance[open_date][emp_id]):
                if record['check_in'] and not record['check_out']:
                    found_record = record
                    break
        
        if found_record:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            found_record['check_out'] = now
            system.save_data()
            
            # إظهار رسالة نجاح
            if open_date != datetime.now().strftime('%Y-%m-%d'):
                msg = st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {open_date}")
            else:
                msg = st.success("✅ تم تسجيل الانصراف بنجاح")
            
            time.sleep(1)  # تأخير قصير لرؤية الرسالة
            msg.empty()
            st.rerun()
        else:
            st.error("حدث خطأ في العثور على سجل الحضور")

def show_employee_page(system):
    """عرض واجهة الموظف (الصفحة الرئيسية بعد الدخول)"""
    emp_id = st.session_state.current_emp_id
    
    if emp_id in system.employees:
        emp_name = system.employees[emp_id]['name']
        
        st.markdown(f"<h1 class='main-header'>مرحباً، {emp_name} ({emp_id})</h1>", unsafe_allow_html=True)
        
        # زر العودة
        if st.button("← تسجيل الخروج والعودة للصفحة الرئيسية"):
            st.session_state.logged_in = False
            st.session_state.current_emp_id = ""
            st.rerun()
        
        # عرض حالة الموظف في الصفحة الرئيسية
        show_employee_status_main(system, emp_id)
        
        # عرض سجلات الحضور
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### سجل الحضور اليومي")
            show_daily_attendance(system, emp_id)
        
        with col2:
            st.markdown("### سجل الحضور لهذا الأسبوع")
            show_weekly_attendance(system, emp_id)
    else:
        st.error("حدث خطأ في تحميل بيانات الموظف")
        if st.button("العودة للصفحة الرئيسية"):
            st.session_state.logged_in = False
            st.rerun()

def show_employee_status_main(system, emp_id):
    """عرض حالة الموظف في الصفحة الرئيسية"""
    with st.spinner("جاري تحميل الحالة الحالية..."):
        has_open, open_date = system.has_open_checkin(emp_id)
        today = datetime.now().strftime('%Y-%m-%d')
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if has_open:
                if open_date == today:
                    checkin_time = get_last_checkin_time(system, emp_id, open_date)
                    st.markdown('<div class="warning-box">'
                               '<h4>🎯 الحالة الحالية</h4>'
                               '<p><strong>الحالة:</strong> <span class="status-present">متحضر اليوم</span></p>'
                               '<p><strong>وقت الحضور:</strong> ' + checkin_time + '</p>'
                               '</div>', unsafe_allow_html=True)
                else:
                    checkin_time = get_last_checkin_time(system, emp_id, open_date)
                    st.markdown('<div class="warning-box">'
                               '<h4>🎯 الحالة الحالية</h4>'
                               '<p><strong>الحالة:</strong> <span class="status-old-present">متحضر من يوم سابق</span></p>'
                               '<p><strong>من تاريخ:</strong> ' + open_date + '</p>'
                               '<p><strong>وقت الحضور:</strong> ' + checkin_time + '</p>'
                               '</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="success-box">'
                           '<h4>🎯 الحالة الحالية</h4>'
                           '<p><strong>الحالة:</strong> <span class="status-absent">منصرف</span></p>'
                           '<p>يمكنك تسجيل الحضور عندما تبدأ عملك</p>'
                           '</div>', unsafe_allow_html=True)
        
        with col2:
            if has_open:
                if st.button("🔄 تسجيل الانصراف", type="primary", use_container_width=True, key="main_checkout"):
                    check_out_employee_main(system, emp_id, open_date)
            else:
                if st.button("✅ تسجيل الحضور", type="primary", use_container_width=True, key="main_checkin"):
                    check_in_employee_main(system, emp_id)

def get_last_checkin_time(system, emp_id, date):
    """الحصول على آخر وقت حضور"""
    if date in system.attendance and emp_id in system.attendance[date]:
        for record in reversed(system.attendance[date][emp_id]):
            if record.get('check_in') and not record.get('check_out'):
                try:
                    # تحويل الوقت إلى تنسيق مختصر
                    dt = datetime.strptime(record['check_in'], '%Y-%m-%d %H:%M:%S')
                    return dt.strftime('%I:%M %p')  # 12-hour format with AM/PM
                except ValueError:
                    return record['check_in']
    return "غير معروف"

def check_in_employee_main(system, emp_id):
    """تسجيل الحضور من الصفحة الرئيسية"""
    with st.spinner("جاري تسجيل الحضور..."):
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        system.attendance[today][emp_id].append({
            'check_in': now,
            'check_out': ''
        })
        
        system.save_data()
        st.success("✅ تم تسجيل الحضور بنجاح")
        st.rerun()

def check_out_employee_main(system, emp_id, open_date):
    """تسجيل الانصراف من الصفحة الرئيسية"""
    with st.spinner("جاري تسجيل الانصراف..."):
        found_record = None
        
        if open_date in system.attendance and emp_id in system.attendance[open_date]:
            for record in reversed(system.attendance[open_date][emp_id]):
                if record['check_in'] and not record['check_out']:
                    found_record = record
                    break
        
        if found_record:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            found_record['check_out'] = now
            system.save_data()
            
            if open_date != datetime.now().strftime('%Y-%m-%d'):
                st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {open_date}")
            else:
                st.success("✅ تم تسجيل الانصراف بنجاح")
            
            st.rerun()
        else:
            st.error("حدث خطأ في العثور على سجل الحضور")

def show_daily_attendance(system, emp_id):
    """عرض سجل الحضور اليومي"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    if today in system.attendance and emp_id in system.attendance[today]:
        records = system.attendance[today][emp_id]
        if records:
            data = []
            total_hours = 0
            
            for i, record in enumerate(records, 1):
                check_in = record.get('check_in', '')
                check_out = record.get('check_out', '')
                hours_display = ''
                
                if check_in and check_out:
                    try:
                        time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                        time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                        delta = time_out - time_in
                        hours = round(delta.total_seconds() / 3600, 2)
                        hours_display = f"{hours} ساعة"
                        total_hours += hours
                    except ValueError:
                        hours_display = ''
                
                # تنسيق الأوقات بشكل مختصر
                check_in_short = format_time_short(check_in)
                check_out_short = format_time_short(check_out)
                
                data.append({
                    'التسجيل': i,
                    'الحضور': check_in_short,
                    'الانصراف': check_out_short,
                    'المدة': hours_display
                })
            
            # إضافة صف الإجمالي
            data.append({
                'التسجيل': 'الإجمالي',
                'الحضور': '',
                'الانصراف': '',
                'المدة': f"{round(total_hours, 2)} ساعة"
            })
            
            df = pd.DataFrame(data)
            # استخدام CSS لتخصيص صف الإجمالي
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد سجلات حضور لهذا اليوم")
    else:
        st.info("لا توجد سجلات حضور لهذا اليوم")

def format_time_short(time_str):
    """تنسيق الوقت بشكل مختصر"""
    if not time_str:
        return ""
    try:
        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%I:%M %p')
    except ValueError:
        return time_str

def show_weekly_attendance(system, emp_id):
    """عرض سجل الحضور الأسبوعي"""
    data = []
    
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        
        if date in system.attendance and emp_id in system.attendance[date]:
            day_records = system.attendance[date][emp_id]
            total_hours = 0
            
            for record in day_records:
                check_in = record.get('check_in', '')
                check_out = record.get('check_out', '')
                
                if check_in and check_out:
                    try:
                        time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                        time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                        delta = time_out - time_in
                        total_hours += delta.total_seconds() / 3600
                    except ValueError:
                        pass
            
            if total_hours > 0 or day_records:
                data.append({
                    'التاريخ': date,
                    'التسجيلات': len(day_records),
                    'الساعات': round(total_hours, 2)
                })
    
    if data:
        df = pd.DataFrame(data[::-1])  # عكس الترتيب لعرض الأحدث أولاً
        st.dataframe(df, use_container_width=True, height=300)
    else:
        st.info("لا توجد سجلات حضور لهذا الأسبوع")

# باقي دوال المدير (تبقى كما هي مع بعض التحسينات)

def show_admin_page(system):
    """عرض واجهة المدير"""
    st.markdown("<h1 class='main-header'>واجهة المدير</h1>", unsafe_allow_html=True)
    
    # زر العودة
    if st.button("← تسجيل الخروج والعودة للصفحة الرئيسية"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.rerun()
    
    # تبويبات واجهة المدير مع تحسين الأداء
    tab1, tab2, tab3, tab4 = st.tabs(["📊 إدارة الموظفين", "📅 التقارير اليومية", "📈 التقارير الشهرية", "📁 تصدير التقارير"])
    
    with tab1:
        manage_employees(system)
    
    with tab2:
        daily_reports(system)
    
    with tab3:
        monthly_reports(system)
    
    with tab4:
        export_reports(system)

def manage_employees(system):
    """إدارة الموظفين"""
    st.markdown("### إضافة موظف جديد")
    
    with st.form("add_employee_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_emp_id = st.text_input("كود الموظف", key="new_emp_id")
            new_emp_name = st.text_input("اسم الموظف", key="new_emp_name")
        
        with col2:
            new_emp_dept = st.text_input("القسم", key="new_emp_dept")
            new_emp_salary = st.number_input("الراتب الشهري", min_value=0.0, value=0.0, step=100.0, key="new_emp_salary")
        
        if st.form_submit_button("إضافة موظف", type="primary"):
            if new_emp_id and new_emp_name:
                if new_emp_id in system.employees:
                    st.error("كود الموظف مسجل مسبقاً")
                else:
                    system.employees[new_emp_id] = {
                        'name': new_emp_name,
                        'department': new_emp_dept,
                        'monthly_salary': new_emp_salary
                    }
                    
                    system.save_data()
                    st.success(f"✅ تم إضافة الموظف {new_emp_name} بنجاح")
                    st.rerun()
            else:
                st.error("يرجى إدخال كود الموظف واسمه")
    
    st.markdown("---")
    st.markdown("### قائمة الموظفين")
    
    employees_dict = system.employees
    
    if employees_dict:
        # تحويل القاموس إلى قائمة للعرض
        employees_list = []
        for emp_id, emp_data in employees_dict.items():
            monthly_salary = emp_data.get('monthly_salary', 0)
            hourly_rate = system.calculate_hourly_rate(monthly_salary)
            
            employees_list.append({
                'كود الموظف': emp_id,
                'اسم الموظف': emp_data['name'],
                'القسم': emp_data.get('department', ''),
                'الراتب الشهري': monthly_salary,
                'سعر الساعة': hourly_rate
            })
        
        # عرض البيانات في جدول
        if employees_list:
            df = pd.DataFrame(employees_list)
            st.dataframe(df, use_container_width=True, height=400)
            
            # حذف موظف
            st.markdown("#### حذف موظف")
            emp_ids = list(employees_dict.keys())
            if emp_ids:
                emp_to_delete = st.selectbox("اختر موظف للحذف", options=emp_ids, key="emp_to_delete")
                
                if st.button("حذف الموظف المحدد", type="secondary", key="delete_emp_btn"):
                    if emp_to_delete:
                        del system.employees[emp_to_delete]
                        
                        # حذف سجلات الحضور للموظف
                        for date in list(system.attendance.keys()):
                            if emp_to_delete in system.attendance[date]:
                                del system.attendance[date][emp_to_delete]
                            
                            if not system.attendance[date]:
                                del system.attendance[date]
                        
                        system.save_data()
                        st.success(f"✅ تم حذف الموظف {emp_to_delete} بنجاح")
                        st.rerun()
            else:
                st.info("لا يوجد موظفين للحذف")
    else:
        st.info("لا يوجد موظفين مسجلين")

# باقي الدوال (daily_reports, monthly_reports, export_reports) تبقى كما هي
# مع إضافة @st.cache_data للجداول الكبيرة لتحسين الأداء

@st.cache_data(ttl=60)
def get_daily_report_data(system, report_date_str):
    """الحصول على بيانات التقرير اليومي مع التخزين المؤقت"""
    report_data = []
    total_hours_day = 0
    
    if report_date_str in system.attendance:
        for emp_id, records in system.attendance[report_date_str].items():
            if emp_id in system.employees:
                emp_name = system.employees[emp_id]['name']
                monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
                hourly_rate = system.calculate_hourly_rate(monthly_salary)
                emp_total_hours = 0
                
                for i, record in enumerate(records, 1):
                    check_in = record.get('check_in', '')
                    check_out = record.get('check_out', '')
                    
                    hours = 0
                    salary = 0
                    if check_in and check_out:
                        try:
                            time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                            time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                            delta = time_out - time_in
                            hours = round(delta.total_seconds() / 3600, 2)
                            emp_total_hours += hours
                            salary = system.calculate_salary(hourly_rate, hours)
                        except ValueError:
                            pass
                    
                    report_data.append({
                        'كود الموظف': f"{emp_id} ({i})",
                        'اسم الموظف': emp_name,
                        'وقت الحضور': check_in,
                        'وقت الانصراف': check_out,
                        'الساعات': hours,
                        'الراتب': salary
                    })
                
                if emp_total_hours > 0:
                    total_salary = system.calculate_salary(hourly_rate, emp_total_hours)
                    total_hours_day += emp_total_hours
                    
                    report_data.append({
                        'كود الموظف': f"{emp_id} (الإجمالي)",
                        'اسم الموظف': emp_name,
                        'وقت الحضور': "",
                        'وقت الانصراف': "",
                        'الساعات': emp_total_hours,
                        'الراتب': total_salary
                    })
    
    return report_data, total_hours_day

def daily_reports(system):
    """التقارير اليومية"""
    st.markdown("### تقرير الحضور اليومي")
    
    report_date = st.date_input("تاريخ التقرير", value=datetime.now(), key="daily_report_date")
    report_date_str = report_date.strftime('%Y-%m-%d')
    
    if st.button("عرض التقرير", type="primary", key="show_daily_report"):
        with st.spinner("جاري تحميل التقرير..."):
            report_data, total_hours = get_daily_report_data(system, report_date_str)
            
            if report_data:
                df_report = pd.DataFrame(report_data)
                st.dataframe(df_report, use_container_width=True, height=500)
                
                st.markdown(f"**إجمالي ساعات العمل لليوم:** {total_hours:.2f} ساعة")
            else:
                st.info("لا توجد بيانات للحضور في هذا التاريخ")

# باقي الدوال تبقى كما هي مع إضافة spinners لتحسين تجربة المستخدم

if __name__ == "__main__":
    main()
