import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
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
        color: #2c3e50;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
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
    .present-box {
        background-color: #d1ecf1;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #17a2b8;
        margin: 10px 0;
        text-align: center;
    }
    .employee-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

class GoogleSheetsAttendanceSystem:
    def __init__(self):
        self.admin_password = "a2cf1543"
        self.setup_google_sheets()
    
    def setup_google_sheets(self):
        """إعداد الاتصال مع Google Sheets"""
        try:
            # استخدام بيانات الاعتماد من Streamlit secrets
            credentials_dict = st.secrets["gcp_service_account"]
            
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=scopes
            )
            
            self.gc = gspread.authorize(credentials)
            
            # فتح أو إنشاء الملف
            try:
                self.spreadsheet = self.gc.open("نظام_حضور_الموظفين")
            except:
                self.spreadsheet = self.gc.create("نظام_حضور_الموظفين")
                self.spreadsheet.share('', perm_type='anyone', role='writer')
            
            # إنشاء الأوراق الأساسية
            self.setup_sheets()
            
        except Exception as e:
            st.error(f"خطأ في الاتصال بـ Google Sheets: {str(e)}")
            st.info("""
            **تعليمات الإعداد:**
            1. قم بإنشاء مشروع في Google Cloud Console
            2. فعّل Google Sheets API و Google Drive API
            3. أنشئ Service Account وحمّل ملف JSON
            4. أضف محتويات الملف إلى Streamlit Secrets باسم 'gcp_service_account'
            """)
    
    def setup_sheets(self):
        """إنشاء الأوراق الأساسية إذا لم تكن موجودة"""
        try:
            # ورقة الموظفين
            try:
                self.employees_sheet = self.spreadsheet.worksheet("الموظفين")
            except:
                self.employees_sheet = self.spreadsheet.add_worksheet(
                    title="الموظفين", 
                    rows=1000, 
                    cols=10
                )
                headers = ['كود الموظف', 'اسم الموظف', 'القسم', 'الراتب الشهري', 'سعر الساعة']
                self.employees_sheet.update('A1:E1', [headers])
            
            # ورقة الحضور اليومي
            try:
                self.attendance_sheet = self.spreadsheet.worksheet("الحضور")
            except:
                self.attendance_sheet = self.spreadsheet.add_worksheet(
                    title="الحضور", 
                    rows=10000, 
                    cols=10
                )
                headers = ['التاريخ', 'كود الموظف', 'اسم الموظف', 'وقت الحضور', 
                          'وقت الانصراف', 'عدد الساعات', 'الراتب', 'الملاحظات']
                self.attendance_sheet.update('A1:H1', [headers])
            
        except Exception as e:
            st.error(f"خطأ في إعداد الأوراق: {str(e)}")
    
    def get_employees(self):
        """الحصول على قائمة الموظفين"""
        try:
            records = self.employees_sheet.get_all_records()
            employees = {}
            for record in records:
                emp_id = str(record.get('كود الموظف', ''))
                if emp_id:
                    employees[emp_id] = {
                        'name': record.get('اسم الموظف', ''),
                        'department': record.get('القسم', ''),
                        'monthly_salary': float(record.get('الراتب الشهري', 0))
                    }
            return employees
        except Exception as e:
            st.error(f"خطأ في قراءة الموظفين: {str(e)}")
            return {}
    
    def add_employee(self, emp_id, name, department, monthly_salary):
        """إضافة موظف جديد"""
        try:
            hourly_rate = self.calculate_hourly_rate(monthly_salary)
            self.employees_sheet.append_row([emp_id, name, department, monthly_salary, hourly_rate])
            return True
        except Exception as e:
            st.error(f"خطأ في إضافة الموظف: {str(e)}")
            return False
    
    def delete_employee(self, emp_id):
        """حذف موظف"""
        try:
            records = self.employees_sheet.get_all_records()
            for idx, record in enumerate(records, start=2):
                if str(record.get('كود الموظف', '')) == emp_id:
                    self.employees_sheet.delete_rows(idx)
                    return True
            return False
        except Exception as e:
            st.error(f"خطأ في حذف الموظف: {str(e)}")
            return False
    
    def calculate_hourly_rate(self, monthly_salary):
        """حساب سعر الساعة من الراتب الشهري"""
        return round(monthly_salary / 26, 2) if monthly_salary else 0
    
    def calculate_salary(self, hourly_rate, hours):
        """حساب الراتب من سعر الساعة وعدد الساعات"""
        return round(hourly_rate * hours, 2) if hourly_rate and hours else 0
    
    def check_in(self, emp_id, emp_name):
        """تسجيل الحضور"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.attendance_sheet.append_row([
                today, emp_id, emp_name, now, '', '', '', ''
            ])
            return True
        except Exception as e:
            st.error(f"خطأ في تسجيل الحضور: {str(e)}")
            return False
    
    def check_out(self, emp_id):
        """تسجيل الانصراف"""
        try:
            records = self.attendance_sheet.get_all_records()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # البحث عن آخر حضور مفتوح
            for idx in range(len(records) - 1, -1, -1):
                record = records[idx]
                if (str(record.get('كود الموظف', '')) == emp_id and 
                    record.get('وقت الحضور', '') and 
                    not record.get('وقت الانصراف', '')):
                    
                    row_num = idx + 2
                    check_in_time = record.get('وقت الحضور', '')
                    
                    # حساب عدد الساعات
                    try:
                        time_in = datetime.strptime(check_in_time, '%Y-%m-%d %H:%M:%S')
                        time_out = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
                        hours = round((time_out - time_in).total_seconds() / 3600, 2)
                        
                        # حساب الراتب
                        employees = self.get_employees()
                        monthly_salary = employees.get(emp_id, {}).get('monthly_salary', 0)
                        hourly_rate = self.calculate_hourly_rate(monthly_salary)
                        salary = self.calculate_salary(hourly_rate, hours)
                        
                        # تحديث السجل
                        self.attendance_sheet.update(f'E{row_num}:G{row_num}', 
                                                    [[now, hours, salary]])
                        return True, record.get('التاريخ', '')
                    except ValueError:
                        return False, None
            
            return False, None
        except Exception as e:
            st.error(f"خطأ في تسجيل الانصراف: {str(e)}")
            return False, None
    
    def has_open_checkin(self, emp_id):
        """التحقق من وجود حضور مفتوح"""
        try:
            records = self.attendance_sheet.get_all_records()
            for record in reversed(records):
                if (str(record.get('كود الموظف', '')) == emp_id and 
                    record.get('وقت الحضور', '') and 
                    not record.get('وقت الانصراف', '')):
                    return True, record.get('التاريخ', '')
            return False, None
        except:
            return False, None
    
    def get_present_employees(self):
        """الحصول على الموظفين الحاضرين حاليا"""
        try:
            records = self.attendance_sheet.get_all_records()
            present = {}
            
            for record in reversed(records):
                emp_id = str(record.get('كود الموظف', ''))
                if emp_id and emp_id not in present:
                    if (record.get('وقت الحضور', '') and 
                        not record.get('وقت الانصراف', '')):
                        present[emp_id] = {
                            'name': record.get('اسم الموظف', ''),
                            'check_in': record.get('وقت الحضور', ''),
                            'notes': record.get('الملاحظات', '')
                        }
            
            return present
        except Exception as e:
            st.error(f"خطأ في قراءة الحضور: {str(e)}")
            return {}
    
    def update_notes(self, emp_id, notes):
        """تحديث الملاحظات للموظف الحاضر"""
        try:
            records = self.attendance_sheet.get_all_records()
            
            for idx in range(len(records) - 1, -1, -1):
                record = records[idx]
                if (str(record.get('كود الموظف', '')) == emp_id and 
                    record.get('وقت الحضور', '') and 
                    not record.get('وقت الانصراف', '')):
                    
                    row_num = idx + 2
                    self.attendance_sheet.update(f'H{row_num}', notes)
                    return True
            
            return False
        except Exception as e:
            st.error(f"خطأ في تحديث الملاحظات: {str(e)}")
            return False
    
    def get_daily_attendance(self, date_str):
        """الحصول على حضور يوم معين"""
        try:
            records = self.attendance_sheet.get_all_records()
            daily_records = []
            
            for record in records:
                if record.get('التاريخ', '') == date_str:
                    daily_records.append(record)
            
            return daily_records
        except Exception as e:
            st.error(f"خطأ في قراءة الحضور اليومي: {str(e)}")
            return []
    
    def get_period_attendance(self, start_date, end_date, emp_id=None):
        """الحصول على حضور فترة معينة"""
        try:
            records = self.attendance_sheet.get_all_records()
            period_records = []
            
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            for record in records:
                record_date = record.get('التاريخ', '')
                if record_date:
                    try:
                        rec_date = datetime.strptime(record_date, '%Y-%m-%d')
                        if start <= rec_date <= end:
                            if emp_id is None or str(record.get('كود الموظف', '')) == emp_id:
                                period_records.append(record)
                    except:
                        continue
            
            return period_records
        except Exception as e:
            st.error(f"خطأ في قراءة حضور الفترة: {str(e)}")
            return []

def main():
    # تهيئة النظام
    if 'system' not in st.session_state:
        st.session_state.system = GoogleSheetsAttendanceSystem()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
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
    
    # عرض الموظفين الحاضرين
    st.markdown("### 👥 الموظفين الحاضرين الآن")
    present_employees = system.get_present_employees()
    
    if present_employees:
        cols = st.columns(min(3, len(present_employees)))
        for idx, (emp_id, emp_data) in enumerate(present_employees.items()):
            with cols[idx % 3]:
                st.markdown(f"""
                <div class='employee-card'>
                    <h4 style='color: #28a745; margin: 0;'>{emp_data['name']}</h4>
                    <p style='margin: 5px 0; color: #6c757d;'>الكود: {emp_id}</p>
                    <p style='margin: 5px 0; font-size: 0.9em;'>الحضور: {emp_data['check_in'].split()[1] if ' ' in emp_data['check_in'] else emp_data['check_in']}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("لا يوجد موظفين حاضرين حالياً")
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔐 دخول كموظف")
        
        # استخدام text_input مع on_change
        emp_id = st.text_input(
            "كود الموظف", 
            key="emp_login_id",
            placeholder="أدخل كود الموظف"
        )
        
        # عرض اسم الموظف تلقائياً عند كتابة الكود
        if emp_id:
            employees = system.get_employees()
            if emp_id in employees:
                st.success(f"✓ {employees[emp_id]['name']}")
                
                if st.button("دخول", type="primary", use_container_width=True):
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.current_emp_id = emp_id
                    st.rerun()
            else:
                st.error("❌ كود الموظف غير مسجل")
    
    with col2:
        st.markdown("### 👔 دخول كمدير")
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
    
    if st.button("← العودة للصفحة الرئيسية"):
        st.session_state.logged_in = False
        st.rerun()
    
    emp_id = st.session_state.current_emp_id
    employees = system.get_employees()
    emp_name = employees[emp_id]['name']
    
    st.markdown(f"### مرحباً، {emp_name} ({emp_id})")
    
    has_open, open_date = system.has_open_checkin(emp_id)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if has_open:
            if open_date == datetime.now().strftime('%Y-%m-%d'):
                st.markdown("""
                <div class='warning-box'>
                    <strong>الحالة:</strong> متحضر اليوم ✓
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='warning-box'>
                    <strong>الحالة:</strong> متحضر من {open_date}
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("🚪 تسجيل الانصراف", type="primary", use_container_width=True):
                success, date = system.check_out(emp_id)
                if success:
                    if date != datetime.now().strftime('%Y-%m-%d'):
                        st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {date}")
                    else:
                        st.success("✅ تم تسجيل الانصراف بنجاح")
                    st.rerun()
                else:
                    st.error("حدث خطأ في تسجيل الانصراف")
        else:
            st.markdown("""
            <div class='success-box'>
                <strong>الحالة:</strong> منصرف ⭕
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📥 تسجيل الحضور", type="primary", use_container_width=True):
                if system.check_in(emp_id, emp_name):
                    st.success("✅ تم تسجيل الحضور بنجاح")
                    st.rerun()
                else:
                    st.error("حدث خطأ في تسجيل الحضور")
    
    with col2:
        st.markdown("### 📝 سجل الحضور اليومي")
        today = datetime.now().strftime('%Y-%m-%d')
        daily_records = system.get_daily_attendance(today)
        
        emp_records = [r for r in daily_records if str(r.get('كود الموظف', '')) == emp_id]
        
        if emp_records:
            df_data = []
            for i, record in enumerate(emp_records, 1):
                df_data.append({
                    'التسجيل': i,
                    'وقت الحضور': record.get('وقت الحضور', ''),
                    'وقت الانصراف': record.get('وقت الانصراف', ''),
                    'الساعات': record.get('عدد الساعات', '')
                })
            
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)
        else:
            st.info("لا توجد سجلات حضور لهذا اليوم")

def show_admin_page(system):
    """عرض واجهة المدير"""
    st.markdown("<h1 class='main-header'>👔 واجهة المدير</h1>", unsafe_allow_html=True)
    
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
        show_present_employees(system)
    
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
        
        if st.form_submit_button("إضافة موظف", type="primary"):
            if new_emp_id and new_emp_name:
                employees = system.get_employees()
                if new_emp_id in employees:
                    st.error("كود الموظف مسجل مسبقاً")
                else:
                    if system.add_employee(new_emp_id, new_emp_name, new_emp_dept, new_emp_salary):
                        st.success(f"✅ تم إضافة الموظف {new_emp_name} بنجاح")
                        st.rerun()
            else:
                st.error("يرجى إدخال كود الموظف واسمه")
    
    st.markdown("---")
    st.markdown("### 📋 قائمة الموظفين")
    
    employees = system.get_employees()
    if employees:
        df_data = []
        for emp_id, emp_data in employees.items():
            hourly_rate = system.calculate_hourly_rate(emp_data['monthly_salary'])
            df_data.append({
                'كود الموظف': emp_id,
                'اسم الموظف': emp_data['name'],
                'القسم': emp_data['department'],
                'الراتب الشهري': emp_data['monthly_salary'],
                'سعر الساعة': hourly_rate
            })
        
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
        
        st.markdown("#### 🗑️ حذف موظف")
        emp_to_delete = st.selectbox("اختر موظف للحذف", options=list(employees.keys()))
        
        if st.button("حذف الموظف المحدد", type="secondary"):
            if emp_to_delete and system.delete_employee(emp_to_delete):
                st.success(f"✅ تم حذف الموظف {emp_to_delete} بنجاح")
                st.rerun()
    else:
        st.info("لا يوجد موظفين مسجلين")

def show_present_employees(system):
    """عرض الموظفين الحاضرين مع إمكانية إضافة ملاحظات"""
    st.markdown("### 👥 الموظفين الحاضرين الآن")
    
    present_employees = system.get_present_employees()
    
    if present_employees:
        for emp_id, emp_data in present_employees.items():
            with st.expander(f"👤 {emp_data['name']} ({emp_id})", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**وقت الحضور:** {emp_data['check_in']}")
                    
                    # حساب المدة
                    try:
                        check_in_time = datetime.strptime(emp_data['check_in'], '%Y-%m-%d %H:%M:%S')
                        now = datetime.now()
                        duration = now - check_in_time
                        hours = duration.total_seconds() / 3600
                        st.write(f"**المدة حتى الآن:** {hours:.2f} ساعة")
                    except:
                        pass
                
                with col2:
                    if st.button(f"🚪 تسجيل انصراف", key=f"checkout_{emp_id}", use_container_width=True):
                        success, date = system.check_out(emp_id)
                        if success:
                            st.success("✅ تم تسجيل الانصراف")
                            st.rerun()
                
                # إضافة/تعديل الملاحظات
                st.markdown("**📝 الملاحظات:**")
                notes = st.text_area(
                    "أضف ملاحظات",
                    value=emp_data.get('notes', ''),
                    key=f"notes_{emp_id}",
                    height=100
                )
                
                if st.button("💾 حفظ الملاحظات", key=f"save_notes_{emp_id}"):
                    if system.update_notes(emp_id, notes):
                        st.success("✅ تم حفظ الملاحظات")
                        st.rerun()
    else:
        st.info("لا يوجد موظفين حاضرين حالياً")

def daily_reports(system):
    """التقارير اليومية"""
    st.markdown("### 📅 تقرير الحضور اليومي")
    
    report_date = st.date_input("تاريخ التقرير", value=datetime.now())
    report_date_str = report_date.strftime('%Y-%m-%d')
    
    if st.button("عرض التقرير", type="primary"):
        daily_records = system.get_daily_attendance(report_date_str)
        
        if daily_records:
            df_data = []
            total_hours = 0
            total_salary = 0
            
            for record in daily_records:
                hours = record.get('عدد الساعات', 0)
                salary = record.get('الراتب', 0)
                
                if hours:
                    total_hours += float(hours)
                if salary:
                    total_salary += float(salary)
                
                df_data.append({
                    'كود الموظف': record.get('كود الموظف', ''),
                    'اسم الموظف': record.get('اسم الموظف', ''),
                    'وقت الحضور': record.get('وقت الحضور', ''),
                    'وقت الانصراف': record.get('وقت الانصراف', ''),
                    'الساعات': hours,
                    'الراتب': salary,
                    'الملاحظات': record.get('الملاحظات', '')
                })
            
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("إجمالي ساعات العمل", f"{total_hours:.2f} ساعة")
            with col2:
                st.metric("إجمالي الرواتب", f"{total_salary:.2f}")
        else:
            st.info("لا توجد بيانات للحضور في هذا التاريخ")

def monthly_reports(system):
    """التقارير الشهرية"""
    st.markdown("### 📈 تقرير الحضور الشهري")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1))
        end_date = st.date_input("إلى تاريخ", value=datetime.now())
    
    with col2:
        employees = system.get_employees()
        emp_options = ["الكل"] + [f"{emp_id} - {emp_data['name']}" for emp_id, emp_data in employees.items()]
        selected = st.selectbox("اختر الموظف", options=emp_options)
        
        # استخراج كود الموظف من الاختيار
        if selected != "الكل":
            emp_id = selected.split(" - ")[0]
        else:
            emp_id = None
    
    if st.button("عرض التقرير الشهري", type="primary"):
        if start_date > end_date:
            st.error("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        else:
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            period_records = system.get_period_attendance(start_date_str, end_date_str, emp_id)
            
            if period_records:
                # تجميع البيانات حسب الموظف والتاريخ
                summary = {}
                
                for record in period_records:
                    emp_id_rec = str(record.get('كود الموظف', ''))
                    emp_name = record.get('اسم الموظف', '')
                    date = record.get('التاريخ', '')
                    hours = record.get('عدد الساعات', 0)
                    salary = record.get('الراتب', 0)
                    
                    key = f"{emp_id_rec}_{emp_name}"
                    
                    if key not in summary:
                        summary[key] = {
                            'كود الموظف': emp_id_rec,
                            'اسم الموظف': emp_name,
                            'إجمالي الساعات': 0,
                            'إجمالي الراتب': 0,
                            'أيام العمل': set()
                        }
                    
                    if hours:
                        summary[key]['إجمالي الساعات'] += float(hours)
                    if salary:
                        summary[key]['إجمالي الراتب'] += float(salary)
                    if date:
                        summary[key]['أيام العمل'].add(date)
                
                # تحويل إلى DataFrame
                df_data = []
                for key, data in summary.items():
                    df_data.append({
                        'كود الموظف': data['كود الموظف'],
                        'اسم الموظف': data['اسم الموظف'],
                        'عدد أيام العمل': len(data['أيام العمل']),
                        'إجمالي الساعات': round(data['إجمالي الساعات'], 2),
                        'إجمالي الراتب': round(data['إجمالي الراتب'], 2)
                    })
                
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
                
                # الإحصائيات الإجمالية
                total_hours = sum([d['إجمالي الساعات'] for d in df_data])
                total_salary = sum([d['إجمالي الراتب'] for d in df_data])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("إجمالي ساعات العمل للفترة", f"{total_hours:.2f} ساعة")
                with col2:
                    st.metric("إجمالي الرواتب للفترة", f"{total_salary:.2f}")
            else:
                st.info("لا توجد بيانات للحضور في الفترة المحددة")

def export_reports(system):
    """تصدير التقارير"""
    st.markdown("### 📄 تصدير التقارير")
    
    export_type = st.radio("نوع التقرير", ["تقرير يومي", "تقرير شهري"])
    
    if export_type == "تقرير يومي":
        report_date = st.date_input("تاريخ التقرير", value=datetime.now(), key="export_daily")
        report_date_str = report_date.strftime('%Y-%m-%d')
        
        if st.button("تصدير كـ Excel", type="primary"):
            daily_records = system.get_daily_attendance(report_date_str)
            
            if daily_records:
                df = pd.DataFrame(daily_records)
                
                # تحويل إلى Excel
                output = pd.ExcelWriter(f'تقرير_حضور_{report_date_str}.xlsx', engine='openpyxl')
                df.to_excel(output, index=False, sheet_name='الحضور')
                output.close()
                
                with open(f'تقرير_حضور_{report_date_str}.xlsx', 'rb') as file:
                    st.download_button(
                        label="📥 تحميل Excel",
                        data=file,
                        file_name=f"تقرير_حضور_{report_date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.success("✅ تم إنشاء التقرير بنجاح")
            else:
                st.error("لا توجد بيانات للتصدير")
    
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("من تاريخ", value=datetime.now().replace(day=1), key="export_start")
            end_date = st.date_input("إلى تاريخ", value=datetime.now(), key="export_end")
        
        with col2:
            employees = system.get_employees()
            emp_options = ["الكل"] + [f"{emp_id} - {emp_data['name']}" for emp_id, emp_data in employees.items()]
            selected = st.selectbox("اختر الموظف", options=emp_options, key="export_emp")
            
            if selected != "الكل":
                emp_id = selected.split(" - ")[0]
            else:
                emp_id = None
        
        if st.button("تصدير كـ Excel", type="primary"):
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            period_records = system.get_period_attendance(start_date_str, end_date_str, emp_id)
            
            if period_records:
                df = pd.DataFrame(period_records)
                
                output = pd.ExcelWriter(f'تقرير_حضور_{start_date_str}_to_{end_date_str}.xlsx', engine='openpyxl')
                df.to_excel(output, index=False, sheet_name='الحضور')
                output.close()
                
                with open(f'تقرير_حضور_{start_date_str}_to_{end_date_str}.xlsx', 'rb') as file:
                    st.download_button(
                        label="📥 تحميل Excel",
                        data=file,
                        file_name=f"تقرير_حضور_{start_date_str}_to_{end_date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.success("✅ تم إنشاء التقرير بنجاح")
            else:
                st.error("لا توجد بيانات للتصدير")

if __name__ == "__main__":
    main()
