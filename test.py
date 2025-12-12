import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import tempfile
import time
from collections import defaultdict
from fpdf import FPDF
import warnings
import hashlib
from pathlib import Path
warnings.filterwarnings('ignore')

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
    .present-box {
        background-color: #e8f5e9;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #c8e6c9;
        margin: 10px 0;
    }
    .employee-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .notes-section {
        background-color: #fffde7;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #ffd600;
        margin: 10px 0;
    }
    .status-present {
        color: #28a745;
        font-weight: bold;
        font-size: 1.1em;
    }
    .status-absent {
        color: #007bff;
        font-weight: bold;
        font-size: 1.1em;
    }
    .status-old-present {
        color: #fd7e14;
        font-weight: bold;
        font-size: 1.1em;
    }
    .present-now-badge {
        background-color: #4CAF50;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        display: inline-block;
        margin-left: 10px;
    }
    .refresh-btn {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 8px 15px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
    }
    .section-title {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 15px 0;
        font-weight: bold;
    }
    .dataframe {
        font-size: 0.9em;
    }
    .stSelectbox > div > div {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

class OneDriveManager:
    """محاكاة لتخزين OneDrive محلياً"""
    
    def __init__(self):
        # مجلدات محاكاة لـ OneDrive
        self.employees_folder = "OneDrive_Employees"
        self.attendance_folder = "OneDrive_Attendance"
        self.reports_folder = "OneDrive_Reports"
        
        # إنشاء المجلدات إذا لم تكن موجودة
        for folder in [self.employees_folder, self.attendance_folder, self.reports_folder]:
            os.makedirs(folder, exist_ok=True)
    
    # === إدارة الموظفين ===
    
    def save_employee(self, emp_id, data):
        """حفظ بيانات موظف في ملف منفصل"""
        file_path = os.path.join(self.employees_folder, f"{emp_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def load_employee(self, emp_id):
        """تحميل بيانات موظف"""
        file_path = os.path.join(self.employees_folder, f"{emp_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_all_employees(self):
        """الحصول على جميع الموظفين"""
        employees = {}
        if os.path.exists(self.employees_folder):
            for file in os.listdir(self.employees_folder):
                if file.endswith('.json'):
                    emp_id = file.replace('.json', '')
                    try:
                        with open(os.path.join(self.employees_folder, file), 'r', encoding='utf-8') as f:
                            employees[emp_id] = json.load(f)
                    except:
                        continue
        return employees
    
    def delete_employee(self, emp_id):
        """حذف ملف الموظف"""
        file_path = os.path.join(self.employees_folder, f"{emp_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # === إدارة الحضور ===
    
    def save_attendance_record(self, emp_id, date, record):
        """حفظ سجل حضور لموظف في تاريخ معين"""
        # إنشاء مجلد خاص بالموظف إذا لم يكن موجوداً
        emp_attendance_folder = os.path.join(self.attendance_folder, emp_id)
        os.makedirs(emp_attendance_folder, exist_ok=True)
        
        file_path = os.path.join(emp_attendance_folder, f"{date}.json")
        
        # تحميل السجلات الحالية إذا وجدت
        existing_records = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_records = json.load(f)
        
        # إضافة السجل الجديد
        existing_records.append(record)
        
        # حفظ الملف
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, indent=4, ensure_ascii=False)
    
    def update_attendance_record(self, emp_id, date, record_index, updated_record):
        """تحديث سجل حضور معين"""
        emp_attendance_folder = os.path.join(self.attendance_folder, emp_id)
        file_path = os.path.join(emp_attendance_folder, f"{date}.json")
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            if 0 <= record_index < len(records):
                records[record_index] = updated_record
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(records, f, indent=4, ensure_ascii=False)
                return True
        return False
    
    def get_attendance_records(self, emp_id, date=None):
        """الحصول على سجلات حضور موظف"""
        emp_attendance_folder = os.path.join(self.attendance_folder, emp_id)
        
        if not os.path.exists(emp_attendance_folder):
            return {}
        
        if date:
            # سجلات تاريخ معين
            file_path = os.path.join(emp_attendance_folder, f"{date}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return {date: json.load(f)}
            return {}
        else:
            # جميع السجلات
            all_records = {}
            for file in sorted(os.listdir(emp_attendance_folder)):
                if file.endswith('.json'):
                    date_str = file.replace('.json', '')
                    try:
                        with open(os.path.join(emp_attendance_folder, file), 'r', encoding='utf-8') as f:
                            all_records[date_str] = json.load(f)
                    except:
                        continue
            return all_records
    
    def get_today_present_employees(self):
        """الحصول على الموظفين الحاضرين اليوم"""
        today = datetime.now().strftime('%Y-%m-%d')
        present_employees = []
        
        all_employees = self.get_all_employees()
        
        for emp_id, emp_data in all_employees.items():
            today_records = self.get_attendance_records(emp_id, today)
            
            if today in today_records:
                records = today_records[today]
                for record in records:
                    if record.get('check_in') and not record.get('check_out'):
                        # إضافة الملاحظات إذا كانت موجودة
                        record['emp_id'] = emp_id
                        record['emp_name'] = emp_data.get('name', 'غير معروف')
                        record['department'] = emp_data.get('department', '')
                        present_employees.append(record)
        
        return present_employees
    
    def get_daily_report_data(self, date):
        """الحصول على بيانات التقرير اليومي"""
        report_data = []
        total_hours_day = 0
        total_salary_day = 0
        
        all_employees = self.get_all_employees()
        
        for emp_id, emp_data in all_employees.items():
            date_records = self.get_attendance_records(emp_id, date)
            
            if date in date_records:
                emp_name = emp_data.get('name', 'غير معروف')
                monthly_salary = emp_data.get('monthly_salary', 0)
                hourly_rate = monthly_salary / 26 if monthly_salary else 0
                emp_total_hours = 0
                
                for i, record in enumerate(date_records[date], 1):
                    check_in = record.get('check_in', '')
                    check_out = record.get('check_out', '')
                    notes = record.get('notes', '')
                    
                    hours = 0
                    salary = 0
                    if check_in and check_out:
                        try:
                            time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                            time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                            delta = time_out - time_in
                            hours = round(delta.total_seconds() / 3600, 2)
                            emp_total_hours += hours
                            salary = round(hourly_rate * hours, 2)
                        except ValueError:
                            pass
                    
                    report_data.append({
                        'كود الموظف': f"{emp_id} ({i})",
                        'اسم الموظف': emp_name,
                        'وقت الحضور': check_in,
                        'وقت الانصراف': check_out,
                        'الساعات': hours,
                        'الراتب': salary,
                        'ملاحظات': notes
                    })
                
                if emp_total_hours > 0:
                    total_salary = round(hourly_rate * emp_total_hours, 2)
                    total_hours_day += emp_total_hours
                    total_salary_day += total_salary
                    
                    report_data.append({
                        'كود الموظف': f"{emp_id} (الإجمالي)",
                        'اسم الموظف': emp_name,
                        'وقت الحضور': "",
                        'وقت الانصراف': "",
                        'الساعات': emp_total_hours,
                        'الراتب': total_salary,
                        'ملاحظات': ""
                    })
        
        return report_data, total_hours_day, total_salary_day

class EmployeeAttendanceSystem:
    def __init__(self):
        # كلمة السر للإدارة
        self.admin_password = "a2cf1543"
        
        # مدير OneDrive
        self.od_manager = OneDriveManager()
        
        # تحميل البيانات
        self.employees = self.od_manager.get_all_employees()
    
    def save_data(self):
        """حفظ جميع البيانات"""
        # بيانات الموظفين محفوظة تلقائياً عند الإضافة/التعديل
        
        # تحديث البيانات المحملة
        self.employees = self.od_manager.get_all_employees()
    
    def calculate_hourly_rate(self, monthly_salary):
        """حساب سعر الساعة من الراتب الشهري"""
        return round(monthly_salary / 26, 2) if monthly_salary else 0
    
    def calculate_salary(self, hourly_rate, hours):
        """حساب الراتب من سعر الساعة وعدد الساعات"""
        return round(hourly_rate * hours, 2) if hourly_rate and hours else 0
    
    def has_open_checkin(self, emp_id):
        """التحقق من وجود حضور مفتوح (بدون انصراف) للموظف"""
        today = datetime.now().strftime('%Y-%m-%d')
        today_records = self.od_manager.get_attendance_records(emp_id, today)
        
        if today in today_records:
            records = today_records[today]
            for record in records:
                if record.get('check_in') and not record.get('check_out'):
                    return True, today
        
        # التحقق من الأيام السابقة
        all_records = self.od_manager.get_attendance_records(emp_id)
        for date, records in all_records.items():
            if date != today:
                for record in records:
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
        
        # إنشاء حقل الإدخال
        emp_id = st.text_input(
            "كود الموظف", 
            key="emp_login_id",
            value=st.session_state.temp_emp_id
        )
        
        # تحديث القيمة في session_state
        st.session_state.temp_emp_id = emp_id
        
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
    if emp_id and emp_id in system.employees:
        emp_name = system.employees[emp_id]['name']
        
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
                
                # زر الانصراف مع ملاحظات
                with st.form(key=f"checkout_form_{emp_id}"):
                    notes = st.text_area("ملاحظات الانصراف (اختياري)", key=f"notes_checkout_{emp_id}")
                    if st.form_submit_button("تسجيل الانصراف", type="primary"):
                        check_out_employee_auto(system, emp_id, open_date, notes)
            else:
                # متحضر من يوم سابق
                st.markdown('<div class="warning-box">'
                           '<strong>الحالة:</strong> <span class="status-old-present">متحضر من يوم سابق</span><br>'
                           '<strong>التاريخ:</strong> ' + open_date +
                           '</div>', unsafe_allow_html=True)
                
                # زر الانصراف مع ملاحظات
                with st.form(key=f"checkout_old_form_{emp_id}"):
                    notes = st.text_area("ملاحظات الانصراف (اختياري)", key=f"notes_checkout_old_{emp_id}")
                    if st.form_submit_button("تسجيل الانصراف (إغلاق الجلسة القديمة)", type="primary"):
                        check_out_employee_auto(system, emp_id, open_date, notes)
        else:
            # منصرف
            st.markdown('<div class="info-box">'
                       '<strong>الحالة:</strong> <span class="status-absent">منصرف</span>' +
                       '</div>', unsafe_allow_html=True)
            
            # زر الحضور مع ملاحظات
            with st.form(key=f"checkin_form_{emp_id}"):
                notes = st.text_area("ملاحظات الحضور (اختياري)", key=f"notes_checkin_{emp_id}")
                if st.form_submit_button("تسجيل الحضور", type="primary"):
                    check_in_employee_auto(system, emp_id, notes)
    elif emp_id:
        st.warning("⚠️ كود الموظف غير مسجل")

def check_in_employee_auto(system, emp_id, notes=""):
    """تسجيل الحضور تلقائياً"""
    with st.spinner("جاري تسجيل الحضور..."):
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        record = {
            'check_in': now,
            'check_out': '',
            'notes_checkin': notes,
            'notes_checkout': ''
        }
        
        system.od_manager.save_attendance_record(emp_id, today, record)
        st.success("✅ تم تسجيل الحضور بنجاح")
        time.sleep(1)
        st.rerun()

def check_out_employee_auto(system, emp_id, open_date, notes=""):
    """تسجيل الانصراف تلقائياً"""
    with st.spinner("جاري تسجيل الانصراف..."):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # الحصول على سجلات اليوم
        records = system.od_manager.get_attendance_records(emp_id, open_date)
        
        if open_date in records:
            # البحث عن السجل المفتوح
            for i, record in enumerate(records[open_date]):
                if record.get('check_in') and not record.get('check_out'):
                    # تحديث السجل
                    updated_record = record.copy()
                    updated_record['check_out'] = now
                    updated_record['notes_checkout'] = notes
                    
                    # حفظ التحديث
                    system.od_manager.update_attendance_record(emp_id, open_date, i, updated_record)
                    
                    # إظهار رسالة نجاح
                    if open_date != today:
                        st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {open_date}")
                    else:
                        st.success("✅ تم تسجيل الانصراف بنجاح")
                    
                    time.sleep(1)
                    st.rerun()
                    return
        
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
                with st.form(key=f"main_checkout_form_{emp_id}"):
                    notes = st.text_area("ملاحظات الانصراف", key=f"main_notes_checkout_{emp_id}")
                    if st.form_submit_button("🔄 تسجيل الانصراف", type="primary"):
                        check_out_employee_main(system, emp_id, open_date, notes)
            else:
                with st.form(key=f"main_checkin_form_{emp_id}"):
                    notes = st.text_area("ملاحظات الحضور", key=f"main_notes_checkin_{emp_id}")
                    if st.form_submit_button("✅ تسجيل الحضور", type="primary"):
                        check_in_employee_main(system, emp_id, notes)

def get_last_checkin_time(system, emp_id, date):
    """الحصول على آخر وقت حضور"""
    records = system.od_manager.get_attendance_records(emp_id, date)
    if date in records:
        for record in reversed(records[date]):
            if record.get('check_in') and not record.get('check_out'):
                try:
                    dt = datetime.strptime(record['check_in'], '%Y-%m-%d %H:%M:%S')
                    return dt.strftime('%I:%M %p')
                except ValueError:
                    return record['check_in']
    return "غير معروف"

def check_in_employee_main(system, emp_id, notes=""):
    """تسجيل الحضور من الصفحة الرئيسية"""
    with st.spinner("جاري تسجيل الحضور..."):
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        record = {
            'check_in': now,
            'check_out': '',
            'notes_checkin': notes,
            'notes_checkout': ''
        }
        
        system.od_manager.save_attendance_record(emp_id, today, record)
        st.success("✅ تم تسجيل الحضور بنجاح")
        st.rerun()

def check_out_employee_main(system, emp_id, open_date, notes=""):
    """تسجيل الانصراف من الصفحة الرئيسية"""
    with st.spinner("جاري تسجيل الانصراف..."):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        records = system.od_manager.get_attendance_records(emp_id, open_date)
        
        if open_date in records:
            for i, record in enumerate(records[open_date]):
                if record.get('check_in') and not record.get('check_out'):
                    updated_record = record.copy()
                    updated_record['check_out'] = now
                    updated_record['notes_checkout'] = notes
                    
                    system.od_manager.update_attendance_record(emp_id, open_date, i, updated_record)
                    
                    if open_date != today:
                        st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {open_date}")
                    else:
                        st.success("✅ تم تسجيل الانصراف بنجاح")
                    
                    st.rerun()
                    return
        
        st.error("حدث خطأ في العثور على سجل الحضور")

def show_daily_attendance(system, emp_id):
    """عرض سجل الحضور اليومي"""
    today = datetime.now().strftime('%Y-%m-%d')
    records = system.od_manager.get_attendance_records(emp_id, today)
    
    if today in records and records[today]:
        data = []
        total_hours = 0
        
        for i, record in enumerate(records[today], 1):
            check_in = record.get('check_in', '')
            check_out = record.get('check_out', '')
            notes_checkin = record.get('notes_checkin', '')
            notes_checkout = record.get('notes_checkout', '')
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
                'المدة': hours_display,
                'ملاحظات الحضور': notes_checkin,
                'ملاحظات الانصراف': notes_checkout
            })
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=300)
            st.markdown(f"**إجمالي ساعات اليوم:** {round(total_hours, 2)} ساعة")
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
        records = system.od_manager.get_attendance_records(emp_id, date)
        
        if date in records:
            day_records = records[date]
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

# ========== واجهة المدير ==========

def show_admin_page(system):
    """عرض واجهة المدير"""
    st.markdown("<h1 class='main-header'>واجهة المدير</h1>", unsafe_allow_html=True)
    
    # زر العودة
    if st.button("← تسجيل الخروج والعودة للصفحة الرئيسية"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.rerun()
    
    # تبويبات واجهة المدير
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 إدارة الموظفين", 
        "👥 الحاضرون الآن", 
        "📅 التقارير اليومية", 
        "📈 التقارير الشهرية", 
        "📁 تصدير التقارير"
    ])
    
    with tab1:
        manage_employees(system)
    
    with tab2:
        show_present_now(system)
    
    with tab3:
        daily_reports(system)
    
    with tab4:
        monthly_reports(system)
    
    with tab5:
        export_reports(system)

def manage_employees(system):
    """إدارة الموظفين"""
    st.markdown('<div class="section-title">إضافة موظف جديد</div>', unsafe_allow_html=True)
    
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
                    employee_data = {
                        'name': new_emp_name,
                        'department': new_emp_dept,
                        'monthly_salary': new_emp_salary
                    }
                    
                    system.od_manager.save_employee(new_emp_id, employee_data)
                    system.save_data()
                    st.success(f"✅ تم إضافة الموظف {new_emp_name} بنجاح")
                    st.rerun()
            else:
                st.error("يرجى إدخال كود الموظف واسمه")
    
    st.markdown('<div class="section-title">قائمة الموظفين</div>', unsafe_allow_html=True)
    
    if system.employees:
        employees_list = []
        for emp_id, emp_data in system.employees.items():
            monthly_salary = emp_data.get('monthly_salary', 0)
            hourly_rate = system.calculate_hourly_rate(monthly_salary)
            
            employees_list.append({
                'كود الموظف': emp_id,
                'اسم الموظف': emp_data['name'],
                'القسم': emp_data.get('department', ''),
                'الراتب الشهري': monthly_salary,
                'سعر الساعة': hourly_rate
            })
        
        if employees_list:
            df = pd.DataFrame(employees_list)
            st.dataframe(df, use_container_width=True, height=400)
            
            # حذف موظف
            st.markdown("#### حذف موظف")
            emp_ids = list(system.employees.keys())
            if emp_ids:
                emp_to_delete = st.selectbox("اختر موظف للحذف", options=emp_ids, key="emp_to_delete")
                
                if st.button("حذف الموظف المحدد", type="secondary", key="delete_emp_btn"):
                    if emp_to_delete:
                        system.od_manager.delete_employee(emp_to_delete)
                        system.save_data()
                        st.success(f"✅ تم حذف الموظف {emp_to_delete} بنجاح")
                        st.rerun()
    else:
        st.info("لا يوجد موظفين مسجلين")

def show_present_now(system):
    """عرض الحاضرين الآن"""
    st.markdown('<div class="section-title">👥 الموظفون الحاضرون الآن</div>', unsafe_allow_html=True)
    
    if st.button("🔄 تحديث القائمة", key="refresh_present"):
        st.rerun()
    
    present_employees = system.od_manager.get_today_present_employees()
    
    if present_employees:
        st.markdown(f"### عدد الحاضرين: {len(present_employees)}")
        
        for emp in present_employees:
            emp_id = emp['emp_id']
            emp_name = emp['emp_name']
            department = emp['department']
            checkin_time = format_time_short(emp['check_in'])
            
            with st.expander(f"{emp_name} - {department} (كود: {emp_id})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**وقت الحضور:** {checkin_time}")
                    if emp.get('notes_checkin'):
                        st.markdown(f"**ملاحظات الحضور:** {emp['notes_checkin']}")
                
                with col2:
                    # زر لإنهاء حضور الموظف (للمدير)
                    if st.button(f"إنهاء حضور {emp_name}", key=f"end_{emp_id}"):
                        # يمكن إضافة وظيفة لإنهاء الحضور من قبل المدير
                        st.info("هذه الخاصية قيد التطوير")
    
        # عرض كجدول أيضاً
        st.markdown("### جدول الحاضرين")
        table_data = []
        for emp in present_employees:
            table_data.append({
                'الكود': emp['emp_id'],
                'الاسم': emp['emp_name'],
                'القسم': emp['department'],
                'وقت الحضور': format_time_short(emp['check_in']),
                'ملاحظات': emp.get('notes_checkin', '')
            })
        
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
    else:
        st.success("🎉 لا يوجد موظفين حاضرين حالياً")

def daily_reports(system):
    """التقارير اليومية"""
    st.markdown('<div class="section-title">📅 التقرير اليومي</div>', unsafe_allow_html=True)
    
    report_date = st.date_input("تاريخ التقرير", value=datetime.now(), key="daily_report_date")
    report_date_str = report_date.strftime('%Y-%m-%d')
    
    if st.button("عرض التقرير", type="primary", key="show_daily_report"):
        with st.spinner("جاري تحميل التقرير..."):
            report_data, total_hours, total_salary = system.od_manager.get_daily_report_data(report_date_str)
            
            if report_data:
                df_report = pd.DataFrame(report_data)
                st.dataframe(df_report, use_container_width=True, height=500)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**إجمالي ساعات العمل لليوم:** {total_hours:.2f} ساعة")
                with col2:
                    st.markdown(f"**إجمالي الرواتب لليوم:** {total_salary:.2f} جنيه")
            else:
                st.info("لا توجد بيانات للحضور في هذا التاريخ")

def monthly_reports(system):
    """التقارير الشهرية"""
    st.markdown('<div class="section-title">📈 التقرير الشهري</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1), key="start_date")
        end_date = st.date_input("إلى تاريخ", value=datetime.now(), key="end_date")
    
    with col2:
        emp_id = st.selectbox("اختر الموظف", options=["الكل"] + list(system.employees.keys()), key="monthly_emp")
    
    if st.button("عرض التقرير الشهري", type="primary", key="show_monthly_report"):
        if start_date > end_date:
            st.error("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        else:
            generate_monthly_report(system, start_date, end_date, emp_id)

def generate_monthly_report(system, start_date, end_date, emp_id):
    """توليد التقرير الشهري"""
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    with st.spinner("جاري تحميل التقرير..."):
        report_data = []
        total_period_hours = 0
        total_period_salary = 0
        
        # تحديد الموظفين المطلوبين
        employees_to_report = [emp_id] if emp_id != "الكل" else list(system.employees.keys())
        
        for emp_id in employees_to_report:
            if emp_id in system.employees:
                emp_data = system.employees[emp_id]
                emp_name = emp_data.get('name', 'غير معروف')
                monthly_salary = emp_data.get('monthly_salary', 0)
                hourly_rate = system.calculate_hourly_rate(monthly_salary)
                
                current_date = start_date
                emp_total_hours = 0
                
                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    records = system.od_manager.get_attendance_records(emp_id, date_str)
                    
                    if date_str in records:
                        day_total = 0
                        day_notes = []
                        
                        for record in records[date_str]:
                            check_in = record.get('check_in', '')
                            check_out = record.get('check_out', '')
                            notes_checkin = record.get('notes_checkin', '')
                            notes_checkout = record.get('notes_checkout', '')
                            
                            hours = 0
                            if check_in and check_out:
                                try:
                                    time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                                    time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                                    delta = time_out - time_in
                                    hours = round(delta.total_seconds() / 3600, 2)
                                    day_total += hours
                                except ValueError:
                                    pass
                            
                            if notes_checkin:
                                day_notes.append(f"حضور: {notes_checkin}")
                            if notes_checkout:
                                day_notes.append(f"انصراف: {notes_checkout}")
                        
                        if day_total > 0:
                            day_salary = system.calculate_salary(hourly_rate, day_total)
                            emp_total_hours += day_total
                            
                            report_data.append({
                                'الكود': emp_id,
                                'الاسم': emp_name,
                                'التاريخ': date_str,
                                'الساعات': day_total,
                                'الراتب': day_salary,
                                'ملاحظات': " | ".join(day_notes) if day_notes else ""
                            })
                    
                    current_date += timedelta(days=1)
                
                if emp_total_hours > 0:
                    emp_total_salary = system.calculate_salary(hourly_rate, emp_total_hours)
                    total_period_hours += emp_total_hours
                    total_period_salary += emp_total_salary
                    
                    report_data.append({
                        'الكود': emp_id,
                        'الاسم': f"{emp_name} (الإجمالي)",
                        'التاريخ': f"{start_date_str} إلى {end_date_str}",
                        'الساعات': emp_total_hours,
                        'الراتب': emp_total_salary,
                        'ملاحظات': ""
                    })
        
        if report_data:
            df_report = pd.DataFrame(report_data)
            st.dataframe(df_report, use_container_width=True, height=500)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**إجمالي ساعات العمل للفترة:** {total_period_hours:.2f} ساعة")
            with col2:
                st.markdown(f"**إجمالي الرواتب للفترة:** {total_period_salary:.2f} جنيه")
        else:
            st.info("لا توجد بيانات للحضور في الفترة المحددة")

def export_reports(system):
    """تصدير التقارير"""
    st.markdown('<div class="section-title">📁 تصدير التقارير</div>', unsafe_allow_html=True)
    
    export_type = st.radio("نوع التقرير", ["تقرير يومي", "تقرير شهري"], horizontal=True)
    
    if export_type == "تقرير يومي":
        report_date = st.date_input("تاريخ التقرير", value=datetime.now(), key="export_daily_date")
        report_date_str = report_date.strftime('%Y-%m-%d')
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("تصدير كـ PDF", type="primary", key="export_pdf_daily"):
                export_daily_pdf(system, report_date_str)
        with col2:
            if st.button("تصدير كـ Excel", type="secondary", key="export_excel_daily"):
                export_daily_excel(system, report_date_str)
    
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1), key="export_start_date")
            end_date = st.date_input("إلى تاريخ", value=datetime.now(), key="export_end_date")
        with col2:
            emp_id = st.selectbox("اختر الموظف", options=["الكل"] + list(system.employees.keys()), key="export_emp_id")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("تصدير كـ PDF", type="primary", key="export_pdf_monthly"):
                export_monthly_pdf(system, start_date, end_date, emp_id)
        with col2:
            if st.button("تصدير كـ Excel", type="secondary", key="export_excel_monthly"):
                export_monthly_excel(system, start_date, end_date, emp_id)

def export_daily_pdf(system, date_str):
    """تصدير التقرير اليومي كـ PDF"""
    report_data, total_hours, total_salary = system.od_manager.get_daily_report_data(date_str)
    
    if not report_data:
        st.error("لا توجد بيانات للتاريخ المحدد")
        return
    
    pdf = FPDF()
    pdf.add_page()
    
    # إضافة النص العربي
    try:
        pdf.add_font('Arial', '', 'arial.ttf', uni=True)
        pdf.set_font('Arial', '', 12)
    except:
        pdf.set_font('Arial', '', 12)
    
    pdf.cell(0, 10, f"تقرير الحضور اليومي - {date_str}", 0, 1, 'C')
    pdf.ln(10)
    
    # عناوين الأعمدة
    col_widths = [25, 35, 35, 35, 15, 15, 25]
    headers = ['كود الموظف', 'اسم الموظف', 'وقت الحضور', 'وقت الانصراف', 'الساعات', 'الراتب', 'ملاحظات']
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
    pdf.ln()
    
    # البيانات
    for row in report_data:
        if "الإجمالي" in str(row['كود الموظف']):
            continue
            
        pdf.cell(col_widths[0], 10, str(row['كود الموظف']), 1, 0, 'C')
        pdf.cell(col_widths[1], 10, str(row['اسم الموظف']), 1, 0, 'C')
        pdf.cell(col_widths[2], 10, str(row['وقت الحضور']), 1, 0, 'C')
        pdf.cell(col_widths[3], 10, str(row['وقت الانصراف']), 1, 0, 'C')
        pdf.cell(col_widths[4], 10, str(row['الساعات']), 1, 0, 'C')
        pdf.cell(col_widths[5], 10, str(row['الراتب']), 1, 0, 'C')
        pdf.cell(col_widths[6], 10, str(row['ملاحظات']), 1, 0, 'C')
        pdf.ln()
    
    # إجمالي
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(150, 10, "الإجمالي:", 1, 0, 'R')
    pdf.cell(15, 10, f"{total_hours:.1f}", 1, 0, 'C')
    pdf.cell(15, 10, f"{total_salary:.1f}", 1, 0, 'C')
    pdf.cell(25, 10, "", 1, 0, 'C')
    
    # حفظ الملف
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        pdf.output(tmp_file.name)
        
        with open(tmp_file.name, 'rb') as file:
            st.download_button(
                label="⬇️ تحميل PDF",
                data=file,
                file_name=f"تقرير_حضور_{date_str}.pdf",
                mime="application/pdf",
                key="download_pdf_daily"
            )
    
    st.success("✅ تم إنشاء التقرير بنجاح")

def export_daily_excel(system, date_str):
    """تصدير التقرير اليومي كـ Excel"""
    report_data, total_hours, total_salary = system.od_manager.get_daily_report_data(date_str)
    
    if not report_data:
        st.error("لا توجد بيانات للتاريخ المحدد")
        return
    
    # تحويل البيانات إلى DataFrame
    df = pd.DataFrame(report_data)
    
    # إضافة صف الإجمالي
    total_row = {
        'كود الموظف': 'الإجمالي',
        'اسم الموظف': '',
        'وقت الحضور': '',
        'وقت الانصراف': '',
        'الساعات': total_hours,
        'الراتب': total_salary,
        'ملاحظات': ''
    }
    df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    
    # إنشاء ملف Excel مؤقت
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        df.to_excel(tmp_file.name, index=False, engine='openpyxl')
        
        with open(tmp_file.name, 'rb') as file:
            st.download_button(
                label="⬇️ تحميل Excel",
                data=file,
                file_name=f"تقرير_حضور_{date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_daily"
            )
    
    st.success("✅ تم إنشاء التقرير بنجاح")

def export_monthly_pdf(system, start_date, end_date, emp_id):
    """تصدير التقرير الشهري كـ PDF"""
    st.info("خاصية التصدير الشهري كـ PDF قيد التطوير")

def export_monthly_excel(system, start_date, end_date, emp_id):
    """تصدير التقرير الشهري كـ Excel"""
    st.info("خاصية التصدير الشهري كـ Excel قيد التطوير")

if __name__ == "__main__":
    main()
