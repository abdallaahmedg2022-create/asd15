import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import tempfile
import time
from collections import defaultdict
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials
from google.auth import default
import warnings
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
    .present-list {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #dee2e6;
    }
    .section-title {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 15px 0;
        font-weight: bold;
    }
    .employee-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px;
        border-bottom: 1px solid #eee;
    }
    .employee-info {
        flex-grow: 1;
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
    .auto-update {
        font-size: 0.9em;
        color: #666;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

class GoogleSheetsManager:
    """مدير للتعامل مع Google Sheets"""
    
    def __init__(self, use_local_fallback=True):
        self.use_local_fallback = use_local_fallback
        self.local_folder = "GoogleSheets_Local_Backup"
        
        # إعداد مجلدات محلية احتياطية
        if not os.path.exists(self.local_folder):
            os.makedirs(self.local_folder)
            os.makedirs(os.path.join(self.local_folder, "employees"))
            os.makedirs(os.path.join(self.local_folder, "attendance"))
        
        # إعداد اتصال Google Sheets
        self.setup_google_sheets()
    
    def setup_google_sheets(self):
        """إعداد اتصال Google Sheets"""
        try:
            # محاولة تحميل ملف الاعتماد من Streamlit secrets
            if 'GOOGLE_CREDENTIALS' in st.secrets:
                credentials_dict = dict(st.secrets['GOOGLE_CREDENTIALS'])
                creds = Credentials.from_service_account_info(credentials_dict)
            else:
                # محاولة استخدام الاعتماد الافتراضي (للتطبيقات المنشورة على GCP)
                creds, _ = default()
            
            self.client = gspread.authorize(creds)
            
            # إنشاء أو فتح جداول البيانات
            self.setup_spreadsheets()
            
            st.session_state.google_sheets_connected = True
            return True
            
        except Exception as e:
            st.warning(f"⚠️ تعذر الاتصال بـ Google Sheets: {str(e)}")
            st.info("سيتم استخدام التخزين المحلي كنسخة احتياطية")
            self.client = None
            st.session_state.google_sheets_connected = False
            return False
    
    def setup_spreadsheets(self):
        """إعداد جداول البيانات"""
        try:
            # محاولة فتح جدول البيانات الموجود
            self.spreadsheet = self.client.open("نظام_حضور_وانصراف_الموظفين")
        except gspread.SpreadsheetNotFound:
            # إنشاء جدول بيانات جديد
            self.spreadsheet = self.client.create("نظام_حضور_وانصراف_الموظفين")
        
        # إنشاء أو فتح الأوراق المطلوبة
        self.setup_worksheets()
    
    def setup_worksheets(self):
        """إعداد الأوراق (Worksheets)"""
        worksheet_names = ["الموظفين", "سجلات_الحضور", "الملاحظات"]
        
        self.worksheets = {}
        for name in worksheet_names:
            try:
                self.worksheets[name] = self.spreadsheet.worksheet(name)
            except gspread.WorksheetNotFound:
                self.worksheets[name] = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
        
        # إعداد العناوين للأوراق
        self.setup_headers()
    
    def setup_headers(self):
        """إعداد العناوين للأوراق"""
        # عناوين ورقة الموظفين
        employees_headers = ["كود الموظف", "اسم الموظف", "القسم", "الراتب الشهري", "سعر الساعة"]
        if self.worksheets["الموظفين"].row_count == 1000:
            self.worksheets["الموظفين"].append_row(employees_headers)
        
        # عناوين ورقة سجلات الحضور
        attendance_headers = ["كود الموظف", "التاريخ", "وقت الحضور", "وقت الانصراف", "الساعات", "الراتب", "الحالة"]
        if self.worksheets["سجلات_الحضور"].row_count == 1000:
            self.worksheets["سجلات_الحضور"].append_row(attendance_headers)
        
        # عناوين ورقة الملاحظات
        notes_headers = ["كود الموظف", "التاريخ", "الوقت", "نوع الملاحظة", "الملاحظة"]
        if self.worksheets["الملاحظات"].row_count == 1000:
            self.worksheets["الملاحظات"].append_row(notes_headers)
    
    # === عمليات الموظفين ===
    
    def save_employee(self, emp_id, data):
        """حفظ بيانات موظف"""
        try:
            # الحفظ في Google Sheets
            if st.session_state.google_sheets_connected:
                employees_sheet = self.worksheets["الموظفين"]
                
                # البحث عن الموظف إذا كان موجوداً
                try:
                    cell = employees_sheet.find(emp_id)
                    row = cell.row
                    # تحديث الصف الموجود
                    employees_sheet.update(f"A{row}:E{row}", [[
                        emp_id,
                        data.get('name', ''),
                        data.get('department', ''),
                        data.get('monthly_salary', 0),
                        data.get('hourly_rate', 0)
                    ]])
                except gspread.exceptions.CellNotFound:
                    # إضافة موظف جديد
                    employees_sheet.append_row([
                        emp_id,
                        data.get('name', ''),
                        data.get('department', ''),
                        data.get('monthly_salary', 0),
                        data.get('hourly_rate', 0)
                    ])
            
            # حفظ نسخة محلية احتياطية
            self.save_employee_local(emp_id, data)
            return True
            
        except Exception as e:
            print(f"خطأ في حفظ الموظف: {e}")
            # الحفظ المحلي فقط
            return self.save_employee_local(emp_id, data)
    
    def save_employee_local(self, emp_id, data):
        """حفظ بيانات موظف محلياً"""
        try:
            file_path = os.path.join(self.local_folder, "employees", f"{emp_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False
    
    def load_employee(self, emp_id):
        """تحميل بيانات موظف"""
        # محاولة التحميل من Google Sheets
        if st.session_state.google_sheets_connected:
            try:
                employees_sheet = self.worksheets["الموظفين"]
                cell = employees_sheet.find(emp_id)
                row = cell.row
                values = employees_sheet.row_values(row)
                
                if len(values) >= 4:
                    return {
                        'name': values[1],
                        'department': values[2],
                        'monthly_salary': float(values[3]) if values[3] else 0,
                        'hourly_rate': float(values[4]) if len(values) > 4 and values[4] else 0
                    }
            except:
                pass
        
        # محاولة التحميل من النسخة المحلية
        return self.load_employee_local(emp_id)
    
    def load_employee_local(self, emp_id):
        """تحميل بيانات موظف محلياً"""
        try:
            file_path = os.path.join(self.local_folder, "employees", f"{emp_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def get_all_employees(self):
        """الحصول على جميع الموظفين"""
        employees = {}
        
        # محاولة التحميل من Google Sheets
        if st.session_state.google_sheets_connected:
            try:
                employees_sheet = self.worksheets["الموظفين"]
                records = employees_sheet.get_all_records()
                
                for record in records:
                    if 'كود الموظف' in record and record['كود الموظف']:
                        emp_id = record['كود الموظف']
                        employees[emp_id] = {
                            'name': record.get('اسم الموظف', ''),
                            'department': record.get('القسم', ''),
                            'monthly_salary': float(record.get('الراتب الشهري', 0)) if record.get('الراتب الشهري') else 0,
                            'hourly_rate': float(record.get('سعر الساعة', 0)) if record.get('سعر الساعة') else 0
                        }
                return employees
            except:
                pass
        
        # محاولة التحميل من النسخة المحلية
        try:
            emp_dir = os.path.join(self.local_folder, "employees")
            if os.path.exists(emp_dir):
                for file in os.listdir(emp_dir):
                    if file.endswith('.json'):
                        emp_id = file.replace('.json', '')
                        employee_data = self.load_employee_local(emp_id)
                        if employee_data:
                            employees[emp_id] = employee_data
        except:
            pass
        
        return employees
    
    def delete_employee(self, emp_id):
        """حذف موظف"""
        # حذف من Google Sheets
        if st.session_state.google_sheets_connected:
            try:
                employees_sheet = self.worksheets["الموظفين"]
                cell = employees_sheet.find(emp_id)
                if cell:
                    employees_sheet.delete_rows(cell.row)
            except:
                pass
        
        # حذف من النسخة المحلية
        try:
            file_path = os.path.join(self.local_folder, "employees", f"{emp_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
    
    # === عمليات الحضور ===
    
    def save_attendance(self, emp_id, date, check_in=None, check_out=None, notes=""):
        """حفظ سجل حضور"""
        try:
            # حساب الساعات والراتب
            hours = 0
            salary = 0
            
            if check_in and check_out:
                try:
                    time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                    time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                    delta = time_out - time_in
                    hours = round(delta.total_seconds() / 3600, 2)
                    
                    # حساب الراتب
                    employee_data = self.load_employee(emp_id)
                    if employee_data and employee_data.get('monthly_salary'):
                        hourly_rate = employee_data.get('monthly_salary', 0) / 26
                        salary = round(hourly_rate * hours, 2)
                except:
                    pass
            
            # تحديد الحالة
            status = "حاضر" if check_in and not check_out else "منصرف" if check_out else "غير محدد"
            
            # الحفظ في Google Sheets
            if st.session_state.google_sheets_connected:
                attendance_sheet = self.worksheets["سجلات_الحضور"]
                
                # البحث عن السجل إذا كان موجوداً
                try:
                    # البحث عن سجل لهذا الموظف في هذا التاريخ بدون انصراف
                    records = attendance_sheet.get_all_records()
                    for i, record in enumerate(records, start=2):  # start=2 لأن الصف الأول للعناوين
                        if (record.get('كود الموظف') == emp_id and 
                            record.get('التاريخ') == date and 
                            record.get('وقت الحضور') and 
                            not record.get('وقت الانصراف')):
                            
                            # تحديث سجل الحضور الحالي
                            attendance_sheet.update(f"C{i}:G{i}", [[
                                check_in or record.get('وقت الحضور', ''),
                                check_out or record.get('وقت الانصراف', ''),
                                hours,
                                salary,
                                status
                            ]])
                            break
                    else:
                        # إضافة سجل جديد
                        attendance_sheet.append_row([
                            emp_id,
                            date,
                            check_in or '',
                            check_out or '',
                            hours,
                            salary,
                            status
                        ])
                except:
                    # إضافة سجل جديد في حالة الخطأ
                    attendance_sheet.append_row([
                        emp_id,
                        date,
                        check_in or '',
                        check_out or '',
                        hours,
                        salary,
                        status
                    ])
            
            # حفظ نسخة محلية احتياطية
            self.save_attendance_local(emp_id, date, {
                'check_in': check_in,
                'check_out': check_out,
                'hours': hours,
                'salary': salary,
                'status': status
            })
            
            # حفظ الملاحظات إذا كانت موجودة
            if notes:
                self.save_note(emp_id, date, "حضور" if check_in and not check_out else "انصراف", notes)
            
            return True
            
        except Exception as e:
            print(f"خطأ في حفظ الحضور: {e}")
            # الحفظ المحلي فقط
            return self.save_attendance_local(emp_id, date, {
                'check_in': check_in,
                'check_out': check_out,
                'hours': 0,
                'salary': 0,
                'status': "حاضر" if check_in and not check_out else "منصرف" if check_out else "غير محدد"
            })
    
    def save_attendance_local(self, emp_id, date, data):
        """حفظ سجل حضور محلياً"""
        try:
            emp_folder = os.path.join(self.local_folder, "attendance", emp_id)
            os.makedirs(emp_folder, exist_ok=True)
            
            file_path = os.path.join(emp_folder, f"{date}.json")
            
            # تحميل السجلات الحالية إذا وجدت
            existing_records = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            
            # البحث عن سجل بدون انصراف لتحديثه
            updated = False
            for i, record in enumerate(existing_records):
                if record.get('check_in') and not record.get('check_out'):
                    existing_records[i] = data
                    updated = True
                    break
            
            # إذا لم يتم التحديث، أضف سجلاً جديداً
            if not updated:
                existing_records.append(data)
            
            # حفظ الملف
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_records, f, indent=4, ensure_ascii=False)
            
            return True
        except:
            return False
    
    def get_attendance_records(self, emp_id, date=None):
        """الحصول على سجلات حضور"""
        records = {}
        
        if date:
            # سجلات تاريخ معين
            # محاولة التحميل من Google Sheets
            if st.session_state.google_sheets_connected:
                try:
                    attendance_sheet = self.worksheets["سجلات_الحضور"]
                    all_records = attendance_sheet.get_all_records()
                    
                    date_records = []
                    for record in all_records:
                        if (record.get('كود الموظف') == emp_id and 
                            record.get('التاريخ') == date):
                            date_records.append({
                                'check_in': record.get('وقت الحضور', ''),
                                'check_out': record.get('وقت الانصراف', ''),
                                'hours': float(record.get('الساعات', 0)) if record.get('الساعات') else 0,
                                'salary': float(record.get('الراتب', 0)) if record.get('الراتب') else 0,
                                'status': record.get('الحالة', '')
                            })
                    
                    if date_records:
                        records[date] = date_records
                except:
                    pass
            
            # محاولة التحميل من النسخة المحلية
            if date not in records:
                local_records = self.get_attendance_local(emp_id, date)
                if local_records:
                    records.update(local_records)
        else:
            # جميع السجلات
            # محاولة التحميل من Google Sheets
            if st.session_state.google_sheets_connected:
                try:
                    attendance_sheet = self.worksheets["سجلات_الحضور"]
                    all_records = attendance_sheet.get_all_records()
                    
                    for record in all_records:
                        if record.get('كود الموظف') == emp_id:
                            date_str = record.get('التاريخ', '')
                            if date_str not in records:
                                records[date_str] = []
                            
                            records[date_str].append({
                                'check_in': record.get('وقت الحضور', ''),
                                'check_out': record.get('وقت الانصراف', ''),
                                'hours': float(record.get('الساعات', 0)) if record.get('الساعات') else 0,
                                'salary': float(record.get('الراتب', 0)) if record.get('الراتب') else 0,
                                'status': record.get('الحالة', '')
                            })
                except:
                    pass
            
            # محاولة التحميل من النسخة المحلية
            local_records = self.get_attendance_local(emp_id)
            for date_str, date_records in local_records.items():
                if date_str not in records:
                    records[date_str] = []
                records[date_str].extend(date_records)
        
        return records
    
    def get_attendance_local(self, emp_id, date=None):
        """الحصول على سجلات حضور محلياً"""
        records = {}
        
        try:
            emp_folder = os.path.join(self.local_folder, "attendance", emp_id)
            if not os.path.exists(emp_folder):
                return records
            
            if date:
                # سجلات تاريخ معين
                file_path = os.path.join(emp_folder, f"{date}.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        records[date] = json.load(f)
            else:
                # جميع السجلات
                for file in os.listdir(emp_folder):
                    if file.endswith('.json'):
                        date_str = file.replace('.json', '')
                        file_path = os.path.join(emp_folder, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            records[date_str] = json.load(f)
        except:
            pass
        
        return records
    
    def has_open_checkin(self, emp_id):
        """التحقق من وجود حضور مفتوح"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # التحقق من Google Sheets
        if st.session_state.google_sheets_connected:
            try:
                attendance_sheet = self.worksheets["سجلات_الحضور"]
                records = attendance_sheet.get_all_records()
                
                for record in records:
                    if (record.get('كود الموظف') == emp_id and 
                        record.get('وقت الحضور') and 
                        not record.get('وقت الانصراف')):
                        date = record.get('التاريخ', today)
                        return True, date
            except:
                pass
        
        # التحقق من النسخة المحلية
        all_records = self.get_attendance_records(emp_id)
        for date_str, date_records in all_records.items():
            for record in date_records:
                if record.get('check_in') and not record.get('check_out'):
                    return True, date_str
        
        return False, None
    
    # === عمليات الملاحظات ===
    
    def save_note(self, emp_id, date, note_type, note):
        """حفظ ملاحظة"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # الحفظ في Google Sheets
            if st.session_state.google_sheets_connected:
                notes_sheet = self.worksheets["الملاحظات"]
                notes_sheet.append_row([
                    emp_id,
                    date,
                    current_time,
                    note_type,
                    note
                ])
            
            # حفظ نسخة محلية احتياطية
            self.save_note_local(emp_id, date, note_type, note, current_time)
            return True
            
        except Exception as e:
            print(f"خطأ في حفظ الملاحظة: {e}")
            return self.save_note_local(emp_id, date, note_type, note, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def save_note_local(self, emp_id, date, note_type, note, timestamp):
        """حفظ ملاحظة محلياً"""
        try:
            notes_folder = os.path.join(self.local_folder, "notes")
            os.makedirs(notes_folder, exist_ok=True)
            
            file_path = os.path.join(notes_folder, f"{emp_id}_{date}.json")
            
            # تحميل الملاحظات الحالية إذا وجدت
            existing_notes = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_notes = json.load(f)
            
            # إضافة الملاحظة الجديدة
            existing_notes.append({
                'timestamp': timestamp,
                'type': note_type,
                'note': note
            })
            
            # حفظ الملف
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_notes, f, indent=4, ensure_ascii=False)
            
            return True
        except:
            return False
    
    def get_notes(self, emp_id, date=None):
        """الحصول على الملاحظات"""
        notes = []
        
        # محاولة التحميل من Google Sheets
        if st.session_state.google_sheets_connected:
            try:
                notes_sheet = self.worksheets["الملاحظات"]
                all_notes = notes_sheet.get_all_records()
                
                for note_record in all_notes:
                    if note_record.get('كود الموظف') == emp_id:
                        if not date or note_record.get('التاريخ') == date:
                            notes.append({
                                'timestamp': note_record.get('الوقت', ''),
                                'type': note_record.get('نوع الملاحظة', ''),
                                'note': note_record.get('الملاحظة', '')
                            })
            except:
                pass
        
        # محاولة التحميل من النسخة المحلية
        local_notes = self.get_notes_local(emp_id, date)
        notes.extend(local_notes)
        
        # ترتيب الملاحظات حسب الوقت (الأحدث أولاً)
        notes.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return notes
    
    def get_notes_local(self, emp_id, date=None):
        """الحصول على الملاحظات محلياً"""
        notes = []
        
        try:
            notes_folder = os.path.join(self.local_folder, "notes")
            if not os.path.exists(notes_folder):
                return notes
            
            if date:
                # ملاحظات تاريخ معين
                file_path = os.path.join(notes_folder, f"{emp_id}_{date}.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        notes = json.load(f)
            else:
                # جميع الملاحظات
                for file in os.listdir(notes_folder):
                    if file.startswith(f"{emp_id}_") and file.endswith('.json'):
                        file_path = os.path.join(notes_folder, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            notes.extend(json.load(f))
        except:
            pass
        
        return notes
    
    # === التقارير ===
    
    def get_daily_report_data(self, date):
        """الحصول على بيانات التقرير اليومي"""
        report_data = []
        total_hours = 0
        total_salary = 0
        
        # الحصول على جميع الموظفين
        employees = self.get_all_employees()
        
        for emp_id, emp_data in employees.items():
            emp_name = emp_data.get('name', 'غير معروف')
            hourly_rate = emp_data.get('monthly_salary', 0) / 26 if emp_data.get('monthly_salary') else 0
            
            # الحصول على سجلات الحضور لهذا التاريخ
            attendance_records = self.get_attendance_records(emp_id, date)
            
            if date in attendance_records:
                emp_total_hours = 0
                emp_total_salary = 0
                
                for i, record in enumerate(attendance_records[date], 1):
                    hours = record.get('hours', 0)
                    salary = record.get('salary', 0)
                    
                    report_data.append({
                        'كود الموظف': f"{emp_id} ({i})",
                        'اسم الموظف': emp_name,
                        'وقت الحضور': record.get('check_in', ''),
                        'وقت الانصراف': record.get('check_out', ''),
                        'الساعات': hours,
                        'الراتب': salary,
                        'الحالة': record.get('status', '')
                    })
                    
                    emp_total_hours += hours
                    emp_total_salary += salary
                
                if emp_total_hours > 0:
                    total_hours += emp_total_hours
                    total_salary += emp_total_salary
                    
                    report_data.append({
                        'كود الموظف': f"{emp_id} (الإجمالي)",
                        'اسم الموظف': emp_name,
                        'وقت الحضور': "",
                        'وقت الانصراف': "",
                        'الساعات': emp_total_hours,
                        'الراتب': emp_total_salary,
                        'الحالة': "الإجمالي"
                    })
        
        return report_data, total_hours, total_salary
    
    def get_monthly_report_data(self, emp_id, start_date, end_date):
        """الحصول على بيانات التقرير الشهري"""
        report_data = []
        total_hours = 0
        total_salary = 0
        
        # الحصول على بيانات الموظف
        employee_data = self.load_employee(emp_id)
        if not employee_data:
            return report_data, total_hours, total_salary
        
        emp_name = employee_data.get('name', 'غير معروف')
        hourly_rate = employee_data.get('monthly_salary', 0) / 26 if employee_data.get('monthly_salary') else 0
        
        # الحصول على جميع سجلات الحضور
        all_records = self.get_attendance_records(emp_id)
        
        # تحويل التواريخ إلى كائنات datetime للمقارنة
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        for date_str, date_records in all_records.items():
            try:
                record_date = datetime.strptime(date_str, '%Y-%m-%d')
                if start_dt <= record_date <= end_dt:
                    day_total_hours = 0
                    day_total_salary = 0
                    
                    for record in date_records:
                        hours = record.get('hours', 0)
                        salary = record.get('salary', 0)
                        
                        day_total_hours += hours
                        day_total_salary += salary
                    
                    if day_total_hours > 0:
                        report_data.append({
                            'التاريخ': date_str,
                            'اسم الموظف': emp_name,  # تم إضافة اسم الموظف هنا
                            'إجمالي الساعات': day_total_hours,
                            'إجمالي الراتب': day_total_salary
                        })
                        
                        total_hours += day_total_hours
                        total_salary += day_total_salary
            except:
                continue
        
        return report_data, total_hours, total_salary

class EmployeeAttendanceSystem:
    def __init__(self):
        # كلمة السر للإدارة
        self.admin_password = "a2cf1543"
        
        # مدير Google Sheets
        self.gs_manager = GoogleSheetsManager()
        
        # تحميل البيانات
        self.employees = self.gs_manager.get_all_employees()
        
        # إعداد session state للملاحظات
        if 'notes' not in st.session_state:
            st.session_state.notes = {}
    
    def save_data(self):
        """تحديث بيانات الموظفين"""
        self.employees = self.gs_manager.get_all_employees()
    
    def calculate_hourly_rate(self, monthly_salary):
        """حساب سعر الساعة"""
        return round(monthly_salary / 26, 2) if monthly_salary else 0
    
    def has_open_checkin(self, emp_id):
        """التحقق من وجود حضور مفتوح"""
        return self.gs_manager.has_open_checkin(emp_id)
    
    def get_today_present_employees(self):
        """الحصول على الموظفين الحاضرين اليوم"""
        today = datetime.now().strftime('%Y-%m-%d')
        present_employees = []
        
        for emp_id, emp_data in self.employees.items():
            attendance_records = self.gs_manager.get_attendance_records(emp_id, today)
            
            if today in attendance_records:
                for record in attendance_records[today]:
                    if record.get('check_in') and not record.get('check_out'):
                        # الحصول على الملاحظات
                        notes = self.gs_manager.get_notes(emp_id, today)
                        
                        present_employees.append({
                            'emp_id': emp_id,
                            'emp_name': emp_data.get('name', 'غير معروف'),
                            'department': emp_data.get('department', ''),
                            'check_in': record.get('check_in', ''),
                            'notes': notes
                        })
        
        return present_employees

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
    
    if 'last_emp_id' not in st.session_state:
        st.session_state.last_emp_id = ""
    
    if 'google_sheets_connected' not in st.session_state:
        st.session_state.google_sheets_connected = False
    
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
    
    # معلومات الاتصال بـ Google Sheets
    if st.session_state.google_sheets_connected:
        st.success("✅ متصل بـ Google Sheets")
    else:
        st.warning("⚠️ استخدام التخزين المحلي")
    
    # استخدام أعمدة لعرض واجهة الدخول
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### دخول كموظف")
        
        # حقل إدخال كود الموظف مع تحديث تلقائي
        emp_id = st.text_input("كود الموظف", key="emp_login_id", 
                              placeholder="اكتب كود الموظف هنا...")
        
        # تحديث حالة الموظف عند تغيير الكود
        if emp_id and emp_id != st.session_state.get('last_emp_id', ''):
            st.session_state.last_emp_id = emp_id
            # لا نحتاج لـ st.rerun() هنا لأن التحديث يكون تلقائياً
        
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
        if emp_id in system.employees:
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
                    
                    # زر الانصراف
                    if st.button("تسجيل الانصراف", type="primary", key=f"auto_checkout_{emp_id}"):
                        check_out_employee(system, emp_id, open_date)
                else:
                    # متحضر من يوم سابق
                    st.markdown('<div class="warning-box">'
                               '<strong>الحالة:</strong> <span class="status-old-present">متحضر من يوم سابق</span><br>'
                               '<strong>التاريخ:</strong> ' + open_date +
                               '</div>', unsafe_allow_html=True)
                    
                    # زر الانصراف
                    if st.button("تسجيل الانصراف (إغلاق الجلسة القديمة)", type="primary", key=f"auto_checkout_old_{emp_id}"):
                        check_out_employee(system, emp_id, open_date)
            else:
                # منصرف
                st.markdown('<div class="info-box">'
                           '<strong>الحالة:</strong> <span class="status-absent">منصرف</span>' +
                           '</div>', unsafe_allow_html=True)
                
                # زر الحضور
                if st.button("تسجيل الحضور", type="primary", key=f"auto_checkin_{emp_id}"):
                    check_in_employee(system, emp_id)
        else:
            st.warning("⚠️ كود الموظف غير مسجل")

def check_in_employee(system, emp_id):
    """تسجيل الحضور"""
    with st.spinner("جاري تسجيل الحضور..."):
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # حفظ الحضور
        success = system.gs_manager.save_attendance(emp_id, today, check_in=now)
        
        if success:
            st.success("✅ تم تسجيل الحضور بنجاح")
            time.sleep(1)
            st.rerun()
        else:
            st.error("حدث خطأ في تسجيل الحضور")

def check_out_employee(system, emp_id, date):
    """تسجيل الانصراف"""
    with st.spinner("جاري تسجيل الانصراف..."):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # حفظ الانصراف
        success = system.gs_manager.save_attendance(emp_id, date, check_out=now)
        
        if success:
            if date != today:
                st.success(f"✅ تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {date}")
            else:
                st.success("✅ تم تسجيل الانصراف بنجاح")
            
            time.sleep(1)
            st.rerun()
        else:
            st.error("حدث خطأ في تسجيل الانصراف")

def show_employee_page(system):
    """عرض واجهة الموظف"""
    emp_id = st.session_state.current_emp_id
    
    if emp_id in system.employees:
        emp_name = system.employees[emp_id]['name']
        
        st.markdown(f"<h1 class='main-header'>مرحباً، {emp_name} ({emp_id})</h1>", unsafe_allow_html=True)
        
        # قسم الحاضرين الآن (في الواجهة الرئيسية)
        st.markdown('<div class="section-title">👥 الحاضرون الآن</div>', unsafe_allow_html=True)
        show_present_now_in_main(system)
        
        # زر العودة
        if st.button("← تسجيل الخروج والعودة للصفحة الرئيسية"):
            st.session_state.logged_in = False
            st.session_state.current_emp_id = ""
            st.rerun()
        
        # عرض حالة الموظف في الصفحة الرئيسية
        show_employee_status_main(system, emp_id)
        
        # قسم الملاحظات
        st.markdown('<div class="section-title">📝 إضافة ملاحظة</div>', unsafe_allow_html=True)
        show_notes_section(system, emp_id)
        
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

def show_present_now_in_main(system):
    """عرض الحاضرين الآن في الواجهة الرئيسية"""
    present_employees = system.get_today_present_employees()
    
    if present_employees:
        st.markdown(f"**عدد الحاضرين:** {len(present_employees)}")
        
        for emp in present_employees:
            with st.expander(f"{emp['emp_name']} - {emp.get('department', '')} (كود: {emp['emp_id']})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    checkin_time = format_time_short(emp['check_in'])
                    st.markdown(f"**وقت الحضور:** {checkin_time}")
                    
                    # عرض الملاحظات
                    if emp['notes']:
                        st.markdown("**الملاحظات:**")
                        for note in emp['notes'][:3]:  # عرض أول 3 ملاحظات فقط
                            st.markdown(f"- {note.get('note', '')} ({note.get('type', '')})")
                
                with col2:
                    # زر لإضافة ملاحظة
                    if st.button(f"إضافة ملاحظة", key=f"add_note_{emp['emp_id']}"):
                        st.session_state[f"show_note_form_{emp['emp_id']}"] = True
                
                # نموذج إضافة ملاحظة
                if st.session_state.get(f"show_note_form_{emp['emp_id']}", False):
                    with st.form(key=f"note_form_{emp['emp_id']}"):
                        note_type = st.selectbox("نوع الملاحظة", 
                                               ["عام", "مهم", "تحذير", "متابعة"], 
                                               key=f"note_type_{emp['emp_id']}")
                        note_text = st.text_area("الملاحظة", key=f"note_text_{emp['emp_id']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("حفظ الملاحظة", type="primary"):
                                today = datetime.now().strftime('%Y-%m-%d')
                                success = system.gs_manager.save_note(
                                    emp['emp_id'], 
                                    today, 
                                    note_type, 
                                    note_text
                                )
                                if success:
                                    st.success("✅ تم حفظ الملاحظة بنجاح")
                                    st.session_state[f"show_note_form_{emp['emp_id']}"] = False
                                    time.sleep(1)
                                    st.rerun()
                        with col2:
                            if st.form_submit_button("إلغاء"):
                                st.session_state[f"show_note_form_{emp['emp_id']}"] = False
                                st.rerun()
        
        # عرض كجدول أيضاً
        st.markdown("### جدول الحاضرين")
        table_data = []
        for emp in present_employees:
            table_data.append({
                'الكود': emp['emp_id'],
                'الاسم': emp['emp_name'],
                'القسم': emp.get('department', ''),
                'وقت الحضور': format_time_short(emp['check_in'])
            })
        
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, height=200)
    else:
        st.success("🎉 لا يوجد موظفين حاضرين حالياً")

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
                if st.button("🔄 تسجيل الانصراف", type="primary", key="main_checkout"):
                    check_out_employee(system, emp_id, open_date)
            else:
                if st.button("✅ تسجيل الحضور", type="primary", key="main_checkin"):
                    check_in_employee(system, emp_id)

def get_last_checkin_time(system, emp_id, date):
    """الحصول على آخر وقت حضور"""
    records = system.gs_manager.get_attendance_records(emp_id, date)
    if date in records:
        for record in reversed(records[date]):
            if record.get('check_in') and not record.get('check_out'):
                try:
                    dt = datetime.strptime(record['check_in'], '%Y-%m-%d %H:%M:%S')
                    return dt.strftime('%I:%M %p')
                except ValueError:
                    return record['check_in']
    return "غير معروف"

def show_notes_section(system, emp_id):
    """عرض قسم الملاحظات"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # نموذج إضافة ملاحظة
    with st.form(key=f"add_note_form_{emp_id}"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            note_text = st.text_area("اكتب ملاحظة جديدة", 
                                   placeholder="اكتب ملاحظتك هنا...",
                                   key=f"new_note_{emp_id}")
        
        with col2:
            note_type = st.selectbox("النوع", 
                                   ["عام", "مهم", "تحذير", "متابعة"], 
                                   key=f"note_type_select_{emp_id}")
            
            if st.form_submit_button("💾 حفظ الملاحظة", type="primary"):
                if note_text.strip():
                    success = system.gs_manager.save_note(emp_id, today, note_type, note_text)
                    if success:
                        st.success("✅ تم حفظ الملاحظة بنجاح")
                        st.rerun()
                    else:
                        st.error("حدث خطأ في حفظ الملاحظة")
                else:
                    st.warning("يرجى كتابة ملاحظة")
    
    # عرض الملاحظات السابقة
    notes = system.gs_manager.get_notes(emp_id, today)
    if notes:
        st.markdown("### 📋 الملاحظات السابقة")
        for note in notes[:5]:  # عرض أول 5 ملاحظات فقط
            st.markdown(f"""
            <div class="notes-section">
                <strong>{note.get('type', 'عام')}</strong> - {note.get('timestamp', '')}
                <p>{note.get('note', '')}</p>
            </div>
            """, unsafe_allow_html=True)

def show_daily_attendance(system, emp_id):
    """عرض سجل الحضور اليومي"""
    today = datetime.now().strftime('%Y-%m-%d')
    records = system.gs_manager.get_attendance_records(emp_id, today)
    
    if today in records and records[today]:
        data = []
        total_hours = 0
        
        for i, record in enumerate(records[today], 1):
            check_in = record.get('check_in', '')
            check_out = record.get('check_out', '')
            hours = record.get('hours', 0)
            hours_display = f"{hours} ساعة" if hours else ''
            
            total_hours += hours
            
            # تنسيق الأوقات بشكل مختصر
            check_in_short = format_time_short(check_in)
            check_out_short = format_time_short(check_out)
            
            data.append({
                'التسجيل': i,
                'الحضور': check_in_short,
                'الانصراف': check_out_short,
                'المدة': hours_display,
                'الحالة': record.get('status', '')
            })
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=200)
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
        records = system.gs_manager.get_attendance_records(emp_id, date)
        
        if date in records:
            day_records = records[date]
            total_hours = 0
            
            for record in day_records:
                total_hours += record.get('hours', 0)
            
            if total_hours > 0 or day_records:
                data.append({
                    'التاريخ': date,
                    'التسجيلات': len(day_records),
                    'الساعات': round(total_hours, 2)
                })
    
    if data:
        df = pd.DataFrame(data[::-1])
        st.dataframe(df, use_container_width=True, height=200)
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
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 إدارة الموظفين", 
        "📅 التقارير اليومية", 
        "📈 التقارير الشهرية", 
        "📁 تصدير التقارير"
    ])
    
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
                    hourly_rate = system.calculate_hourly_rate(new_emp_salary)
                    employee_data = {
                        'name': new_emp_name,
                        'department': new_emp_dept,
                        'monthly_salary': new_emp_salary,
                        'hourly_rate': hourly_rate
                    }
                    
                    success = system.gs_manager.save_employee(new_emp_id, employee_data)
                    if success:
                        system.save_data()
                        st.success(f"✅ تم إضافة الموظف {new_emp_name} بنجاح")
                        st.rerun()
                    else:
                        st.error("حدث خطأ في حفظ بيانات الموظف")
            else:
                st.error("يرجى إدخال كود الموظف واسمه")
    
    st.markdown('<div class="section-title">قائمة الموظفين</div>', unsafe_allow_html=True)
    
    if system.employees:
        employees_list = []
        for emp_id, emp_data in system.employees.items():
            employees_list.append({
                'كود الموظف': emp_id,
                'اسم الموظف': emp_data['name'],
                'القسم': emp_data.get('department', ''),
                'الراتب الشهري': emp_data.get('monthly_salary', 0),
                'سعر الساعة': emp_data.get('hourly_rate', 0)
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
                        system.gs_manager.delete_employee(emp_to_delete)
                        system.save_data()
                        st.success(f"✅ تم حذف الموظف {emp_to_delete} بنجاح")
                        st.rerun()
    else:
        st.info("لا يوجد موظفين مسجلين")

def daily_reports(system):
    """التقارير اليومية"""
    st.markdown('<div class="section-title">📅 التقرير اليومي</div>', unsafe_allow_html=True)
    
    report_date = st.date_input("تاريخ التقرير", value=datetime.now(), key="daily_report_date")
    report_date_str = report_date.strftime('%Y-%m-%d')
    
    if st.button("عرض التقرير", type="primary", key="show_daily_report"):
        with st.spinner("جاري تحميل التقرير..."):
            report_data, total_hours, total_salary = system.gs_manager.get_daily_report_data(report_date_str)
            
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
        # عرض أسماء الموظفين بدلاً من الأكواد
        employee_options = []
        for emp_id, emp_data in system.employees.items():
            employee_options.append(f"{emp_data.get('name', 'غير معروف')} ({emp_id})")
        
        if employee_options:
            selected_employee = st.selectbox("اختر الموظف", options=["الكل"] + employee_options, key="monthly_emp")
            
            # استخراج كود الموظف من الاختيار
            if selected_employee != "الكل":
                emp_id = selected_employee.split("(")[-1].replace(")", "").strip()
            else:
                emp_id = "الكل"
        else:
            st.info("لا يوجد موظفين")
            emp_id = "الكل"
    
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
        if emp_id == "الكل":
            # تقرير لجميع الموظفين
            all_report_data = []
            total_period_hours = 0
            total_period_salary = 0
            
            for emp_id, emp_data in system.employees.items():
                emp_name = emp_data.get('name', 'غير معروف')
                report_data, emp_total_hours, emp_total_salary = system.gs_manager.get_monthly_report_data(
                    emp_id, start_date_str, end_date_str
                )
                
                if report_data:
                    all_report_data.extend(report_data)
                    total_period_hours += emp_total_hours
                    total_period_salary += emp_total_salary
            
            if all_report_data:
                df_report = pd.DataFrame(all_report_data)
                st.dataframe(df_report, use_container_width=True, height=500)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**إجمالي ساعات العمل للفترة:** {total_period_hours:.2f} ساعة")
                with col2:
                    st.markdown(f"**إجمالي الرواتب للفترة:** {total_period_salary:.2f} جنيه")
            else:
                st.info("لا توجد بيانات للحضور في الفترة المحددة")
        else:
            # تقرير لموظف معين
            report_data, total_hours, total_salary = system.gs_manager.get_monthly_report_data(
                emp_id, start_date_str, end_date_str
            )
            
            if report_data:
                df_report = pd.DataFrame(report_data)
                st.dataframe(df_report, use_container_width=True, height=500)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**إجمالي ساعات العمل للفترة:** {total_hours:.2f} ساعة")
                with col2:
                    st.markdown(f"**إجمالي الرواتب للفترة:** {total_salary:.2f} جنيه")
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
            # عرض أسماء الموظفين بدلاً من الأكواد
            employee_options = []
            for emp_id, emp_data in system.employees.items():
                employee_options.append(f"{emp_data.get('name', 'غير معروف')} ({emp_id})")
            
            if employee_options:
                selected_employee = st.selectbox("اختر الموظف", 
                                               options=["الكل"] + employee_options, 
                                               key="export_emp_id")
                
                # استخراج كود الموظف من الاختيار
                if selected_employee != "الكل":
                    emp_id = selected_employee.split("(")[-1].replace(")", "").strip()
                else:
                    emp_id = "الكل"
            else:
                st.info("لا يوجد موظفين")
                emp_id = "الكل"
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("تصدير كـ PDF", type="primary", key="export_pdf_monthly"):
                export_monthly_pdf(system, start_date, end_date, emp_id)
        with col2:
            if st.button("تصدير كـ Excel", type="secondary", key="export_excel_monthly"):
                export_monthly_excel(system, start_date, end_date, emp_id)

def export_daily_pdf(system, date_str):
    """تصدير التقرير اليومي كـ PDF"""
    report_data, total_hours, total_salary = system.gs_manager.get_daily_report_data(date_str)
    
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
    col_widths = [25, 35, 30, 30, 20, 20, 20]
    headers = ['كود الموظف', 'اسم الموظف', 'وقت الحضور', 'وقت الانصراف', 'الساعات', 'الراتب', 'الحالة']
    
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
        pdf.cell(col_widths[6], 10, str(row['الحالة']), 1, 0, 'C')
        pdf.ln()
    
    # إجمالي
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(160, 10, "الإجمالي:", 1, 0, 'R')
    pdf.cell(20, 10, f"{total_hours:.1f}", 1, 0, 'C')
    pdf.cell(20, 10, f"{total_salary:.1f}", 1, 0, 'C')
    pdf.cell(20, 10, "", 1, 0, 'C')
    
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
    report_data, total_hours, total_salary = system.gs_manager.get_daily_report_data(date_str)
    
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
        'الحالة': ''
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
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    if emp_id == "الكل":
        # تصدير لجميع الموظفين
        st.warning("تصدير PDF لجميع الموظفين قيد التطوير")
        return
    
    # تصدير لموظف معين
    report_data, total_hours, total_salary = system.gs_manager.get_monthly_report_data(
        emp_id, start_date_str, end_date_str
    )
    
    if not report_data:
        st.error("لا توجد بيانات للفترة المحددة")
        return
    
    pdf = FPDF()
    pdf.add_page()
    
    # إضافة النص العربي
    try:
        pdf.add_font('Arial', '', 'arial.ttf', uni=True)
        pdf.set_font('Arial', '', 12)
    except:
        pdf.set_font('Arial', '', 12)
    
    # الحصول على اسم الموظف
    emp_name = system.employees.get(emp_id, {}).get('name', 'غير معروف')
    
    pdf.cell(0, 10, f"تقرير الحضور الشهري - {emp_name}", 0, 1, 'C')
    pdf.cell(0, 10, f"الفترة: من {start_date_str} إلى {end_date_str}", 0, 1, 'C')
    pdf.ln(10)
    
    # عناوين الأعمدة
    col_widths = [40, 50, 30, 30]
    headers = ['التاريخ', 'اسم الموظف', 'الساعات', 'الراتب']
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
    pdf.ln()
    
    # البيانات
    for row in report_data:
        pdf.cell(col_widths[0], 10, str(row['التاريخ']), 1, 0, 'C')
        pdf.cell(col_widths[1], 10, str(row['اسم الموظف']), 1, 0, 'C')
        pdf.cell(col_widths[2], 10, str(row['إجمالي الساعات']), 1, 0, 'C')
        pdf.cell(col_widths[3], 10, str(row['إجمالي الراتب']), 1, 0, 'C')
        pdf.ln()
    
    # إجمالي
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(90, 10, "الإجمالي:", 1, 0, 'R')
    pdf.cell(30, 10, f"{total_hours:.1f}", 1, 0, 'C')
    pdf.cell(30, 10, f"{total_salary:.1f}", 1, 0, 'C')
    
    # حفظ الملف
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        pdf.output(tmp_file.name)
        
        with open(tmp_file.name, 'rb') as file:
            st.download_button(
                label="⬇️ تحميل PDF",
                data=file,
                file_name=f"تقرير_شهري_{emp_id}_{start_date_str}_إلى_{end_date_str}.pdf",
                mime="application/pdf",
                key="download_pdf_monthly"
            )
    
    st.success("✅ تم إنشاء التقرير بنجاح")

def export_monthly_excel(system, start_date, end_date, emp_id):
    """تصدير التقرير الشهري كـ Excel"""
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    if emp_id == "الكل":
        # تجميع بيانات جميع الموظفين
        all_report_data = []
        for emp_id, emp_data in system.employees.items():
            report_data, emp_total_hours, emp_total_salary = system.gs_manager.get_monthly_report_data(
                emp_id, start_date_str, end_date_str
            )
            if report_data:
                all_report_data.extend(report_data)
        
        if not all_report_data:
            st.error("لا توجد بيانات للفترة المحددة")
            return
        
        df = pd.DataFrame(all_report_data)
    else:
        # بيانات موظف معين
        report_data, total_hours, total_salary = system.gs_manager.get_monthly_report_data(
            emp_id, start_date_str, end_date_str
        )
        
        if not report_data:
            st.error("لا توجد بيانات للفترة المحددة")
            return
        
        df = pd.DataFrame(report_data)
    
    # إنشاء ملف Excel مؤقت
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        df.to_excel(tmp_file.name, index=False, engine='openpyxl')
        
        with open(tmp_file.name, 'rb') as file:
            file_name = f"تقرير_شهري_{start_date_str}_إلى_{end_date_str}"
            if emp_id != "الكل":
                file_name += f"_{emp_id}"
            file_name += ".xlsx"
            
            st.download_button(
                label="⬇️ تحميل Excel",
                data=file,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_monthly"
            )
    
    st.success("✅ تم إنشاء التقرير بنجاح")

if __name__ == "__main__":
    main()
