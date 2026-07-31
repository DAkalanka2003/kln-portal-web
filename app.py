import os
import re
import time
import base64
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="UoK Science Portal Viewer",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

PORTAL_URL = "http://www.science.kln.ac.lk:8080/(S(aeobswamkffx5xku1veqzzrw))/sfkn.aspx"

GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "E": 0.0, "F": 0.0
}

# --- LUXURY THEME CSS ---
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #f9fafb; }
    .stTextInput>div>div>input { background-color: #111827; color: #f9fafb; border: 1px solid #374151; border-radius: 8px; }
    .stSelectbox>div>div>div { background-color: #111827; color: #f9fafb; border: 1px solid #374151; border-radius: 8px; }
    div.stButton>button { background-color: #f59e0b; color: #0b0f19; font-weight: bold; border-radius: 8px; width: 100%; border: none; padding: 10px; transition: 0.3s; }
    div.stButton>button:hover { background-color: #fbbf24; color: #0b0f19; box-shadow: 0 0 15px rgba(245, 158, 11, 0.4); }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "sys_user" not in st.session_state:
    st.session_state.sys_user = ""
if "portal_data" not in st.session_state:
    st.session_state.portal_data = None

# --- SYSTEM AUTHENTICATION GUARD ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; color: #f59e0b; margin-top: 50px;'>🛡️ System Authorization</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9ca3af;'>Restricted Access Area • Enter System Credentials</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("auth_form"):
            sys_user = st.text_input("System Username", value="admin")
            sys_pass = st.text_input("System Password", type="password")
            submit_auth = st.form_submit_button("UNLOCK SYSTEM")
            
            if submit_auth:
                if sys_user == "admin" and sys_pass == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.sys_user = sys_user
                    st.rerun()
                else:
                    st.error("Invalid System Username or Password!")
    st.stop()

# --- HELPER FUNCTIONS FOR SCRAPING ---
def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")
    
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
    elif os.path.exists("/usr/bin/chromium-browser"):
        options.binary_location = "/usr/bin/chromium-browser"

    # Codespaces Linux සර්වර් එකේ පවතින සැබෑ ක්‍රෝම් බයිනරි සහ ඩ්‍රයිවර් භාවිතය
    service_paths = ["/usr/bin/chromedriver", "/usr/local/bin/chromedriver"]
    service = None
    for path in service_paths:
        if os.path.exists(path):
            service = Service(path)
            break
            
    if service:
        return webdriver.Chrome(service=service, options=options)
    else:
        return webdriver.Chrome(options=options)

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

    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            if not any(cols):
                continue
            if len(cols) >= 2:
                code, title, grade = "", "", ""
                for col in cols:
                    col_clean = col.strip()
                    if grade_regex.match(col_clean):
                        grade = col_clean
                    elif re.search(r'[A-Za-z]{2,5}\s*\d{4,5}', col_clean):
                        code = col_clean
                    elif len(col_clean) > 3 and not title and col_clean.lower() not in ["course code", "course title", "grade", "marks", "subject"]:
                        title = col_clean

                if not code and len(cols) >= 3:
                    code, title = cols[0], cols[1]
                    possible_grade = cols[-1].strip()
                    if len(possible_grade) <= 4:
                        grade = possible_grade

                clean_code = code.strip().upper() if code else ""
                if clean_code and clean_code in seen_codes:
                    continue

                if code or grade:
                    if clean_code:
                        seen_codes.add(clean_code)
                    prefix_match = re.match(r'([A-Za-z]+)', code)
                    prefix = prefix_match.group(1).upper() if prefix_match else "OTHER"
                    semester = 1
                    credits = 2
                    digits_match = re.search(r'\d+', code)
                    if digits_match:
                        digits = digits_match.group(0)
                        if len(digits) >= 2 and digits[1] == '2':
                            semester = 2
                        if len(digits) >= 4:
                            try:
                                credits = int(digits[-1])
                            except:
                                credits = 2

                    results_data.append({
                        'code': code if code else "N/A",
                        'title': title if title else "Course Module",
                        'grade': grade if grade else "Pending / -",
                        'prefix': prefix,
                        'semester': semester,
                        'credits': credits
                    })
    return results_data

# --- MAIN APP INTERFACE ---
st.markdown("<h1 style='text-align: center; color: #f59e0b;'>🎓 University of Kelaniya</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>Faculty of Science — Exam Portal Web Viewer</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 System: `{st.session_state.sys_user}`")
    if st.button("🔒 Logout System"):
        st.session_state.logged_in = False
        st.session_state.portal_data = None
        st.rerun()
    st.divider()
    st.markdown("### 📌 Instructions")
    st.info("Enter your university Student Number and select the required Year or Exam Timetable option, then click Fetch.")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    with st.form("fetch_form"):
        student_no = st.text_input("Student Number / Username *", placeholder="PS/2022/130")
        password = st.text_input("Password (If applicable)", type="password")
        selected_year = st.selectbox(
            "Select Academic Year / Option *",
            ["1st Year", "2nd Year", "3rd Year", "4th Year", "📅 Exam Admission / Timetable"]
        )
        submit_btn = st.form_submit_button("🚀 START AUTO LOGIN & FETCH")

        if submit_btn:
            if not student_no:
                st.warning("Please enter your Student Number!")
            else:
                with st.spinner("Connecting to UoK Science Faculty Portal... Please wait."):
                    driver = None
                    try:
                        driver = init_driver()
                        driver.get(PORTAL_URL)
                        time.sleep(1)

                        inputs = driver.find_elements(By.TAG_NAME, "input")
                        student_input, password_input, login_button = None, None, None

                        for inp in inputs:
                            inp_type = (inp.get_attribute("type") or "").lower()
                            inp_name = (inp.get_attribute("name") or "").lower()
                            inp_id = (inp.get_attribute("id") or "").lower()
                            if inp_type == "password" or "pass" in inp_name or "pass" in inp_id:
                                password_input = inp
                            elif inp_type in ["text", ""] or "txt" in inp_id or "user" in inp_name or "student" in inp_name:
                                if not student_input:
                                    student_input = inp

                        for inp in inputs:
                            if (inp.get_attribute("type") or "").lower() in ["submit", "button"] or "btn" in (inp.get_attribute("id") or "").lower():
                                login_button = inp
                                break

                        if student_input and login_button:
                            student_input.clear()
                            student_input.send_keys(student_no)
                            if password_input and password:
                                password_input.clear()
                                password_input.send_keys(password)
                            login_button.click()
                            time.sleep(2.5)

                            student_name = parse_student_name(driver.page_source)
                            
                            if "Admission" in selected_year or "Timetable" in selected_year:
                                st.session_state.portal_data = {
                                    "type": "timetable",
                                    "student_no": student_no,
                                    "student_name": student_name,
                                    "html": driver.page_source
                                }
                            else:
                                year_num = selected_year[0]
                                select_elements = driver.find_elements(By.TAG_NAME, "select")
                                for sel in select_elements:
                                    select = Select(sel)
                                    for option in select.options:
                                        if year_num in option.text or selected_year.lower() in option.text.lower():
                                            select.select_by_visible_text(option.text)
                                            time.sleep(1.5)
                                            break

                                results = parse_results_page(driver.page_source)
                                st.session_state.portal_data = {
                                    "type": "results",
                                    "student_no": student_no,
                                    "student_name": student_name,
                                    "year": selected_year,
                                    "results": results
                                }
                            driver.quit()
                            st.success("Data fetched successfully!")
                            st.rerun()
                        else:
                            if driver:
                                driver.quit()
                            st.error("Portal login inputs could not be identified automatically.")
                    except Exception as e:
                        if driver:
                            try:
                                driver.quit()
                            except:
                                pass
                        st.error(f"Connection Error: {e}")

# --- DISPLAY RESULTS OR TIMETABLE IF AVAILABLE ---
if st.session_state.portal_data:
    data = st.session_state.portal_data
    st.divider()
    
    if data["type"] == "results":
        st.subheader(f"📊 Academic Dashboard — {data['student_no']} ({data['year']})")
        st.markdown(f"**Student Name:** {data['student_name']}")
        
        results = data["results"]
        if results:
            import pandas as pd
            df = pd.DataFrame(results)
            st.dataframe(df[["code", "title", "grade", "credits", "semester"]], use_container_width=True)
            
            # GPA Calculation
            total_pts, total_creds = 0.0, 0
            for r in results:
                g = r['grade'].upper()
                c = r['credits']
                if g in GRADE_POINTS and c > 0:
                    total_pts += GRADE_POINTS[g] * c
                    total_creds += c
            if total_creds > 0:
                gpa = total_pts / total_creds
                st.metric(label="Calculated GPA", value=f"{gpa:.2f}")
        else:
            st.warning("No result modules found for this selection.")

    elif data["type"] == "timetable":
        st.subheader(f"📅 Exam Admission / Timetable — {data['student_no']}")
        st.markdown(f"**Student Name:** {data['student_name']}")
        st.info("Successfully accessed portal timetable page.")
        
    if st.button("🔄 Clear & Search Another"):
        st.session_state.portal_data = None
        st.rerun()
