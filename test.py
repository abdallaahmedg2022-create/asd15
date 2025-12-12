# app.py
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from fpdf import FPDF
from collections import defaultdict

# إعداد الصفحة مع دعم RTL للعربية
st.set_page_config(page_title="نظام حضور وانصراف الموظفين", layout="wide")

# تحسين الاتجاه للنصوص العربية
st.markdown("""
<style>
    .css-1d391kg {direction: rtl; text-align: right;}
    .css-1y0tuds {direction: rtl;}
    body {direction: rtl;}
    .stButton>button {width: 100%;}
</style>
""", unsafe_allow_html=True)

# كلمة السر للمدير
ADMIN_PASSWORD = "a2cf1543"

# إنشاء مجلد البيانات إذا لم يكن موجوداً
if not os.path.exists('data'):
    os.makedirs('data')

# تحميل البيانات مع الكاش لتحسين الأداء
@st.cache_data
def load_data():
    employees = {}
    attendance = defaultdict(lambda: defaultdict(list))
    
    # تحميل بيانات الموظفين
    try:
        with open('data/employees.json', 'r', encoding='utf-8') as f:
            employees = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        employees = {}
    
    # تحميل سجلات الحضور
    try:
        with open('data/attendance.json', 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            for date, emps in old_data.items():
                for emp_id, records in emps.items():
                    if isinstance(records, list):
                        attendance[date][emp_id] = records
                    elif isinstance(records, dict):
                        # تحويل الهيكل القديم
                        attendance[date][emp_id] = [{
                            'check_in': records.get('check_in', ''),
                            'check_out': records.get('check_out', '')
                        }]
                    else:
                        attendance[date][emp_id] = []
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    return employees, attendance

def save_data(employees, attendance):
    # حفظ الموظفين
    with open('data/employees.json', 'w', encoding='utf-8') as f:
        json.dump(employees, f, indent=4, ensure_ascii=False)
    
    # حفظ الحضور (تحويل إلى dict عادي للحفظ)
    normal_dict = {date: dict(emps) for date, emps in attendance.items()}
    with open('data/attendance.json', 'w', encoding='utf-8') as f:
        json.dump(normal_dict, f, indent=4, ensure_ascii=False)
    
    # مسح الكاش لتحديث البيانات
    st.cache_data.clear()

def calculate_hourly_rate(monthly_salary):
    return round(monthly_salary / 26, 2) if monthly_salary else 0

def calculate_salary(hourly_rate, hours):
    return round(hourly_rate * hours, 2)

# تحميل البيانات عند بدء التطبيق
employees, attendance = load_data()

# إدارة الصفحات باستخدام session_state
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'report_data' not in st.session_state:
    st.session_state.report_data = None

# ------------------- صفحة تسجيل الدخول -------------------
if st.session_state.page == 'login':
    st.title("🏢 نظام حضور وانصراف الموظفين")
    st.markdown("### مرحباً بك في النظام")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👤 دخول كموظف", use_container_width=True):
            st.session_state.page = 'employee'
            st.rerun()
    with col2:
        if st.button("👨‍💼 دخول كمدير", use_container_width=True):
            st.session_state.page = 'admin_login'
            st,st.rerun()

# ------------------- صفحة دخول المدير -------------------
elif st.session_state.page == 'admin_login':
    st.title("🔐 دخول المدير")
    password = st.text_input("أدخل كلمة السر:", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("دخول"):
            if password == ADMIN_PASSWORD:
                st.session_state.page = 'admin'
                st.success("تم تسجيل الدخول بنجاح!")
                st.rerun()
            else:
                st.error("كلمة السر غير صحيحة")
    with col2:
        if st.button("عودة"):
            st.session_state.page = 'login'
            st.rerun()

# ------------------- واجهة الموظف -------------------
elif st.session_state.page == 'employee':
    st.title("👤 واجهة الموظف - تسجيل الحضور والانصراف")
    
    if st.button("🔙 العودة"):
        st.session_state.page = 'login'
        st.rerun()
    
    st.markdown("---")
    emp_id = st.text_input("🔑 كود الموظف")
    
    if emp_id:
        if emp_id in employees:
            emp_name = employees[emp_id]['name']
            st.success(f"اسم الموظف: **{emp_name}**")
            
            # التحقق من وجود حضور مفتوح
            has_open = False
            open_date = None
            for date in attendance:
                if emp_id in attendance[date]:
                    for rec in attendance[date][emp_id]:
                        if rec['check_in'] and not rec['check_out']:
                            has_open = True
                            open_date = date
                            break
                    if has_open:
                        break
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🟢 تسجيل الحضور", disabled=has_open, use_container_width=True):
                    if has_open:
                        st.warning(f"لديك حضور مفتوح من تاريخ {open_date}")
                    else:
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        attendance[today][emp_id].append({'check_in': now, 'check_out': ''})
                        save_data(employees, attendance)
                        st.success("✅ تم تسجيل الحضور بنجاح!")
                        st.rerun()
            
            with col2:
                if st.button("🔴 تسجيل الانصراف", disabled=not has_open, use_container_width=True):
                    found = False
                    for date in sorted(attendance.keys(), reverse=True):
                        if emp_id in attendance[date]:
                            for rec in reversed(attendance[date][emp_id]):
                                if rec['check_in'] and not rec['check_out']:
                                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    rec['check_out'] = now
                                    save_data(employees, attendance)
                                    st.success("✅ تم تسجيل الانصراف بنجاح!")
                                    found = True
                                    break
                            if found:
                                break
                    st.rerun()
        else:
            st.error("❌ كود الموظف غير موجود")
    
    st.markdown("---")
    st.subheader(f"📅 سجل الحضور اليومي - {datetime.now().strftime('%Y-%m-%d')}")
    
    today = datetime.now().strftime('%Y-%m-%d')
    daily_data = []
    if today in attendance:
        for emp_id, records in attendance[today].items():
            if emp_id in employees:
                emp_name = employees[emp_id]['name']
                total_hours = 0
                for i, rec in enumerate(records, 1):
                    cin = rec.get('check_in', '')
                    cout = rec.get('check_out', '')
                    hours = 0
                    if cin and cout:
                        try:
                            tin = datetime.strptime(cin, '%Y-%m-%d %H:%M:%S')
                            tout = datetime.strptime(cout, '%Y-%m-%d %H:%M:%S')
                            hours = round((tout - tin).total_seconds() / 3600, 2)
                            total_hours += hours
                        except:
                            pass
                    daily_data.append({
                        "كود الموظف": f"{emp_id} ({i})",
                        "الاسم": emp_name,
                        "الحضور": cin,
                        "الانصراف": cout,
                        "الساعات": hours
                    })
                if total_hours > 0:
                    daily_data.append({
                        "كود الموظف": f"{emp_id} (إجمالي)",
                        "الاسم": emp_name,
                        "الحضور": "",
                        "الانصراف": "",
                        "الساعات": total_hours
                    })
    
    if daily_data:
        df = pd.DataFrame(daily_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد بيانات حضور اليوم")

# ------------------- واجهة المدير -------------------
elif st.session_state.page == 'admin':
    st.title("👨‍💼 واجهة المدير")
    
    if st.button("🔙 العودة"):
        st.session_state.page = 'login'
        st.rerun()
    
    tab1, tab2 = st.tabs(["إدارة الموظفين", "التقارير"])
    
    with tab1:
        st.subheader("➕ إضافة موظف جديد")
        col1, col2 = st.columns(2)
        with col1:
            new_id = st.text_input("كود الموظف")
            new_name = st.text_input("اسم الموظف")
        with col2:
            new_dept = st.text_input("القسم (اختياري)")
            new_salary = st.number_input("الراتب الشهري", min_value=0.0, step=100.0)
        
        if st.button("إضافة الموظف", use_container_width=True):
            if not new_id or not new_name:
                st.error("كود الموظف والاسم مطلوبان")
            elif new_id in employees:
                st.error("هذا الكود موجود مسبقاً")
            else:
                employees[new_id] = {
                    'name': new_name,
                    'department': new_dept,
                    'monthly_salary': float(new_salary)
                }
                save_data(employees, attendance)
                st.success("تم إضافة الموظف بنجاح")
                st.rerun()
        
        st.markdown("---")
        st.subheader("📋 قائمة الموظفين")
        emp_list = []
        for eid, data in employees.items():
            emp_list.append({
                "كود": eid,
                "الاسم": data['name'],
                "القسم": data.get('department', ''),
                "الراتب الشهري": data.get('monthly_salary', 0),
                "سعر الساعة": calculate_hourly_rate(data.get('monthly_salary', 0))
            })
        if emp_list:
            df_emp = pd.DataFrame(emp_list)
            st.dataframe(df_emp, use_container_width=True)
            
            del_id = st.text_input("كود الموظف المراد حذفه")
            if st.button("🗑️ حذف الموظف") and del_id in employees:
                if st.button(f"تأكيد حذف {employees[del_id]['name']}؟"):
                    del employees[del_id]
                    for date in list(attendance.keys()):
                        if del_id in attendance[date]:
                            del attendance[date][del_id]
                        if not attendance[date]:
                            del attendance[date]
                    save_data(employees, attendance)
                    st.success("تم الحذف بنجاح")
                    st.rerun()
        else:
            st.info("لا توجد موظفين مسجلين")
    
    with tab2:
        st.subheader("📊 توليد التقارير")
        report_type = st.radio("اختر نوع التقرير", ["تقرير يومي", "تقرير شهري"])
        
        if report_type == "تقرير يومي":
            report_date = st.date_input("التاريخ", datetime.now())
            if st.button("عرض التقرير اليومي"):
                st.session_state.report_data = (report_date.strftime('%Y-%m-%d'), "daily")
                st.rerun()
        
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("من تاريخ", datetime.now().replace(day=1))
                monthly_emp_id = st.text_input("كود الموظف")
            with col2:
                end_date = st.date_input("إلى تاريخ", datetime.now())
            
            if st.button("عرض التقرير الشهري") and monthly_emp_id:
                if monthly_emp_id not in employees:
                    st.error("كود الموظف غير موجود")
                else:
                    st.session_state.report_data = ((start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), monthly_emp_id), "monthly")
                    st.rerun()
        
        # عرض التقرير إذا تم اختياره
        if st.session_state.report_data:
            data, rtype = st.session_state.report_data
            report_rows = []
            title = ""
            
            if rtype == "daily":
                date_str = data
                title = f"تقرير ي cachي - {date_str}"
                if date_str in attendance:
                    for emp_id, records in attendance[date_str].items():
                        if emp_id in employees:
                            emp_name = employees[emp_id]['name']
                            hourly = calculate_hourly_rate(employees[emp_id].get('monthly_salary', 0))
                            total_h = 0
                            for i, rec in enumerate(records, 1):
                                cin = rec.get('check_in', '')
                                cout = rec.get('check_out', '')
                                h = 0
                                sal = 0
                                if cin and cout:
                                    try:
                                        tin = datetime.strptime(cin, '%Y-%m-%d %H:%M:%S')
                                        tout = datetime.strptime(cout, '%Y-%m-%d %H:%M:%S')
                                        h = round((tout - tin).total_seconds() / 3600, 2)
                                        sal = calculate_salary(hourly, h)
                                        total_h += h
                                    except:
                                        pass
                                report_rows.append({
                                    "كود": f"{emp_id} ({i})",
                                    "الاسم": emp_name,
                                    "الحضور": cin,
                                    "الانصراف": cout,
                                    "الساعات": h,
                                    "الراتب": sal
                                })
                            if total_h > 0:
                                report_rows.append({
                                    "كود": "إجمالي",
                                    "الاسم": emp_name,
                                    "الحضور": "",
                                    "الانصراف": "",
                                    "الساعات": total_h,
                                    "الراتب": calculate_salary(hourly, total_h)
                                })
            
            else:
                start_str, end_str, emp_id = data
                title = f"تقرير شهري للموظف {employees[emp_id]['name']} من {start_str} إلى {end_str}"
                hourly = calculate_hourly_rate(employees[emp_id].get('monthly_salary', 0))
                total_h = 0
                total_sal = 0
                current = datetime.strptime(start_str, '%Y-%m-%d')
                end = datetime.strptime(end_str, '%Y-%m-%d')
                
                while current <= end:
                    dstr = current.strftime('%Y-%m-%d')
                    day_h = 0
                    first_in = ""
                    last_out = ""
                    if dstr in attendance and emp_id in attendance[dstr]:
                        recs = attendance[dstr][emp_id]
                        if recs:
                            first_in = recs[0].get('check_in', '')
                            for rec in reversed(recs):
                                if rec.get('check_out'):
                                    last_out = rec.get('check_out', '')
                                    break
                        for rec in recs:
                            cin = rec.get('check_in', '')
                            cout = rec.get('check_out', '')
                            if cin and cout:
                                try:
                                    tin = datetime.strptime(cin, '%Y-%m-%d %H:%M:%S')
                                    tout = datetime.strptime(cout, '%Y-%m-%d %H:%M:%S')
                                    h = round((tout - tin).total_seconds() / 3600, 2)
                                    day_h += h
                                except:
                                    pass
                    if day_h > 0:
                        day_sal = calculate_salary(hourly, day_h)
                        total_h += day_h
                        total_sal += day_sal
                        report_rows.append({
                            "التاريخ": dstr,
                            "الحضور": first_in,
                            "الانصراف": last_out,
                            "الساعات": day_h,
                            "الراتب": day_sal
                        })
                    current += timedelta(days=1)
                
                if total_h > 0:
                    report_rows.append({
                        "التاريخ": f"إجمالي الفترة",
                        "الحضور": "",
                        "الانصراف": "",
                        "الساعات": total_h,
                        "الراتب": total_sal
                    })
            
            if report_rows:
                st.subheader(title)
                df_report = pd.DataFrame(report_rows)
                st.dataframe(df_report, use_container_width=True)
                
                # تصدير Excel (CSV)
                csv = df_report.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 تحميل Excel (CSV)",
                    csv,
                    f"تقرير_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
                
                # تصدير PDF بسيط
                def create_pdf():
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt=title, ln=1, align='C')
                    pdf.ln(10)
                    for _, row in df_report.iterrows():
                        line = " | ".join([str(v) for v in row.values])
                        pdf.cell(200, 10, txt=line, ln=1)
                    return pdf.output(dest='S').encode('latin-1')
                
                pdf_data = create_pdf()
                st.download_button(
                    "📄 تحميل PDF",
                    pdf_data,
                    f"تقرير_{datetime.now().strftime('%Y%m%d')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
            else:
                st.info("لا توجد بيانات لهذا التقرير")
            
            if st.button("تقرير جديد"):
                st.session_state.report_data = None
                st.rerun()
