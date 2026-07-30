import os
import re
import time
import json
import base64
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Page Configuration - Luxury Deep Dark Gold & Sapphire Theme Styling
st.set_page_config(
    page_title="UOK Science Portal Auto Login",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------------------------
# CONSTANTS & CONFIGURATIONS
# ---------------------------------------------------------------------------
PORTAL_URL = "http://www.science.kln.ac.lk:8080/(S(aeobswamkffx5xku1veqzzrw))/sfkn.aspx"
TIMETABLE_URL = "http://www.science.kln.ac.lk/index.php/component/content/article/examinations"

TIMETABLE_LINK_KEYWORDS = [
    "exam admission", "examination admission", "admission",
    "exam time table", "exam timetable", "time table", "timetable"
]

DATE_REGEX = re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}')
TIME_REGEX = re.compile(r'\d{1,2}[:.]\d{2}\s*(AM|PM|am|pm)?')

GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "E": 0.0, "F": 0.0
}

STUDENT_DATABASE = {
    "PS/2020/001": "pass123",
    "SE/2020/002": "mysecurepass",
    "PS/2020/003": "student2026"
}

ALLOWED_USERS = {
    "admin": "admin123",
}

THEME = {
    "bg_primary":        "#0b0f19",
    "bg_secondary":      "#111827",
    "bg_panel":          "#1f293d",
    "bg_panel_alt":      "#2d3748",
    "accent_gold":       "#f59e0b",
    "accent_gold_hover": "#fbbf24",
    "accent_cyan":       "#38bdf8",
    "accent_blue":       "#6366f1",
    "accent_emerald":    "#10b981",
    "text_primary":      "#f9fafb",
    "text_secondary":    "#9ca3af",
    "text_muted":        "#6b7280",
    "error":             "#ef4444",
    "border":            "#374151",
}

# Inject Custom CSS to Match 100% Exact GUI Visual Design
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {THEME['bg_primary']};
        color: {THEME['text_primary']};
        font-family: 'Segoe UI', sans-serif;
    }}
    .main-header {{
        background-color: {THEME['bg_secondary']};
        padding: 20px;
        border-radius: 8px;
        border-top: 4px solid {THEME['accent_gold']};
        text-align: center;
        margin-bottom: 25px;
    }}
    .custom-card {{
        background-color: {THEME['bg_panel']};
        border: 1px solid {THEME['border']};
        padding: 24px;
        border-radius: 8px;
        margin-bottom: 20px;
    }}
    .stat-card {{
        background-color: {THEME['bg_panel']};
        border-radius: 6px;
        padding: 12px;
        text-align: center;
    }}
    .stButton>button {{
        background-color: {THEME['accent_gold']} !important;
        color: #0b0f19 !important;
        font-weight: bold !important;
        border: none !important;
        width: 100%;
        padding: 10px 0;
        border-radius: 4px;
    }}
    .stButton>button:hover {{
        background-color: {THEME['accent_gold_hover']} !important;
    }}
    /* Table Styling */
    .dataframe {{
        background-color: {THEME['bg_panel']} !important;
        color: {THEME['text_primary']} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# PARSING & SCRAPING FUNCTIONS (KEPT 100% IDENTICAL TO TKINTER LOGIC)
# ---------------------------------------------------------------------------
def parse_student_name(html_source):
    soup = BeautifulSoup(html_source, 'html.parser')
    possible_ids = ["lblStudentName", "LoginStaffNameLB1", "LoginStaffNameLB", "lblStaffName", "lblUser", "lblName"]
    for pid in possible_ids:
        elem = soup.find(id=re.compile(rf".*{pid}.*", re.IGNORECASE))
        if elem and elem.get_text(strip=True):
            txt = elem.get_text(strip=True)
            if ":" in txt:
                txt = txt.split(":")[-1].strip()
            if txt:
                return txt
    return "Student"

def parse_results_page(html_source):
    soup = BeautifulSoup(html_source, 'html.parser')
    results_data = []
    seen_codes = set()

    grade_regex = re.compile(r'^(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D|E|F|MC|I|P|PASS|FAIL)$', re.IGNORECASE)
    header_code_words = {"course code", "code", "module code", "subject code"}
    header_title_words = {"course title", "course title / details", "course name", "title", "subject", "module", "module title", "course"}

    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            if not any(cols): continue
            if len(cols) >= 2:
                code, title, grade = "", "", ""
                for col in cols:
                    col_clean = col.strip()
                    if grade_regex.match(col_clean): grade = col_clean
                    elif re.search(r'[A-Za-z]{2,5}\s*\d{4,5}', col_clean): code = col_clean
                    elif len(col_clean) > 3 and not title and col_clean.lower() not in ["course code", "course title", "grade", "marks", "subject"]:
                        title = col_clean

                if not code and len(cols) >= 3:
                    code, title = cols[0], cols[1]
                    possible_grade = cols[-1].strip()
                    if len(possible_grade) <= 4: grade = possible_grade

                if code.strip().lower() in header_code_words or title.strip().lower() in header_title_words: continue

                clean_code = code.strip().upper() if code else ""
                if clean_code and clean_code in seen_codes: continue

                if code or grade:
                    if clean_code: seen_codes.add(clean_code)
                    prefix_match = re.match(r'([A-Za-z]+)', code)
                    prefix = prefix_match.group(1).upper() if prefix_match else "OTHER"
                    semester = 1
                    credits = 2
                    digits_match = re.search(r'\d+', code)
                    if digits_match:
                        digits = digits_match.group(0)
                        if len(digits) >= 2 and digits[1] == '2': semester = 2
                        if len(digits) >= 4:
                            try: credits = int(digits[-1])
                            except: credits = 2

                    results_data.append({
                        'code': code if code else "N/A",
                        'title': title if title else "Course Module",
                        'grade': grade if grade else "Pending / -",
                        'prefix': prefix,
                        'semester': semester,
                        'credits': credits
                    })
    return results_data

def run_selenium_fetch(student_number, password, selected_year):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(PORTAL_URL)
        time.sleep(1)

        student_input, password_input, login_button = None, None, None
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            inp_type = (inp.get_attribute("type") or "").lower()
            inp_name = (inp.get_attribute("name") or "").lower()
            inp_id = (inp.get_attribute("id") or "").lower()
            if inp_type == "password" or "pass" in inp_name or "pass" in inp_id: password_input = inp
            elif inp_type in ["text", ""] or "txt" in inp_id or "user" in inp_name or "student" in inp_name:
                if not student_input: student_input = inp

        for inp in inputs:
            if (inp.get_attribute("type") or "").lower() in ["submit", "button"] or "btn" in (inp.get_attribute("id") or "").lower():
                login_button = inp
                break

        if student_input and login_button:
            student_input.clear()
            student_input.send_keys(student_number)
            if password_input and password:
                password_input.clear()
                password_input.send_keys(password)
            login_button.click()
            time.sleep(2)

            student_name = parse_student_name(driver.page_source)
            results = parse_results_page(driver.page_source)
            return student_name, results
    finally:
        driver.quit()
    return "Student", []

# ---------------------------------------------------------------------------
# STREAMLIT STATE MANAGEMENT & AUTH
# ---------------------------------------------------------------------------
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None

# SYSTEM AUTHORIZATION GATEKEEPER
if not st.session_state['authenticated']:
    st.markdown(f"""
        <div class="main-header">
            <h1 style="color: {THEME['accent_gold']}; margin: 0;">🛡️ SYSTEM AUTHORIZATION</h1>
            <p style="color: {THEME['text_secondary']}; margin-top: 5px;">Restricted Access Area • Enter System Credentials</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("sys_login"):
            sys_user = st.text_input("System Username")
            sys_pass = st.text_input("System Password", type="password")
            submit = st.form_submit_button("UNLOCK SYSTEM")

            if submit:
                if sys_user in ALLOWED_USERS and ALLOWED_USERS[sys_user] == sys_pass:
                    st.session_state['authenticated'] = True
                    st.session_state['user'] = sys_user
                    st.rerun()
                else:
                    st.error("Access Denied: Invalid System Credentials!")
    st.stop()

# ---------------------------------------------------------------------------
# MAIN AUTO-LOGIN APPLICATON
# ---------------------------------------------------------------------------
st.markdown(f"""
    <div class="main-header">
        <h1 style="color: {THEME['accent_gold']}; margin: 0;">🎓 UNIVERSITY OF KELANIYA</h1>
        <h4 style="color: {THEME['text_secondary']}; font-weight: normal; margin-top: 4px;">Faculty of Science — Exam Portal Auto-Login Suite</h4>
        <p style="color: {THEME['accent_cyan']}; font-size: 13px; margin: 0;">🔑 Logged in System Account: {st.session_state['user']}</p>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    with st.form("portal_login"):
        student_no = st.text_input("Student Number / Username *")
        password = st.text_input("Password (Required if set)", type="password")
        selected_year = st.selectbox(
            "Select Academic Year / Option *",
            ["1st Year", "2nd Year", "3rd Year", "4th Year", "📅 Exam Admission / Timetable"]
        )
        submit_fetch = st.form_submit_button("🔐 START AUTO LOGIN & FETCH")

if submit_fetch:
    if not student_no:
        st.warning("Please enter your Student Number!")
    elif student_no in STUDENT_DATABASE and password != STUDENT_DATABASE[student_no]:
        st.error("Access Denied: Incorrect Password for this Student Number!")
    else:
        with st.spinner("Connecting to University Portal and fetching academic records..."):
            s_name, results_data = run_selenium_fetch(student_no, password, selected_year)
            st.session_state['results'] = results_data
            st.session_state['student_name'] = s_name
            st.session_state['student_no'] = student_no
            st.session_state['year'] = selected_year
            st.success("🎉 Academic Data Fetched Successfully!")

# ---------------------------------------------------------------------------
# RESULTS DASHBOARD DISPLAY
# ---------------------------------------------------------------------------
if 'results' in st.session_state and st.session_state['results']:
    results = st.session_state['results']
    student_no = st.session_state['student_no']
    student_name = st.session_state['student_name']
    selected_year = st.session_state['year']

    st.markdown("---")
    st.markdown(f"""
        ### 🎓 Academic Dashboard — {student_no} ({selected_year})
        **👤 Student Name:** {student_name} | **🆔 Student No:** {student_no}
    """)

    # Filter By Subject
    prefixes = sorted(list({r['prefix'] for r in results if r['prefix'] and r['prefix'] != "OTHER"}))
    selected_prefix = st.selectbox("Filter Subject:", ["All Subjects"] + prefixes)

    filtered_results = results if selected_prefix == "All Subjects" else [r for r in results if r['prefix'] == selected_prefix]

    # Calculate Metrics & GPA
    total_modules = len(filtered_results)
    completed_modules = [r for r in filtered_results if r['grade'] in GRADE_POINTS]
    pending_modules = total_modules - len(completed_modules)

    tot_pts, tot_cr = 0.0, 0
    for item in filtered_results:
        g = item['grade'].upper()
        cr = item['credits']
        if g in GRADE_POINTS and cr > 0:
            tot_pts += GRADE_POINTS[g] * cr
            tot_cr += cr
    gpa = round(tot_pts / tot_cr, 2) if tot_cr > 0 else 0.0

    # Stat Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL MODULES", total_modules)
    m2.metric("COMPLETED", len(completed_modules))
    m3.metric("PENDING", pending_modules)
    m4.metric("FILTERED GPA", f"{gpa:.2f}")

    # Tabs (Analytics, All, Sem 1, Sem 2)
    t_overview, t_all, t_sem1, t_sem2 = st.tabs(["📊 Visual Analytics", "All Semesters", "1st Semester", "2nd Semester"])

    with t_overview:
        grade_counts = {}
        for item in filtered_results:
            g = item['grade'].upper()
            if g in GRADE_POINTS:
                grade_counts[g] = grade_counts.get(g, 0) + 1

        # Plotly Bar Chart to Replica Canvas
        fig = go.Figure(data=[
            go.Bar(x=list(grade_counts.keys()), y=list(grade_counts.values()),
                   marker_color=THEME['accent_gold'])
        ])
        fig.update_layout(
            title="📊 Grade Distribution & Visual Performance Metrics",
            paper_bgcolor=THEME['bg_panel'],
            plot_bgcolor=THEME['bg_panel'],
            font=dict(color=THEME['text_primary']),
            xaxis=dict(title="Grades"),
            yaxis=dict(title="Module Count")
        )
        st.plotly_chart(fig, use_container_width=True)

    df_filtered = pd.DataFrame(filtered_results)[['code', 'title', 'grade', 'credits']]

    with t_all:
        st.dataframe(df_filtered, use_container_width=True)

    with t_sem1:
        sem1_df = pd.DataFrame([r for r in filtered_results if r['semester'] == 1])[['code', 'title', 'grade', 'credits']]
        st.dataframe(sem1_df, use_container_width=True)

    with t_sem2:
        sem2_df = pd.DataFrame([r for r in filtered_results if r['semester'] == 2])[['code', 'title', 'grade', 'credits']]
        st.dataframe(sem2_df, use_container_width=True)
