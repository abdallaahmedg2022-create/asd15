import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict
from fpdf import FPDF
import tempfile

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
</style>
""", unsafe_allow_html=True)

class EmployeeAttendanceSystem:
    def __init__(self):
        # كلمة السر للإدارة
        self.admin_password = "a2cf1543"
        
        # إنشاء مجلد البيانات إذا لم يكن موجوداً
        if not os.path.exists('data'):
            os.makedirs('data')
        
        # تحميل البيانات
        self.load_data()
    
    def load_data(self):
        """تحميل بيانات الموظفين وسجلات الحضور"""
        try:
            with open('data/employees.json', 'r', encoding='utf-8') as f:
                self.employees = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.employees = {}
        
        try:
            with open('data/attendance.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                self.attendance = self.convert_old_data(old_data)
        except (FileNotFoundError, json.JSONDecodeError):
            self.attendance = defaultdict(lambda: defaultdict(list))
    
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
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "main"
    
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
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### دخول كموظف")
        emp_id = st.text_input("كود الموظف", key="emp_login_id")
        
        if st.button("دخول كموظف", type="primary", use_container_width=True):
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

def show_employee_page(system):
    """عرض واجهة الموظف"""
    st.markdown("<h1 class='main-header'>نظام الحضور والانصراف</h1>", unsafe_allow_html=True)
    
    # زر العودة
    if st.button("← العودة للصفحة الرئيسية"):
        st.session_state.logged_in = False
        st.rerun()
    
    emp_id = st.session_state.current_emp_id
    emp_name = system.employees[emp_id]['name']
    
    st.markdown(f"### مرحباً، {emp_name} ({emp_id})")
    
    # التحقق من حالة الموظف
    has_open, open_date = system.has_open_checkin(emp_id)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if has_open:
            if open_date == datetime.now().strftime('%Y-%m-%d'):
                st.markdown("""
                <div class='warning-box'>
                    <strong>الحالة:</strong> متحضر اليوم
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='warning-box'>
                    <strong>الحالة:</strong> متحضر من {open_date}
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("تسجيل الانصراف", type="primary", use_container_width=True):
                check_out_employee(system, emp_id)
        else:
            st.markdown("""
            <div class='success-box'>
                <strong>الحالة:</strong> منصرف
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("تسجيل الحضور", type="primary", use_container_width=True):
                check_in_employee(system, emp_id)
    
    with col2:
        st.markdown("### سجل الحضور اليومي")
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today in system.attendance and emp_id in system.attendance[today]:
            records = system.attendance[today][emp_id]
            data = []
            
            for i, record in enumerate(records, 1):
                check_in = record.get('check_in', '')
                check_out = record.get('check_out', '')
                hours = ''
                
                if check_in and check_out:
                    try:
                        time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                        time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                        delta = time_out - time_in
                        hours = f"{round(delta.total_seconds() / 3600, 2)} ساعة"
                    except ValueError:
                        hours = ''
                
                data.append({
                    'التسجيل': i,
                    'وقت الحضور': check_in,
                    'وقت الانصراف': check_out,
                    'المدة': hours
                })
            
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            else:
                st.info("لا توجد سجلات حضور لهذا اليوم")
        else:
            st.info("لا توجد سجلات حضور لهذا اليوم")
    
    # عرض سجل الحضور الأسبوعي
    st.markdown("### سجل الحضور لهذا الأسبوع")
    weekly_data = get_weekly_attendance(system, emp_id)
    if not weekly_data.empty:
        st.dataframe(weekly_data, use_container_width=True)
    else:
        st.info("لا توجد سجلات حضور لهذا الأسبوع")

def check_in_employee(system, emp_id):
    """تسجيل الحضور"""
    today = datetime.now().strftime('%Y-%m-%d')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    system.attendance[today][emp_id].append({
        'check_in': now,
        'check_out': ''
    })
    
    system.save_data()
    st.success("✅ تم تسجيل الحضور بنجاح")
    st.rerun()

def check_out_employee(system, emp_id):
    """تسجيل الانصراف"""
    found_record = None
    found_date = None
    
    for date in sorted(system.attendance.keys(), reverse=True):
        if emp_id in system.attendance[date]:
            for record in reversed(system.attendance[date][emp_id]):
                if record['check_in'] and not record['check_out']:
                    found_record = record
                    found_date = date
                    break
            if found_record:
                break
    
    if found_record:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        found_record['check_out'] = now
        system.save_data()
        
        if found_date != datetime.now().strftime('%Y-%m-%d'):
            st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {found_date}")
        else:
            st.success("✅ تم تسجيل الانصراف بنجاح")
        
        st.rerun()
    else:
        st.error("لا يوجد حضور مسجل يحتاج إلى انصراف")

def get_weekly_attendance(system, emp_id):
    """الحصول على سجل الحضور الأسبوعي"""
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
            
            data.append({
                'التاريخ': date,
                'عدد التسجيلات': len(day_records),
                'إجمالي الساعات': round(total_hours, 2)
            })
    
    return pd.DataFrame(data[::-1]) if data else pd.DataFrame()

def show_admin_page(system):
    """عرض واجهة المدير"""
    st.markdown("<h1 class='main-header'>واجهة المدير</h1>", unsafe_allow_html=True)
    
    # زر العودة
    if st.button("← العودة للصفحة الرئيسية"):
        st.session_state.logged_in = False
        st.rerun()
    
    # تبويبات واجهة المدير
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
            new_emp_id = st.text_input("كود الموظف")
            new_emp_name = st.text_input("اسم الموظف")
        
        with col2:
            new_emp_dept = st.text_input("القسم")
            new_emp_salary = st.number_input("الراتب الشهري", min_value=0.0, value=0.0, step=100.0)
        
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
    
    if system.employees:
        employees_data = []
        for emp_id, emp_data in system.employees.items():
            monthly_salary = emp_data.get('monthly_salary', 0)
            hourly_rate = system.calculate_hourly_rate(monthly_salary)
            
            employees_data.append({
                'كود الموظف': emp_id,
                'اسم الموظف': emp_data['name'],
                'القسم': emp_data.get('department', ''),
                'الراتب الشهري': monthly_salary,
                'سعر الساعة': hourly_rate
            })
        
        df_employees = pd.DataFrame(employees_data)
        st.dataframe(df_employees, use_container_width=True)
        
        # حذف موظف
        st.markdown("#### حذف موظف")
        emp_to_delete = st.selectbox("اختر موظف للحذف", options=list(system.employees.keys()))
        
        if st.button("حذف الموظف المحدد", type="secondary"):
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
        st.info("لا يوجد موظفين مسجلين")

def daily_reports(system):
    """التقارير اليومية"""
    st.markdown("### تقرير الحضور اليومي")
    
    report_date = st.date_input("تاريخ التقرير", value=datetime.now())
    report_date_str = report_date.strftime('%Y-%m-%d')
    
    if st.button("عرض التقرير", type="primary"):
        if report_date_str in system.attendance:
            report_data = []
            total_hours_day = 0
            
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
            
            if report_data:
                df_report = pd.DataFrame(report_data)
                st.dataframe(df_report, use_container_width=True)
                
                st.markdown(f"**إجمالي ساعات العمل لليوم:** {total_hours_day:.2f} ساعة")
            else:
                st.info("لا توجد بيانات للحضور في هذا التاريخ")
        else:
            st.info("لا توجد بيانات للحضور في هذا التاريخ")

def monthly_reports(system):
    """التقارير الشهرية"""
    st.markdown("### تقرير الحضور الشهري")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1))
        end_date = st.date_input("إلى تاريخ", value=datetime.now())
    
    with col2:
        emp_id = st.selectbox("اختر الموظف", options=["الكل"] + list(system.employees.keys()))
    
    if st.button("عرض التقرير الشهري", type="primary"):
        if start_date > end_date:
            st.error("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        else:
            generate_monthly_report(system, start_date, end_date, emp_id)

def generate_monthly_report(system, start_date, end_date, emp_id):
    """توليد التقرير الشهري"""
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    report_data = []
    total_period_hours = 0
    total_period_salary = 0
    
    # تحديد الموظفين المطلوبين
    employees_to_report = [emp_id] if emp_id != "الكل" else list(system.employees.keys())
    
    for emp_id in employees_to_report:
        if emp_id in system.employees:
            emp_name = system.employees[emp_id]['name']
            monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
            hourly_rate = system.calculate_hourly_rate(monthly_salary)
            
            current_date = start_date
            emp_total_hours = 0
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                
                if date_str in system.attendance and emp_id in system.attendance[date_str]:
                    day_total = 0
                    
                    for record in system.attendance[date_str][emp_id]:
                        check_in = record.get('check_in', '')
                        check_out = record.get('check_out', '')
                        
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
                    
                    if day_total > 0:
                        day_salary = system.calculate_salary(hourly_rate, day_total)
                        emp_total_hours += day_total
                        
                        report_data.append({
                            'كود الموظف': emp_id,
                            'اسم الموظف': emp_name,
                            'التاريخ': date_str,
                            'إجمالي الساعات': day_total,
                            'الراتب اليومي': day_salary
                        })
                
                current_date += timedelta(days=1)
            
            if emp_total_hours > 0:
                emp_total_salary = system.calculate_salary(hourly_rate, emp_total_hours)
                total_period_hours += emp_total_hours
                total_period_salary += emp_total_salary
                
                report_data.append({
                    'كود الموظف': emp_id,
                    'اسم الموظف': f"{emp_name} (الإجمالي)",
                    'التاريخ': f"{start_date_str} إلى {end_date_str}",
                    'إجمالي الساعات': emp_total_hours,
                    'الراتب اليومي': emp_total_salary
                })
    
    if report_data:
        df_report = pd.DataFrame(report_data)
        st.dataframe(df_report, use_container_width=True)
        
        st.markdown(f"**إجمالي ساعات العمل للفترة:** {total_period_hours:.2f} ساعة")
        st.markdown(f"**إجمالي الرواتب للفترة:** {total_period_salary:.2f}")
    else:
        st.info("لا توجد بيانات للحضور في الفترة المحددة")

def export_reports(system):
    """تصدير التقارير"""
    st.markdown("### تصدير التقارير")
    
    export_type = st.radio("نوع التقرير", ["تقرير يومي", "تقرير شهري"])
    
    if export_type == "تقرير يومي":
        report_date = st.date_input("تاريخ التقرير", value=datetime.now(), key="export_daily")
        report_date_str = report_date.strftime('%Y-%m-%d')
        
        if st.button("تصدير كـ PDF", type="primary"):
            export_daily_pdf(system, report_date_str)
        
        if st.button("تصدير كـ Excel", type="secondary"):
            export_daily_excel(system, report_date_str)
    
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1), key="export_start")
            end_date = st.date_input("إلى تاريخ", value=datetime.now(), key="export_end")
        
        with col2:
            emp_id = st.selectbox("اختر الموظف", options=["الكل"] + list(system.employees.keys()), key="export_emp")
        
        if st.button("تصدير كـ PDF", type="primary"):
            export_monthly_pdf(system, start_date, end_date, emp_id)
        
        if st.button("تصدير كـ Excel", type="secondary"):
            export_monthly_excel(system, start_date, end_date, emp_id)

def export_daily_pdf(system, date_str):
    """تصدير التقرير اليومي كـ PDF"""
    if date_str in system.attendance:
        pdf = FPDF()
        pdf.add_page()
        
        # إضافة النص العربي (قد تحتاج لتثبيت خط عربي)
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 12)
        
        pdf.cell(0, 10, f"تقرير الحضور اليومي - {date_str}", 0, 1, 'C')
        pdf.ln(10)
        
        # عناوين الأعمدة
        col_widths = [30, 40, 40, 40, 20, 20]
        headers = ['كود الموظف', 'اسم الموظف', 'وقت الحضور', 'وقت الانصراف', 'الساعات', 'الراتب']
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        # البيانات
        for emp_id, records in system.attendance[date_str].items():
            if emp_id in system.employees:
                emp_name = system.employees[emp_id]['name']
                monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
                hourly_rate = system.calculate_hourly_rate(monthly_salary)
                
                for record in records:
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
                            salary = system.calculate_salary(hourly_rate, hours)
                        except ValueError:
                            pass
                    
                    pdf.cell(col_widths[0], 10, emp_id, 1, 0, 'C')
                    pdf.cell(col_widths[1], 10, emp_name, 1, 0, 'C')
                    pdf.cell(col_widths[2], 10, check_in, 1, 0, 'C')
                    pdf.cell(col_widths[3], 10, check_out, 1, 0, 'C')
                    pdf.cell(col_widths[4], 10, str(hours), 1, 0, 'C')
                    pdf.cell(col_widths[5], 10, str(salary), 1, 0, 'C')
                    pdf.ln()
        
        # حفظ الملف
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            
            with open(tmp_file.name, 'rb') as file:
                st.download_button(
                    label="تحميل PDF",
                    data=file,
                    file_name=f"تقرير_حضور_{date_str}.pdf",
                    mime="application/pdf"
                )
        
        st.success("✅ تم إنشاء التقرير بنجاح")
    else:
        st.error("لا توجد بيانات للتاريخ المحدد")

def export_daily_excel(system, date_str):
    """تصدير التقرير اليومي كـ Excel"""
    if date_str in system.attendance:
        data = []
        
        for emp_id, records in system.attendance[date_str].items():
            if emp_id in system.employees:
                emp_name = system.employees[emp_id]['name']
                monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
                hourly_rate = system.calculate_hourly_rate(monthly_salary)
                
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
                            salary = system.calculate_salary(hourly_rate, hours)
                        except ValueError:
                            pass
                    
                    data.append({
                        'كود الموظف': emp_id,
                        'اسم الموظف': emp_name,
                        'رقم التسجيل': i,
                        'وقت الحضور': check_in,
                        'وقت الانصراف': check_out,
                        'الساعات': hours,
                        'الراتب': salary
                    })
        
        if data:
            df = pd.DataFrame(data)
            
            # إنشاء ملف Excel مؤقت
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                df.to_excel(tmp_file.name, index=False, engine='openpyxl')
                
                with open(tmp_file.name, 'rb') as file:
                    st.download_button(
                        label="تحميل Excel",
                        data=file,
                        file_name=f"تقرير_حضور_{date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            st.success("✅ تم إنشاء التقرير بنجاح")
        else:
            st.error("لا توجد بيانات للتصدير")
    else:
        st.error("لا توجد بيانات للتاريخ المحدد")

def export_monthly_pdf(system, start_date, end_date, emp_id):
    """تصدير التقرير الشهري كـ PDF"""
    # تنفيذ مشابه لـ export_daily_pdf لكن للفترة الشهرية
    st.info("خاصية التصدير الشهري كـ PDF قيد التطوير")
    # يمكنك إضافة التنفيذ الكامل هنا

def export_monthly_excel(system, start_date, end_date, emp_id):
    """تصدير التقرير الشهري كـ Excel"""
    st.info("خاصية التصدير الشهري كـ Excel قيد التطوير")
    # يمكنك إضافة التنفيذ الكامل هنا

if __name__ == "__main__":
    main()