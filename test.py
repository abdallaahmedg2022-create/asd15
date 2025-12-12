import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict

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
        color: white;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
    .employee-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

class EmployeeAttendanceSystem:
    def __init__(self):
        self.admin_password = "a2cf1543"
        
        if not os.path.exists('data'):
            os.makedirs('data')
        
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
                data = json.load(f)
                self.attendance = defaultdict(lambda: defaultdict(list))
                for date, emps in data.items():
                    for emp_id, records in emps.items():
                        self.attendance[date][emp_id] = records
        except (FileNotFoundError, json.JSONDecodeError):
            self.attendance = defaultdict(lambda: defaultdict(list))
    
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
    
    def get_present_employees(self):
        """الحصول على الموظفين الحاضرين حالياً"""
        present = {}
        for date in self.attendance:
            for emp_id in self.attendance[date]:
                if emp_id in self.employees:
                    for record in self.attendance[date][emp_id]:
                        if record.get('check_in') and not record.get('check_out'):
                            if emp_id not in present:
                                present[emp_id] = {
                                    'name': self.employees[emp_id]['name'],
                                    'check_in': record['check_in'],
                                    'date': date,
                                    'notes': record.get('notes', '')
                                }
        return present
    
    def check_in_employee(self, emp_id):
        """تسجيل الحضور"""
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.attendance[today][emp_id].append({
            'check_in': now,
            'check_out': '',
            'notes': ''
        })
        
        self.save_data()
    
    def check_out_employee(self, emp_id):
        """تسجيل الانصراف"""
        found_record = None
        found_date = None
        
        for date in sorted(self.attendance.keys(), reverse=True):
            if emp_id in self.attendance[date]:
                for record in reversed(self.attendance[date][emp_id]):
                    if record['check_in'] and not record['check_out']:
                        found_record = record
                        found_date = date
                        break
                if found_record:
                    break
        
        if found_record:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            found_record['check_out'] = now
            self.save_data()
            return True, found_date
        
        return False, None
    
    def update_notes(self, emp_id, notes):
        """تحديث الملاحظات للموظف الحاضر"""
        for date in sorted(self.attendance.keys(), reverse=True):
            if emp_id in self.attendance[date]:
                for record in reversed(self.attendance[date][emp_id]):
                    if record['check_in'] and not record['check_out']:
                        record['notes'] = notes
                        self.save_data()
                        return True
        return False
    
    def get_daily_attendance(self, date_str):
        """الحصول على حضور يوم معين"""
        if date_str in self.attendance:
            return self.attendance[date_str]
        return {}
    
    def get_period_attendance(self, start_date, end_date, emp_id=None):
        """الحصول على حضور فترة معينة"""
        result = defaultdict(lambda: defaultdict(list))
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        for date_str in self.attendance:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if start <= date_obj <= end:
                    if emp_id:
                        if emp_id in self.attendance[date_str]:
                            result[date_str][emp_id] = self.attendance[date_str][emp_id]
                    else:
                        result[date_str] = self.attendance[date_str]
            except:
                continue
        
        return result

def main():
    if 'system' not in st.session_state:
        st.session_state.system = EmployeeAttendanceSystem()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
    system = st.session_state.system
    
    if not st.session_state.logged_in:
        show_login_page(system)
    else:
        if st.session_state.is_admin:
            show_admin_page(system)
        else:
            show_employee_page(system)

def show_login_page(system):
    """عرض صفحة تسجيل الدخول"""
    st.markdown("<h1 class='main-header'>🏢 نظام حضور وانصراف الموظفين</h1>", unsafe_allow_html=True)
    
    # عرض الموظفين الحاضرين
    st.markdown("### 👥 الموظفين الحاضرين الآن")
    present_employees = system.get_present_employees()
    
    if present_employees:
        cols = st.columns(min(3, len(present_employees)))
        for idx, (emp_id, emp_data) in enumerate(present_employees.items()):
            with cols[idx % 3]:
                # حساب المدة
                try:
                    check_in_time = datetime.strptime(emp_data['check_in'], '%Y-%m-%d %H:%M:%S')
                    now = datetime.now()
                    duration = now - check_in_time
                    hours = duration.total_seconds() / 3600
                    duration_str = f"{hours:.1f} ساعة"
                except:
                    duration_str = "-"
                
                st.markdown(f"""
                <div class='employee-card'>
                    <h4 style='color: #28a745; margin: 0;'>✓ {emp_data['name']}</h4>
                    <p style='margin: 5px 0; color: #6c757d; font-size: 0.9em;'>الكود: {emp_id}</p>
                    <p style='margin: 5px 0; font-size: 0.85em;'>⏰ الحضور: {emp_data['check_in'].split()[1] if ' ' in emp_data['check_in'] else emp_data['check_in']}</p>
                    <p style='margin: 5px 0; font-size: 0.85em;'>⏱️ المدة: {duration_str}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("📭 لا يوجد موظفين حاضرين حالياً")
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔐 دخول كموظف")
        
        emp_id = st.text_input(
            "كود الموظف", 
            key="emp_login_id",
            placeholder="أدخل كود الموظف",
            label_visibility="visible"
        )
        
        # عرض اسم الموظف تلقائياً
        if emp_id:
            if emp_id in system.employees:
                st.markdown(f"""
                <div style='background-color: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0;'>
                    <strong style='color: #155724;'>✓ {system.employees[emp_id]['name']}</strong>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🚀 دخول", type="primary", use_container_width=True):
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.current_emp_id = emp_id
                    st.rerun()
            else:
                st.error("❌ كود الموظف غير مسجل")
    
    with col2:
        st.markdown("### 👔 دخول كمدير")
        admin_pass = st.text_input("كلمة السر", type="password", key="admin_pass")
        
        st.write("")  # مسافة للمحاذاة
        st.write("")
        
        if st.button("🔑 دخول كمدير", type="secondary", use_container_width=True):
            if admin_pass == system.admin_password:
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("❌ كلمة السر غير صحيحة")

def show_employee_page(system):
    """عرض واجهة الموظف"""
    st.markdown("<h1 class='main-header'>📋 نظام الحضور والانصراف</h1>", unsafe_allow_html=True)
    
    if st.button("← العودة للصفحة الرئيسية"):
        st.session_state.logged_in = False
        st.rerun()
    
    emp_id = st.session_state.current_emp_id
    emp_name = system.employees[emp_id]['name']
    
    st.markdown(f"### مرحباً، {emp_name} ({emp_id})")
    
    has_open, open_date = system.has_open_checkin(emp_id)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if has_open:
            if open_date == datetime.now().strftime('%Y-%m-%d'):
                st.markdown("""
                <div class='warning-box'>
                    <strong>✓ الحالة:</strong> متحضر اليوم
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='warning-box'>
                    <strong>⚠️ الحالة:</strong> متحضر من {open_date}
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("🚪 تسجيل الانصراف", type="primary", use_container_width=True):
                success, date = system.check_out_employee(emp_id)
                if success:
                    if date != datetime.now().strftime('%Y-%m-%d'):
                        st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {date}")
                    else:
                        st.success("✅ تم تسجيل الانصراف بنجاح")
                    st.rerun()
                else:
                    st.error("❌ لا يوجد حضور مسجل يحتاج إلى انصراف")
        else:
            st.markdown("""
            <div class='success-box'>
                <strong>⭕ الحالة:</strong> منصرف
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📥 تسجيل الحضور", type="primary", use_container_width=True):
                system.check_in_employee(emp_id)
                st.success("✅ تم تسجيل الحضور بنجاح")
                st.rerun()
    
    with col2:
        st.markdown("### 📝 سجل الحضور اليومي")
        today = datetime.now().strftime('%Y-%m-%d')
        daily_data = system.get_daily_attendance(today)
        
        if emp_id in daily_data:
            records = daily_data[emp_id]
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
                    'وقت الحضور': check_in.split()[1] if ' ' in check_in else check_in,
                    'وقت الانصراف': check_out.split()[1] if ' ' in check_out else check_out,
                    'المدة': hours
                })
            
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info("📭 لا توجد سجلات حضور لهذا اليوم")
        else:
            st.info("📭 لا توجد سجلات حضور لهذا اليوم")

def show_admin_page(system):
    """عرض واجهة المدير"""
    st.markdown("<h1 class='main-header'>👔 لوحة تحكم المدير</h1>", unsafe_allow_html=True)
    
    if st.button("← العودة للصفحة الرئيسية"):
        st.session_state.logged_in = False
        st.rerun()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 إدارة الموظفين", 
        "👥 الحاضرين الآن",
        "📅 التقارير اليومية", 
        "📈 التقارير الشهرية",
        "📄 تصدير التقارير"
    ])
    
    with tab1:
        manage_employees(system)
    
    with tab2:
        show_present_employees_admin(system)
    
    with tab3:
        daily_reports(system)
    
    with tab4:
        monthly_reports(system)
    
    with tab5:
        export_reports(system)

def manage_employees(system):
    """إدارة الموظفين"""
    st.markdown("### ➕ إضافة موظف جديد")
    
    with st.form("add_employee_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_emp_id = st.text_input("كود الموظف")
            new_emp_name = st.text_input("اسم الموظف")
        
        with col2:
            new_emp_dept = st.text_input("القسم")
            new_emp_salary = st.number_input("الراتب الشهري", min_value=0.0, value=0.0, step=100.0)
        
        if st.form_submit_button("➕ إضافة موظف", type="primary"):
            if new_emp_id and new_emp_name:
                if new_emp_id in system.employees:
                    st.error("❌ كود الموظف مسجل مسبقاً")
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
                st.error("❌ يرجى إدخال كود الموظف واسمه")
    
    st.markdown("---")
    st.markdown("### 📋 قائمة الموظفين")
    
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
        st.dataframe(df_employees, use_container_width=True, hide_index=True)
        
        st.markdown("#### 🗑️ حذف موظف")
        emp_options = [f"{emp_id} - {emp_data['name']}" for emp_id, emp_data in system.employees.items()]
        selected = st.selectbox("اختر موظف للحذف", options=emp_options)
        
        if st.button("🗑️ حذف الموظف المحدد", type="secondary"):
            if selected:
                emp_to_delete = selected.split(" - ")[0]
                emp_name = system.employees[emp_to_delete]['name']
                
                del system.employees[emp_to_delete]
                
                for date in list(system.attendance.keys()):
                    if emp_to_delete in system.attendance[date]:
                        del system.attendance[date][emp_to_delete]
                    if not system.attendance[date]:
                        del system.attendance[date]
                
                system.save_data()
                st.success(f"✅ تم حذف الموظف {emp_name} بنجاح")
                st.rerun()
    else:
        st.info("📭 لا يوجد موظفين مسجلين")

def show_present_employees_admin(system):
    """عرض الموظفين الحاضرين مع إمكانية إضافة ملاحظات"""
    st.markdown("### 👥 الموظفين الحاضرين الآن")
    
    present_employees = system.get_present_employees()
    
    if present_employees:
        for emp_id, emp_data in present_employees.items():
            with st.expander(f"👤 {emp_data['name']} ({emp_id})", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**📅 التاريخ:** {emp_data['date']}")
                    st.write(f"**⏰ وقت الحضور:** {emp_data['check_in']}")
                    
                    try:
                        check_in_time = datetime.strptime(emp_data['check_in'], '%Y-%m-%d %H:%M:%S')
                        now = datetime.now()
                        duration = now - check_in_time
                        hours = duration.total_seconds() / 3600
                        st.write(f"**⏱️ المدة حتى الآن:** {hours:.2f} ساعة")
                    except:
                        pass
                
                with col2:
                    if st.button(f"🚪 تسجيل انصراف", key=f"checkout_{emp_id}", use_container_width=True):
                        success, date = system.check_out_employee(emp_id)
                        if success:
                            st.success("✅ تم تسجيل الانصراف")
                            st.rerun()
                
                st.markdown("**📝 الملاحظات:**")
                notes = st.text_area(
                    "أضف ملاحظات (يتم الحفظ بشكل مستقل عن الانصراف)",
                    value=emp_data.get('notes', ''),
                    key=f"notes_{emp_id}",
                    height=100
                )
                
                if st.button("💾 حفظ الملاحظات", key=f"save_notes_{emp_id}"):
                    if system.update_notes(emp_id, notes):
                        st.success("✅ تم حفظ الملاحظات بنجاح")
                        st.rerun()
                    else:
                        st.error("❌ حدث خطأ في حفظ الملاحظات")
    else:
        st.info("📭 لا يوجد موظفين حاضرين حالياً")

def daily_reports(system):
    """التقارير اليومية"""
    st.markdown("### 📅 تقرير الحضور اليومي")
    
    report_date = st.date_input("تاريخ التقرير", value=datetime.now())
    report_date_str = report_date.strftime('%Y-%m-%d')
    
    if st.button("📊 عرض التقرير", type="primary"):
        daily_data = system.get_daily_attendance(report_date_str)
        
        if daily_data:
            report_data = []
            total_hours_day = 0
            total_salary_day = 0
            
            for emp_id, records in daily_data.items():
                if emp_id in system.employees:
                    emp_name = system.employees[emp_id]['name']
                    monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
                    hourly_rate = system.calculate_hourly_rate(monthly_salary)
                    
                    for i, record in enumerate(records, 1):
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
                                salary = system.calculate_salary(hourly_rate, hours)
                                total_hours_day += hours
                                total_salary_day += salary
                            except ValueError:
                                pass
                        
                        report_data.append({
                            'كود الموظف': emp_id,
                            'اسم الموظف': emp_name,
                            'التسجيل': i,
                            'وقت الحضور': check_in,
                            'وقت الانصراف': check_out,
                            'الساعات': hours,
                            'الراتب': salary,
                            'الملاحظات': notes
                        })
            
            if report_data:
                df_report = pd.DataFrame(report_data)
                st.dataframe(df_report, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <h3 style='margin: 0;'>{total_hours_day:.2f}</h3>
                        <p style='margin: 5px 0;'>إجمالي ساعات العمل</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <h3 style='margin: 0;'>{total_salary_day:.2f}</h3>
                        <p style='margin: 5px 0;'>إجمالي الرواتب</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📭 لا توجد بيانات للحضور في هذا التاريخ")
        else:
            st.info("📭 لا توجد بيانات للحضور في هذا التاريخ")

def monthly_reports(system):
    """التقارير الشهرية"""
    st.markdown("### 📈 تقرير الحضور الشهري")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1))
        end_date = st.date_input("إلى تاريخ", value=datetime.now())
    
    with col2:
        emp_options = ["الكل"] + [f"{emp_id} - {emp_data['name']}" for emp_id, emp_data in system.employees.items()]
        selected = st.selectbox("اختر الموظف", options=emp_options)
        
        if selected != "الكل":
            selected_emp_id = selected.split(" - ")[0]
        else:
            selected_emp_id = None
    
    if st.button("📊 عرض التقرير الشهري", type="primary"):
        if start_date > end_date:
            st.error("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        else:
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            period_data = system.get_period_attendance(start_date_str, end_date_str, selected_emp_id)
            
            if period_data:
                report_data = []
                summary = defaultdict(lambda: {'hours': 0, 'salary': 0, 'days': 0})
                
                for date_str, emps in period_data.items():
                    for emp_id, records in emps.items():
                        if emp_id in system.employees:
                            emp_name = system.employees[emp_id]['name']
                            monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
                            hourly_rate = system.calculate_hourly_rate(monthly_salary)
                            
                            day_hours = 0
                            for record in records:
                                check_in = record.get('check_in', '')
                                check_out = record.get('check_out', '')
                                
                                if check_in and check_out:
                                    try:
                                        time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                                        time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                                        delta = time_out - time_in
                                        hours = round(delta.total_seconds() / 3600, 2)
                                        day_hours += hours
                                    except ValueError:
                                        pass
                            
                            if day_hours > 0:
                                day_salary = system.calculate_salary(hourly_rate, day_hours)
                                
                                report_data.append({
                                    'التاريخ': date_str,
                                    'كود الموظف': emp_id,
                                    'اسم الموظف': emp_name,
                                    'الساعات': day_hours,
                                    'الراتب': day_salary
                                })
                                
                                summary[emp_id]['name'] = emp_name
                                summary[emp_id]['hours'] += day_hours
                                summary[emp_id]['salary'] += day_salary
                                summary[emp_id]['days'] += 1
                
                if report_data:
                    # عرض التقرير التفصيلي
                    st.markdown("#### 📋 التقرير التفصيلي")
                    df_report = pd.DataFrame(report_data)
                    st.dataframe(df_report, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    
                    # عرض الملخص
                    st.markdown("#### 📊 ملخص الموظفين")
                    summary_data = []
                    total_hours = 0
                    total_salary = 0
                    
                    for emp_id, data in summary.items():
                        summary_data.append({
                            'كود الموظف': emp_id,
                            'اسم الموظف': data['name'],
                            'أيام العمل': data['days'],
                            'إجمالي الساعات': round(data['hours'], 2),
                            'إجمالي الراتب': round(data['salary'], 2)
                        })
                        total_hours += data['hours']
                        total_salary += data['salary']
                    
                    df_summary = pd.DataFrame(summary_data)
                    st.dataframe(df_summary, use_container_width=True, hide_index=True)
                    
                    # عرض الإجماليات
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"""
                        <div class='metric-card'>
                            <h3 style='margin: 0;'>{len(summary)}</h3>
                            <p style='margin: 5px 0;'>عدد الموظفين</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div class='metric-card'>
                            <h3 style='margin: 0;'>{total_hours:.2f}</h3>
                            <p style='margin: 5px 0;'>إجمالي الساعات</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"""
                        <div class='metric-card'>
                            <h3 style='margin: 0;'>{total_salary:.2f}</h3>
                            <p style='margin: 5px 0;'>إجمالي الرواتب</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("📭 لا توجد بيانات للحضور في الفترة المحددة")
            else:
                st.info("📭 لا توجد بيانات للحضور في الفترة المحددة")

def export_reports(system):
    """تصدير التقارير"""
    st.markdown("### 📄 تصدير التقارير")
    
    export_type = st.radio("نوع التقرير", ["تقرير يومي", "تقرير شهري"])
    
    if export_type == "تقرير يومي":
        report_date = st.date_input("تاريخ التقرير", value=datetime.now(), key="export_daily")
        report_date_str = report_date.strftime('%Y-%m-%d')
        
        if st.button("📥 تصدير كـ Excel", type="primary"):
            daily_data = system.get_daily_attendance(report_date_str)
            
            if daily_data:
                report_data = []
                
                for emp_id, records in daily_data.items():
                    if emp_id in system.employees:
                        emp_name = system.employees[emp_id]['name']
                        monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
                        hourly_rate = system.calculate_hourly_rate(monthly_salary)
                        
                        for i, record in enumerate(records, 1):
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
                                    salary = system.calculate_salary(hourly_rate, hours)
                                except ValueError:
                                    pass
                            
                            report_data.append({
                                'كود الموظف': emp_id,
                                'اسم الموظف': emp_name,
                                'رقم التسجيل': i,
                                'وقت الحضور': check_in,
                                'وقت الانصراف': check_out,
                                'الساعات': hours,
                                'الراتب': salary,
                                'الملاحظات': notes
                            })
                
                if report_data:
                    df = pd.DataFrame(report_data)
                    
                    # تحويل إلى Excel
                    excel_file = f'تقرير_حضور_{report_date_str}.xlsx'
                    df.to_excel(excel_file, index=False, engine='openpyxl')
                    
                    with open(excel_file, 'rb') as file:
                        st.download_button(
                            label="📥 تحميل التقرير",
                            data=file,
                            file_name=excel_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    # حذف الملف المؤقت
                    try:
                        os.remove(excel_file)
                    except:
                        pass
                    
                    st.success("✅ تم إنشاء التقرير بنجاح")
                else:
                    st.error("❌ لا توجد بيانات للتصدير")
            else:
                st.error("❌ لا توجد بيانات للتاريخ المحدد")
    
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1), key="export_start")
            end_date = st.date_input("إلى تاريخ", value=datetime.now(), key="export_end")
        
        with col2:
            emp_options = ["الكل"] + [f"{emp_id} - {emp_data['name']}" for emp_id, emp_data in system.employees.items()]
            selected = st.selectbox("اختر الموظف", options=emp_options, key="export_emp")
            
            if selected != "الكل":
                selected_emp_id = selected.split(" - ")[0]
            else:
                selected_emp_id = None
        
        if st.button("📥 تصدير كـ Excel", type="primary"):
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            period_data = system.get_period_attendance(start_date_str, end_date_str, selected_emp_id)
            
            if period_data:
                report_data = []
                
                for date_str, emps in period_data.items():
                    for emp_id, records in emps.items():
                        if emp_id in system.employees:
                            emp_name = system.employees[emp_id]['name']
                            monthly_salary = system.employees[emp_id].get('monthly_salary', 0)
                            hourly_rate = system.calculate_hourly_rate(monthly_salary)
                            
                            for record in records:
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
                                        salary = system.calculate_salary(hourly_rate, hours)
                                    except ValueError:
                                        pass
                                
                                report_data.append({
                                    'التاريخ': date_str,
                                    'كود الموظف': emp_id,
                                    'اسم الموظف': emp_name,
                                    'وقت الحضور': check_in,
                                    'وقت الانصراف': check_out,
                                    'الساعات': hours,
                                    'الراتب': salary,
                                    'الملاحظات': notes
                                })
                
                if report_data:
                    df = pd.DataFrame(report_data)
                    
                    excel_file = f'تقرير_حضور_{start_date_str}_to_{end_date_str}.xlsx'
                    df.to_excel(excel_file, index=False, engine='openpyxl')
                    
                    with open(excel_file, 'rb') as file:
                        st.download_button(
                            label="📥 تحميل التقرير",
                            data=file,
                            file_name=excel_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    try:
                        os.remove(excel_file)
                    except:
                        pass
                    
                    st.success("✅ تم إنشاء التقرير بنجاح")
                else:
                    st.error("❌ لا توجد بيانات للتصدير")
            else:
                st.error("❌ لا توجد بيانات للفترة المحددة")

if __name__ == "__main__":
    main()
