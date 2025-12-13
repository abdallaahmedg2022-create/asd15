import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict

class EmployeeAttendanceSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("نظام حضور وانصراف الموظفين")
        self.root.geometry("1100x750")
        self.root.configure(bg='#f0f2f5')
        
        # كلمة السر للإدارة (يمكن تغييرها)
        self.admin_password = "a2cf1543"
        
        # إنشاء مجلد البيانات إذا لم يكن موجوداً
        if not os.path.exists('data'):
            os.makedirs('data')
        
        # تحميل البيانات
        self.load_data()
        
        # إنشاء واجهة المستخدم
        self.create_login_page()
    
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
        """حساب سعر الساعة من سعر الساعه"""
        return round(monthly_salary / 26, 2)
    
    def calculate_salary(self, hourly_rate, hours):
        """حساب الراتب من سعر الساعة وعدد الساعات"""
        return round(hourly_rate * hours, 2)
    
    def create_login_page(self):
        """إنشاء صفحة تسجيل الدخول"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        login_frame = tk.Frame(self.root, bg='#f0f2f5')
        login_frame.pack(expand=True, pady=100)
        
        title_label = tk.Label(login_frame, text="نظام حضور وانصراف الموظفين", 
                              font=('Arial', 18, 'bold'), bg='#f0f2f5', fg='#333')
        title_label.pack(pady=20)
        
        emp_btn = tk.Button(login_frame, text="دخول كموظف", command=self.create_attendance_ui, 
                          width=20, height=2, bg='#4CAF50', fg='white', font=('Arial', 12))
        emp_btn.pack(pady=10, ipadx=10, ipady=5)
        
        admin_btn = tk.Button(login_frame, text="دخول كمدير", command=self.show_admin_login, 
                            width=20, height=2, bg='#2196F3', fg='white', font=('Arial', 12))
        admin_btn.pack(pady=10, ipadx=10, ipady=5)
    
    def show_admin_login(self):
        """عرض نافذة تسجيل دخول المدير"""
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("دخول المدير")
        self.login_window.geometry("350x200")
        self.login_window.resizable(False, False)
        self.login_window.grab_set()
        
        content_frame = tk.Frame(self.login_window, padx=20, pady=20)
        content_frame.pack(expand=True, fill='both')
        
        tk.Label(content_frame, text="أدخل كلمة السر:", font=('Arial', 12)).pack(pady=10)
        
        self.password_entry = tk.Entry(content_frame, show="*", font=('Arial', 12))
        self.password_entry.pack(pady=10, ipadx=10, ipady=5)
        
        btn_frame = tk.Frame(content_frame)
        btn_frame.pack(pady=10)
        
        login_btn = tk.Button(btn_frame, text="دخول", command=self.verify_admin_password,
                            width=10, bg='#2196F3', fg='white', font=('Arial', 10))
        login_btn.pack(side='left', padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="إلغاء", command=self.login_window.destroy,
                             width=10, bg='#f44336', fg='white', font=('Arial', 10))
        cancel_btn.pack(side='right', padx=5)
        
        self.password_entry.bind('<Return>', lambda event: self.verify_admin_password())
    
    def verify_admin_password(self):
        """التحقق من كلمة سر المدير"""
        entered_password = self.password_entry.get()
        if entered_password == self.admin_password:
            self.login_window.destroy()
            self.create_admin_ui()
        else:
            messagebox.showerror("خطأ", "كلمة السر غير صحيحة")
            self.password_entry.focus()
    
    def has_open_checkin(self, emp_id):
        """التحقق من وجود حضور مفتوح (بدون انصراف) للموظف في أي يوم"""
        for date in self.attendance:
            if emp_id in self.attendance[date]:
                for record in self.attendance[date][emp_id]:
                    if record.get('check_in') and not record.get('check_out'):
                        return True, date
        return False, None
    
    def create_attendance_ui(self):
        """إنشاء واجهة الموظف (الحضور والانصراف)"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        title_frame = tk.Frame(self.root, bg='#f0f2f5')
        title_frame.pack(fill='x', pady=10)
        
        tk.Label(title_frame, text="نظام الحضور والانصراف", font=('Arial', 16, 'bold'), 
                bg='#f0f2f5').pack()
        
        input_frame = ttk.LabelFrame(self.root, text="إدخال البيانات", padding=(20, 15))
        input_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(input_frame, text="كود الموظف:", font=('Arial', 12)).grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.emp_id_entry = ttk.Entry(input_frame, width=20, font=('Arial', 12))
        self.emp_id_entry.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        ttk.Label(input_frame, text="اسم الموظف:", font=('Arial', 12)).grid(row=1, column=0, padx=10, pady=10, sticky='e')
        self.emp_name_label = ttk.Label(input_frame, text="", width=20, font=('Arial', 12))
        self.emp_name_label.grid(row=1, column=1, padx=10, pady=10, sticky='w')
        
        ttk.Label(input_frame, text="الحالة:", font=('Arial', 12)).grid(row=2, column=0, padx=10, pady=10, sticky='e')
        self.emp_status_label = ttk.Label(input_frame, text="", width=20, font=('Arial', 12, 'bold'), foreground='red')
        self.emp_status_label.grid(row=2, column=1, padx=10, pady=10, sticky='w')
        
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.check_in_btn = ttk.Button(button_frame, text="حضور", command=self.check_in, 
                                     width=15, style='Accent.TButton')
        self.check_in_btn.pack(side='left', padx=10)
        
        self.check_out_btn = ttk.Button(button_frame, text="انصراف", command=self.check_out, 
                                      width=15, style='Accent.TButton')
        self.check_out_btn.pack(side='left', padx=10)
        
        self.emp_id_entry.bind('<KeyRelease>', self.update_employee_info)
        
        daily_frame = ttk.LabelFrame(self.root, text="سجل الحضور اليومي", padding=(15, 10))
        daily_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        columns = ('emp_id', 'emp_name', 'check_in', 'check_out', 'hours')
        self.daily_tree = ttk.Treeview(daily_frame, columns=columns, show='headings', height=10)
        
        self.daily_tree.heading('emp_id', text='كود الموظف')
        self.daily_tree.heading('emp_name', text='اسم الموظف')
        self.daily_tree.heading('check_in', text='وقت الحضور')
        self.daily_tree.heading('check_out', text='وقت الانصراف')
        self.daily_tree.heading('hours', text='عدد الساعات')
        
        self.daily_tree.column('emp_id', width=120, anchor='center')
        self.daily_tree.column('emp_name', width=180, anchor='center')
        self.daily_tree.column('check_in', width=180, anchor='center')
        self.daily_tree.column('check_out', width=180, anchor='center')
        self.daily_tree.column('hours', width=100, anchor='center')
        
        self.daily_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(daily_frame, orient='vertical', command=self.daily_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.daily_tree.configure(yscrollcommand=scrollbar.set)
        
        back_btn = ttk.Button(self.root, text="العودة", command=self.create_login_page,
                            style='Accent.TButton')
        back_btn.pack(pady=10, ipadx=10, ipady=5)
        
        self.update_daily_attendance()
    
    def create_admin_ui(self):
        """إنشاء واجهة المدير"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        title_frame = tk.Frame(self.root, bg='#f0f2f5')
        title_frame.pack(fill='x', pady=10)
        
        tk.Label(title_frame, text="واجهة المدير", font=('Arial', 16, 'bold'), 
                bg='#f0f2f5').pack()
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.management_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.management_tab, text='إدارة الموظفين')
        
        self.reports_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reports_tab, text='التقارير')
        
        self.create_management_tab()
        self.create_reports_tab()
        
        back_btn = ttk.Button(self.root, text="العودة", command=self.create_login_page,
                            style='Accent.TButton')
        back_btn.pack(pady=10, ipadx=10, ipady=5)
    
    def create_management_tab(self):
        """إنشاء تبويب إدارة الموظفين"""
        add_emp_frame = ttk.LabelFrame(self.management_tab, text="إضافة موظف جديد", padding=(20, 15))
        add_emp_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(add_emp_frame, text="كود الموظف:", font=('Arial', 12)).grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.new_emp_id = ttk.Entry(add_emp_frame, width=20, font=('Arial', 12))
        self.new_emp_id.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        ttk.Label(add_emp_frame, text="اسم الموظف:", font=('Arial', 12)).grid(row=1, column=0, padx=10, pady=10, sticky='e')
        self.new_emp_name = ttk.Entry(add_emp_frame, width=20, font=('Arial', 12))
        self.new_emp_name.grid(row=1, column=1, padx=10, pady=10, sticky='w')
        
        ttk.Label(add_emp_frame, text="القسم:", font=('Arial', 12)).grid(row=2, column=0, padx=10, pady=10, sticky='e')
        self.new_emp_dept = ttk.Entry(add_emp_frame, width=20, font=('Arial', 12))
        self.new_emp_dept.grid(row=2, column=1, padx=10, pady=10, sticky='w')
        
        ttk.Label(add_emp_frame, text="سعر الساعه:", font=('Arial', 12)).grid(row=3, column=0, padx=10, pady=10, sticky='e')
        self.new_emp_salary = ttk.Entry(add_emp_frame, width=20, font=('Arial', 12))
        self.new_emp_salary.grid(row=3, column=1, padx=10, pady=10, sticky='w')
        
        add_btn = ttk.Button(add_emp_frame, text="إضافة موظف", command=self.add_employee,
                            style='Accent.TButton')
        add_btn.grid(row=4, column=0, columnspan=2, pady=15, ipadx=10, ipady=5)
        
        emp_list_frame = ttk.LabelFrame(self.management_tab, text="قائمة الموظفين", padding=(15, 10))
        emp_list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        columns = ('emp_id', 'emp_name', 'department', 'monthly_salary', 'hourly_rate')
        self.emp_tree = ttk.Treeview(emp_list_frame, columns=columns, show='headings', height=10)
        
        self.emp_tree.heading('emp_id', text='كود الموظف')
        self.emp_tree.heading('emp_name', text='اسم الموظف')
        self.emp_tree.heading('department', text='القسم')
        self.emp_tree.heading('monthly_salary', text='الراتب الشهري')
        self.emp_tree.heading('hourly_rate', text='سعر الساعه')
        
        self.emp_tree.column('emp_id', width=100, anchor='center')
        self.emp_tree.column('emp_name', width=150, anchor='center')
        self.emp_tree.column('department', width=120, anchor='center')
        self.emp_tree.column('monthly_salary', width=120, anchor='center')
        self.emp_tree.column('hourly_rate', width=100, anchor='center')
        
        self.emp_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(emp_list_frame, orient='vertical', command=self.emp_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.emp_tree.configure(yscrollcommand=scrollbar.set)
        
        del_btn_frame = ttk.Frame(emp_list_frame)
        del_btn_frame.pack(fill='x', pady=5)
        
        del_btn = ttk.Button(del_btn_frame, text="حذف الموظف المحدد", command=self.delete_employee,
                           style='Accent.TButton')
        del_btn.pack(side='right', padx=5, ipadx=10, ipady=5)
        
        self.update_employees_list()
    
    def create_reports_tab(self):
        """إنشاء تبويب التقارير"""
        report_type_frame = ttk.LabelFrame(self.reports_tab, text="نوع التقرير", padding=(20, 15))
        report_type_frame.pack(fill='x', padx=20, pady=10)
        
        self.report_type = tk.StringVar(value='daily')
        
        ttk.Radiobutton(report_type_frame, text="تقرير يومي", variable=self.report_type, 
                       value='daily', command=self.update_report_ui).pack(side='right', padx=15)
        ttk.Radiobutton(report_type_frame, text="تقرير شهري", variable=self.report_type, 
                       value='monthly', command=self.update_report_ui).pack(side='right', padx=15)
        
        self.report_criteria_frame = ttk.LabelFrame(self.reports_tab, text="معايير التقرير", padding=(20, 15))
        self.report_criteria_frame.pack(fill='x', padx=20, pady=10)
        
        report_result_frame = ttk.LabelFrame(self.reports_tab, text="نتائج التقرير", padding=(15, 10))
        report_result_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.report_tree = ttk.Treeview(report_result_frame)
        self.report_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(report_result_frame, orient='vertical', command=self.report_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.report_tree.configure(yscrollcommand=scrollbar.set)
        
        export_frame = ttk.Frame(report_result_frame)
        export_frame.pack(fill='x', pady=5)
        
        pdf_btn = ttk.Button(export_frame, text="تصدير PDF", command=self.export_pdf,
                           style='Accent.TButton')
        pdf_btn.pack(side='right', padx=5, ipadx=10, ipady=5)
        
        excel_btn = ttk.Button(export_frame, text="تصدير Excel", command=self.export_excel,
                             style='Accent.TButton')
        excel_btn.pack(side='right', padx=5, ipadx=10, ipady=5)
        
        self.update_report_ui()
    
    def update_report_ui(self):
        """تحديث واجهة التقارير بناءً على نوع التقرير المحدد"""
        for widget in self.report_criteria_frame.winfo_children():
            widget.destroy()
        
        if self.report_type.get() == 'daily':
            ttk.Label(self.report_criteria_frame, text="تاريخ التقرير:", font=('Arial', 12)).pack(side='right', padx=10)
            
            self.report_date = ttk.Entry(self.report_criteria_frame, width=15, font=('Arial', 12))
            self.report_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
            self.report_date.pack(side='right', padx=10)
            
            ttk.Button(self.report_criteria_frame, text="عرض التقرير", command=self.generate_daily_report,
                     style='Accent.TButton').pack(side='right', padx=10, ipadx=10, ipady=5)
            
            self.report_tree['columns'] = ('emp_id', 'emp_name', 'check_in', 'check_out', 'hours', 'salary')
            
            for col in self.report_tree['columns']:
                self.report_tree.heading(col, text='')
            
            self.report_tree.heading('emp_id', text='كود الموظف')
            self.report_tree.heading('emp_name', text='اسم الموظف')
            self.report_tree.heading('check_in', text='وقت الحضور')
            self.report_tree.heading('check_out', text='وقت الانصراف')
            self.report_tree.heading('hours', text='عدد الساعات')
            self.report_tree.heading('salary', text='الراتب')
            
            for col in self.report_tree['columns']:
                self.report_tree.column(col, width=100, anchor='center')
        
        else:
            date_frame = ttk.Frame(self.report_criteria_frame)
            date_frame.pack(side='right', padx=10)
            
            ttk.Label(date_frame, text="من تاريخ:", font=('Arial', 10)).grid(row=0, column=0, padx=5)
            self.start_date = ttk.Entry(date_frame, width=12, font=('Arial', 10))
            self.start_date.insert(0, datetime.now().replace(day=1).strftime('%Y-%m-%d'))
            self.start_date.grid(row=0, column=1, padx=5)
            
            ttk.Label(date_frame, text="إلى تاريخ:", font=('Arial', 10)).grid(row=1, column=0, padx=5)
            self.end_date = ttk.Entry(date_frame, width=12, font=('Arial', 10))
            self.end_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
            self.end_date.grid(row=1, column=1, padx=5)
            
            ttk.Label(self.report_criteria_frame, text="كود الموظف:", font=('Arial', 12)).pack(side='right', padx=10)
            
            self.monthly_emp_id = ttk.Entry(self.report_criteria_frame, width=10, font=('Arial', 12))
            self.monthly_emp_id.pack(side='right', padx=10)
            
            ttk.Button(self.report_criteria_frame, text="عرض التقرير", command=self.generate_monthly_report,
                     style='Accent.TButton').pack(side='right', padx=10, ipadx=10, ipady=5)
            
            self.report_tree['columns'] = ('date', 'check_in', 'check_out', 'hours', 'salary')
            
            for col in self.report_tree['columns']:
                self.report_tree.heading(col, text='')
            
            self.report_tree.heading('date', text='التاريخ')
            self.report_tree.heading('check_in', text='وقت الحضور')
            self.report_tree.heading('check_out', text='وقت الانصراف')
            self.report_tree.heading('hours', text='عدد الساعات')
            self.report_tree.heading('salary', text='الراتب')
            
            for col in self.report_tree['columns']:
                self.report_tree.column(col, width=120, anchor='center')
    
    def update_employees_list(self):
        """تحديث قائمة الموظفين"""
        for item in self.emp_tree.get_children():
            self.emp_tree.delete(item)
        
        for emp_id, emp_data in self.employees.items():
            monthly_salary = emp_data.get('monthly_salary', 0)
            hourly_rate = self.calculate_hourly_rate(monthly_salary) if monthly_salary else 0
            
            self.emp_tree.insert('', 'end', values=(
                emp_id, 
                emp_data['name'], 
                emp_data.get('department', ''),
                monthly_salary,
                hourly_rate
            ))
    
    def update_daily_attendance(self):
        """تحديث سجل الحضور اليومي"""
        for item in self.daily_tree.get_children():
            self.daily_tree.delete(item)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today in self.attendance:
            for emp_id, records in self.attendance[today].items():
                if emp_id in self.employees:
                    emp_name = self.employees[emp_id]['name']
                    total_hours = 0
                    
                    for i, record in enumerate(records, 1):
                        check_in = record.get('check_in', '')
                        check_out = record.get('check_out', '')
                        
                        hours = ''
                        if check_in and check_out:
                            try:
                                time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                                time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                                delta = time_out - time_in
                                hours = round(delta.total_seconds() / 3600, 2)
                                total_hours += hours
                            except ValueError:
                                hours = ''
                        
                        self.daily_tree.insert('', 'end', 
                            values=(f"{emp_id} ({i})", emp_name, check_in, check_out, hours))
                    
                    if total_hours > 0:
                        self.daily_tree.insert('', 'end', 
                            values=(f"{emp_id} (الإجمالي)", emp_name, "", "", total_hours),
                            tags=('total',))
                        self.daily_tree.tag_configure('total', background='#e6f7ff', font=('Arial', 10, 'bold'))
    
    def update_employee_info(self, event=None):
        """تحديث معلومات الموظف عند إدخال الكود"""
        emp_id = self.emp_id_entry.get()
        if emp_id in self.employees:
            self.emp_name_label.config(text=self.employees[emp_id]['name'])
            
            has_open, open_date = self.has_open_checkin(emp_id)
            if has_open:
                if open_date == datetime.now().strftime('%Y-%m-%d'):
                    self.emp_status_label.config(text="متحضر اليوم", foreground='green')
                else:
                    self.emp_status_label.config(text=f"متحضر من {open_date}", foreground='orange')
                self.check_in_btn.config(state='disabled')
                self.check_out_btn.config(state='normal')
            else:
                self.emp_status_label.config(text="منصرف", foreground='blue')
                self.check_in_btn.config(state='normal')
                self.check_out_btn.config(state='disabled')
        else:
            self.emp_name_label.config(text="")
            self.emp_status_label.config(text="")
            self.check_in_btn.config(state='normal')
            self.check_out_btn.config(state='normal')
    
    def check_in(self):
        """تسجيل الحضور"""
        emp_id = self.emp_id_entry.get()
        
        if not emp_id:
            messagebox.showerror("خطأ", "يرجى إدخال كود الموظف")
            return
        
        if emp_id not in self.employees:
            messagebox.showerror("خطأ", "كود الموظف غير مسجل")
            return
        
        has_open, open_date = self.has_open_checkin(emp_id)
        if has_open:
            messagebox.showerror("خطأ", f"الموظف متحضر بالفعل من تاريخ {open_date}\nيجب تسجيل الانصراف أولاً")
            return
        
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.attendance[today][emp_id].append({
            'check_in': now,
            'check_out': ''
        })
        
        self.save_data()
        messagebox.showinfo("تم", "تم تسجيل الحضور بنجاح")
        self.update_daily_attendance()
        self.update_employee_info()
    
    def check_out(self):
        """تسجيل الانصراف"""
        emp_id = self.emp_id_entry.get()
        
        if not emp_id:
            messagebox.showerror("خطأ", "يرجى إدخال كود الموظف")
            return
        
        if emp_id not in self.employees:
            messagebox.showerror("خطأ", "كود الموظف غير مسجل")
            return
        
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
        
        if not found_record:
            messagebox.showerror("خطأ", "لا يوجد حضور مسجل يحتاج إلى انصراف")
            return
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        found_record['check_out'] = now
        self.save_data()
        
        if found_date != datetime.now().strftime('%Y-%m-%d'):
            messagebox.showinfo("تم", f"تم تسجيل الانصراف بنجاح\nتم إغلاق جلسة الحضور من تاريخ {found_date}")
        else:
            messagebox.showinfo("تم", "تم تسجيل الانصراف بنجاح")
            
        self.update_daily_attendance()
        self.update_employee_info()
    
    def add_employee(self):
        """إضافة موظف جديد"""
        emp_id = self.new_emp_id.get()
        emp_name = self.new_emp_name.get()
        emp_dept = self.new_emp_dept.get()
        emp_salary = self.new_emp_salary.get()
        
        if not emp_id or not emp_name:
            messagebox.showerror("خطأ", "يرجى إدخال كود الموظف واسمه")
            return
        
        if emp_id in self.employees:
            messagebox.showerror("خطأ", "كود الموظف مسجل مسبقاً")
            return
        
        try:
            monthly_salary = float(emp_salary) if emp_salary else 0
        except ValueError:
            messagebox.showerror("خطأ", "الراتب يجب أن يكون رقماً")
            return
        
        self.employees[emp_id] = {
            'name': emp_name,
            'department': emp_dept,
            'monthly_salary': monthly_salary
        }
        
        self.save_data()
        
        messagebox.showinfo("تم", "تم إضافة الموظف بنجاح")
        
        self.new_emp_id.delete(0, 'end')
        self.new_emp_name.delete(0, 'end')
        self.new_emp_dept.delete(0, 'end')
        self.new_emp_salary.delete(0, 'end')
        
        self.update_employees_list()
    
    def delete_employee(self):
        """حذف موظف"""
        selected_item = self.emp_tree.selection()
        
        if not selected_item:
            messagebox.showerror("خطأ", "يرجى اختيار موظف للحذف")
            return
        
        emp_id = self.emp_tree.item(selected_item)['values'][0]
        
        if not messagebox.askyesno("تأكيد", f"هل أنت متأكد من حذف الموظف {emp_id}؟"):
            return
        
        del self.employees[emp_id]
        
        for date in list(self.attendance.keys()):
            if emp_id in self.attendance[date]:
                del self.attendance[date][emp_id]
            
            if not self.attendance[date]:
                del self.attendance[date]
        
        self.save_data()
        
        messagebox.showinfo("تم", "تم حذف الموظف بنجاح")
        self.update_employees_list()
    
    def generate_daily_report(self):
        """توليد التقرير اليومي"""
        report_date = self.report_date.get()
        
        try:
            datetime.strptime(report_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("خطأ", "صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD")
            return
        
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        
        if report_date in self.attendance:
            for emp_id, records in self.attendance[report_date].items():
                if emp_id in self.employees:
                    emp_name = self.employees[emp_id]['name']
                    monthly_salary = self.employees[emp_id].get('monthly_salary', 0)
                    hourly_rate = self.calculate_hourly_rate(monthly_salary) if monthly_salary else 0
                    total_hours = 0
                    
                    for i, record in enumerate(records, 1):
                        check_in = record.get('check_in', '')
                        check_out = record.get('check_out', '')
                        
                        hours = ''
                        salary = ''
                        if check_in and check_out:
                            try:
                                time_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                                time_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                                delta = time_out - time_in
                                hours = round(delta.total_seconds() / 3600, 2)
                                total_hours += hours
                                salary = self.calculate_salary(hourly_rate, hours)
                            except ValueError:
                                hours = ''
                                salary = ''
                        
                        self.report_tree.insert('', 'end', 
                            values=(f"{emp_id} ({i})", emp_name, check_in, check_out, hours, salary))
                    
                    if total_hours > 0:
                        total_salary = self.calculate_salary(hourly_rate, total_hours)
                        self.report_tree.insert('', 'end', 
                            values=(f"{emp_id} (الإجمالي)", emp_name, "", "", total_hours, total_salary),
                            tags=('total',))
                        self.report_tree.tag_configure('total', background='#e6f7ff', font=('Arial', 10, 'bold'))
        else:
            messagebox.showinfo("معلومة", "لا توجد بيانات للتاريخ المحدد")
    
    def generate_monthly_report(self):
        """توليد التقرير الشهري مع فلتر التاريخ"""
        emp_id = self.monthly_emp_id.get()
        start_date_str = self.start_date.get()
        end_date_str = self.end_date.get()
        
        if not emp_id:
            messagebox.showerror("خطأ", "يرجى إدخال كود الموظف")
            return
        
        if emp_id not in self.employees:
            messagebox.showerror("خطأ", "كود الموظف غير مسجل")
            return
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            if start_date > end_date:
                messagebox.showerror("خطأ", "تاريخ البداية يجب أن يكون أقل من تاريخ النهاية")
                return
                
        except ValueError:
            messagebox.showerror("خطأ", "صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD")
            return
        
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        
        monthly_salary = self.employees[emp_id].get('monthly_salary', 0)
        hourly_rate = self.calculate_hourly_rate(monthly_salary) if monthly_salary else 0
        
        total_period_hours = 0
        total_period_salary = 0
        daily_totals = defaultdict(float)
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str in self.attendance and emp_id in self.attendance[date_str]:
                day_total = 0
                
                for record in self.attendance[date_str][emp_id]:
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
                    daily_totals[date_str] = day_total
                    total_period_hours += day_total
                    day_salary = self.calculate_salary(hourly_rate, day_total)
                    total_period_salary += day_salary
                    
                    first_checkin = self.attendance[date_str][emp_id][0].get('check_in', '')
                    last_checkout = ''
                    for record in reversed(self.attendance[date_str][emp_id]):
                        if record.get('check_out'):
                            last_checkout = record.get('check_out', '')
                            break
                    
                    self.report_tree.insert('', 'end', 
                        values=(date_str, first_checkin, last_checkout, day_total, day_salary))
            
            current_date += timedelta(days=1)
        
        if total_period_hours > 0:
            self.report_tree.insert('', 'end', 
                values=(f"الإجمالي ({start_date_str} إلى {end_date_str})", "", "", total_period_hours, total_period_salary),
                tags=('total',))
            self.report_tree.tag_configure('total', background='#e6f7ff', font=('Arial', 10, 'bold'))
        else:
            messagebox.showinfo("معلومة", "لا توجد بيانات للفترة المحددة")
    
    def export_pdf(self):
        """تصدير التقرير إلى PDF"""
        if not self.report_tree.get_children():
            messagebox.showerror("خطأ", "لا توجد بيانات للتصدير")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="حفظ التقرير كـ PDF"
        )
        
        if not file_path:
            return
        
        pdf = FPDF()
        pdf.add_page()
        
        try:
            pdf.add_font('Arial', '', 'arial.ttf', uni=True)
            pdf.set_font('Arial', '', 12)
        except:
            pdf.set_font('Arial', '', 12)
        
        if self.report_type.get() == 'daily':
            title = f"تقرير الحضور اليومي - {self.report_date.get()}"
        else:
            title = f"تقرير الحضور للفترة - {self.start_date.get()} إلى {self.end_date.get()} للموظف {self.monthly_emp_id.get()}"
        
        pdf.cell(0, 10, title, 0, 1, 'C')
        pdf.ln(10)
        
        if self.report_type.get() == 'daily':
            col_widths = [25, 35, 35, 35, 25, 25]
            headers = ['كود الموظف', 'اسم الموظف', 'وقت الحضور', 'وقت الانصراف', 'الساعات', 'الراتب']
        else:
            col_widths = [35, 35, 35, 25, 25]
            headers = ['التاريخ', 'وقت الحضور', 'وقت الانصراف', 'الساعات', 'الراتب']
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        for item in self.report_tree.get_children():
            values = self.report_tree.item(item)['values']
            
            if "الإجمالي" in str(values[0]):
                continue
            
            for i, value in enumerate(values):
                pdf.cell(col_widths[i], 10, str(value), 1, 0, 'C')
            pdf.ln()
        
        for item in self.report_tree.get_children():
            values = self.report_tree.item(item)['values']
            if "الإجمالي" in str(values[0]):
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(sum(col_widths[:-2]), 10, "الإجمالي:", 1, 0, 'R')
                pdf.cell(col_widths[-2], 10, str(values[-2]), 1, 0, 'C')
                pdf.cell(col_widths[-1], 10, str(values[-1]), 1, 0, 'C')
                pdf.set_font('Arial', '', 12)
                break
        
        pdf.output(file_path)
        messagebox.showinfo("تم", f"تم تصدير التقرير إلى {file_path}")
    
    def export_excel(self):
        """تصدير التقرير إلى Excel"""
        if not self.report_tree.get_children():
            messagebox.showerror("خطأ", "لا توجد بيانات للتصدير")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            title="حفظ التقرير كـ Excel"
        )
        
        if not file_path:
            return
        
        data = []
        columns = []
        
        if self.report_type.get() == 'daily':
            columns = ['كود الموظف', 'اسم الموظف', 'وقت الحضور', 'وقت الانصراف', 'الساعات', 'الراتب']
        else:
            columns = ['التاريخ', 'وقت الحضور', 'وقت الانصراف', 'الساعات', 'الراتب']
        
        for item in self.report_tree.get_children():
            values = self.report_tree.item(item)['values']
            data.append(values)
        
        df = pd.DataFrame(data, columns=columns)
        
        try:
            df.to_excel(file_path, index=False, engine='openpyxl')
            messagebox.showinfo("تم", f"تم تصدير التقرير إلى {file_path}")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء التصدير: {str(e)}")

# تشغيل التطبيق
if __name__ == "__main__":
    root = tk.Tk()
    
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Accent.TButton', foreground='white', background='#4CAF50', font=('Arial', 10, 'bold'))
    style.map('Accent.TButton', background=[('active', '#45a049')])
    
    app = EmployeeAttendanceSystem(root)
    root.mainloop()
