import os
import re
import time
import json
import base64
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

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

# ---------------------------------------------------------------------------
# STUDENT DATABASE (Password සෙට් කර ඇති අය මෙතැනට ඇතුළත් කරන්න)
# ---------------------------------------------------------------------------
STUDENT_DATABASE = {
    "PS/2020/001": "pass123",
    "SE/2020/002": "mysecurepass",
    "PS/2020/003": "student2026"
}

# ---------------------------------------------------------------------------
# LUXURY DEEP DARK GOLD & SAPPHIRE THEME (PREMIUM PALETTE)
# ---------------------------------------------------------------------------
THEME = {
    "bg_primary":        "#0b0f19",  # Ultra Deep Obsidian Blue
    "bg_secondary":      "#111827",  # Dark Slate Container
    "bg_panel":          "#1f293d",  # Card / Panel Background
    "bg_panel_alt":      "#2d3748",  # Secondary Table Header Background
    "accent_mint":       "#f59e0b",  # Radiant Warm Amber / Premium Gold Accent
    "accent_mint_hover": "#fbbf24",  # Gold Hover
    "accent_cyan":       "#38bdf8",  # Sapphire Ice Blue
    "accent_blue":       "#6366f1",  # Deep Indigo Accent
    "accent_emerald":    "#10b981",  # Emerald Green for High Performance
    "text_primary":      "#f9fafb",  # Crisp Off-White
    "text_secondary":    "#9ca3af",  # Muted Silver Grey
    "text_muted":        "#6b7280",  # Darker Muted Text
    "success":           "#10b981",
    "warning":           "#f59e0b",
    "error":             "#ef4444",
    "border":            "#374151",  # Subtle Border Divider
}

FONT_FAMILY = "Segoe UI"

ALLOWED_USERS = {
    "admin": "admin123",
}


def add_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    """Utility function to add dynamic UI hover states."""
    def on_enter(e):
        widget.config(bg=hover_bg)
        if hover_fg:
            widget.config(fg=hover_fg)

    def on_leave(e):
        widget.config(bg=normal_bg)
        if normal_fg:
            widget.config(fg=normal_fg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


class SystemAuthGuard(tk.Tk):
    """Security Gate: First login screen to restrict app usage to selected users."""
    def __init__(self):
        super().__init__()
        self.title("Access Gatekeeper — UOK Portal Tool")
        self.geometry("440x540")
        self.resizable(False, False)
        self.configure(bg=THEME["bg_primary"])

        # Top Premium Accent Line
        tk.Frame(self, bg=THEME["accent_mint"], height=4).pack(fill="x", side="top")

        # Header Title
        header = tk.Frame(self, bg=THEME["bg_secondary"])
        header.pack(fill="x")

        tk.Label(
            header, text="🛡️", font=(FONT_FAMILY, 28),
            bg=THEME["bg_secondary"], fg=THEME["accent_mint"]
        ).pack(pady=(18, 2))

        tk.Label(
            header, text="SYSTEM AUTHORIZATION",
            font=(FONT_FAMILY, 14, "bold"), fg=THEME["accent_mint"], bg=THEME["bg_secondary"]
        ).pack()

        tk.Label(
            header, text="Restricted Access Area • Enter System Credentials",
            font=(FONT_FAMILY, 8), fg=THEME["text_secondary"], bg=THEME["bg_secondary"]
        ).pack(pady=(2, 16))

        tk.Frame(self, bg=THEME["border"], height=1).pack(fill="x")

        # Login Form Panel
        card = tk.Frame(self, bg=THEME["bg_panel"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(padx=32, pady=25, fill="both", expand=True)

        input_frame = tk.Frame(card, bg=THEME["bg_panel"])
        input_frame.pack(pady=20, padx=20, fill="x")

        tk.Label(
            input_frame, text="System Username",
            font=(FONT_FAMILY, 9, "bold"), fg=THEME["text_primary"], bg=THEME["bg_panel"], anchor="w"
        ).pack(fill="x", pady=(0, 4))

        self.txt_sys_user = tk.Entry(
            input_frame, font=("Consolas", 10), bg=THEME["bg_secondary"], fg=THEME["text_primary"],
            insertbackground=THEME["accent_mint"], bd=0, relief="flat",
            highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["accent_mint"]
        )
        self.txt_sys_user.pack(fill="x", ipady=6, pady=(0, 14))

        tk.Label(
            input_frame, text="System Password",
            font=(FONT_FAMILY, 9, "bold"), fg=THEME["text_primary"], bg=THEME["bg_panel"], anchor="w"
        ).pack(fill="x", pady=(0, 4))

        self.txt_sys_pass = tk.Entry(
            input_frame, font=("Consolas", 10), bg=THEME["bg_secondary"], fg=THEME["text_primary"],
            insertbackground=THEME["accent_mint"], bd=0, relief="flat", show="*",
            highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["accent_mint"]
        )
        self.txt_sys_pass.pack(fill="x", ipady=6, pady=(0, 20))

        btn_login = tk.Button(
            input_frame, text="UNLOCK SYSTEM",
            font=(FONT_FAMILY, 10, "bold"), fg="#0b0f19", bg=THEME["accent_mint"],
            activebackground=THEME["accent_mint_hover"], activeforeground="#0b0f19",
            bd=0, cursor="hand2", command=self.verify_login
        )
        btn_login.pack(fill="x", ipady=8)
        add_hover(btn_login, THEME["accent_mint"], THEME["accent_mint_hover"])

        self.bind('<Return>', lambda event: self.verify_login())

    def verify_login(self):
        user = self.txt_sys_user.get().strip()
        pwd = self.txt_sys_pass.get().strip()

        if user in ALLOWED_USERS and ALLOWED_USERS[user] == pwd:
            self.destroy()
            main_app = tk.Tk()
            AutoLoginApp(main_app, authenticated_user=user)
            main_app.mainloop()
        else:
            messagebox.showerror("Access Denied", "Invalid System Username or Password!\nUnauthorized access is blocked.")


class ResultsDashboard(tk.Toplevel):
    def __init__(self, parent, student_no, student_name, selected_year, parsed_results, driver):
        super().__init__(parent)
        self.title(f"Academic Dashboard — {student_no} ({selected_year})")
        self.geometry("1020x760")
        self.minsize(900, 660)
        self.configure(bg=THEME["bg_primary"])

        self.student_no = student_no
        self.student_name = student_name if student_name else "Student"
        self.selected_year = selected_year
        self.all_results = parsed_results
        self.driver = driver

        tk.Frame(self, bg=THEME["accent_mint"], height=4).pack(fill="x", side="top")

        # Top Header Banner
        header_frame = tk.Frame(self, bg=THEME["bg_secondary"])
        header_frame.pack(fill="x")

        crest = tk.Label(
            header_frame, text="🎓", font=(FONT_FAMILY, 28),
            bg=THEME["bg_secondary"], fg=THEME["accent_mint"]
        )
        crest.pack(side="left", padx=(20, 10), pady=14)

        title_box = tk.Frame(header_frame, bg=THEME["bg_secondary"])
        title_box.pack(side="left", pady=12)

        tk.Label(
            title_box, text="University of Kelaniya — Faculty of Science",
            font=(FONT_FAMILY, 15, "bold"), fg=THEME["accent_mint"], bg=THEME["bg_secondary"]
        ).pack(anchor="w")

        user_info_str = f"👤 Student Name: {self.student_name}   |   🆔 Student No: {self.student_no}   |   📅 {self.selected_year}"
        tk.Label(
            title_box, text=user_info_str,
            font=(FONT_FAMILY, 9, "bold"), fg=THEME["accent_cyan"], bg=THEME["bg_secondary"]
        ).pack(anchor="w", pady=(2, 0))

        filter_frame = tk.Frame(self, bg=THEME["bg_primary"])
        filter_frame.pack(fill="x", padx=24, pady=(16, 8))

        lbl_filter = tk.Label(
            filter_frame, text="Filter Subject:",
            font=(FONT_FAMILY, 10, "bold"), fg=THEME["text_primary"], bg=THEME["bg_primary"]
        )
        lbl_filter.pack(side="left", padx=(0, 8))

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Kln.TCombobox",
            fieldbackground=THEME["bg_panel"],
            background=THEME["bg_panel"],
            foreground=THEME["text_primary"],
            arrowcolor=THEME["accent_mint"],
            bordercolor=THEME["border"],
            lightcolor=THEME["bg_panel"],
            darkcolor=THEME["bg_panel"],
            padding=4,
        )

        subject_prefixes = sorted(list({r['prefix'] for r in self.all_results if r['prefix'] and r['prefix'] != "OTHER"}))
        subject_options = ["All Subjects"] + subject_prefixes

        self.cmb_subject = ttk.Combobox(
            filter_frame, values=subject_options, state="readonly",
            font=(FONT_FAMILY, 9), width=18, style="Kln.TCombobox"
        )
        self.cmb_subject.current(0)
        self.cmb_subject.pack(side="left")
        self.cmb_subject.bind("<<ComboboxSelected>>", self.filter_data)

        btn_pdf = tk.Button(
            filter_frame,
            text="📄  Export Official Result Sheet (PDF)",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#0b0f19",
            bg=THEME["accent_mint"],
            activebackground=THEME["accent_mint_hover"],
            activeforeground="#0b0f19",
            bd=0, cursor="hand2", padx=14, pady=6,
            command=self.download_official_pdf
        )
        btn_pdf.pack(side="right")
        add_hover(btn_pdf, THEME["accent_mint"], THEME["accent_mint_hover"])

        style.configure("TNotebook", background=THEME["bg_primary"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=THEME["bg_panel"],
            foreground=THEME["text_secondary"],
            padding=[16, 8],
            font=(FONT_FAMILY, 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["accent_mint"])],
            foreground=[("selected", "#0b0f19")],
        )

        style.configure(
            "Treeview",
            background=THEME["bg_panel"],
            foreground=THEME["text_primary"],
            fieldbackground=THEME["bg_panel"],
            rowheight=32,
            font=(FONT_FAMILY, 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=THEME["bg_panel_alt"],
            foreground=THEME["accent_mint"],
            font=(FONT_FAMILY, 10, "bold"),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[('selected', THEME["accent_blue"])],
            foreground=[('selected', "#ffffff")],
        )
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(4, 8))

        self.tab_overview = tk.Frame(self.notebook, bg=THEME["bg_primary"])
        self.notebook.add(self.tab_overview, text="  📊 Visual Analytics  ")

        self.tab_all = tk.Frame(self.notebook, bg=THEME["bg_primary"])
        self.notebook.add(self.tab_all, text="  All Semesters  ")

        self.tab_sem1 = tk.Frame(self.notebook, bg=THEME["bg_primary"])
        self.notebook.add(self.tab_sem1, text="  1st Semester  ")

        self.tab_sem2 = tk.Frame(self.notebook, bg=THEME["bg_primary"])
        self.notebook.add(self.tab_sem2, text="  2nd Semester  ")

        self.overview_container = tk.Frame(self.tab_overview, bg=THEME["bg_primary"])
        self.overview_container.pack(fill="both", expand=True)

        self.tree_all = self.create_treeview(self.tab_all)
        self.tree_sem1 = self.create_treeview(self.tab_sem1)
        self.tree_sem2 = self.create_treeview(self.tab_sem2)

        for tree in (self.tree_all, self.tree_sem1, self.tree_sem2):
            tree.tag_configure("grade_a", foreground=THEME["accent_emerald"])
            tree.tag_configure("grade_b", foreground=THEME["accent_cyan"])
            tree.tag_configure("grade_c", foreground=THEME["warning"])
            tree.tag_configure("grade_d", foreground=THEME["error"])
            tree.tag_configure("grade_pending", foreground=THEME["text_muted"])

        gpa_frame = tk.Frame(self, bg=THEME["bg_panel"], highlightbackground=THEME["accent_mint"], highlightthickness=1)
        gpa_frame.pack(fill="x", padx=24, pady=(4, 20), ipady=12)

        self.lbl_overall_gpa = tk.Label(
            gpa_frame, text="Overall Year GPA: --",
            font=(FONT_FAMILY, 12, "bold"), fg=THEME["accent_mint"], bg=THEME["bg_panel"]
        )
        self.lbl_overall_gpa.pack(side="left", padx=24)

        self.lbl_subject_gpa = tk.Label(
            gpa_frame, text="Subject GPA: --",
            font=(FONT_FAMILY, 12, "bold"), fg=THEME["text_primary"], bg=THEME["bg_panel"]
        )
        self.lbl_subject_gpa.pack(side="right", padx=24)

        self.current_filtered_data = self.all_results
        self.populate_trees(self.all_results)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def grade_tag(self, grade):
        g = grade.strip().upper()
        if g not in GRADE_POINTS:
            return "grade_pending"
        if g.startswith("A"):
            return "grade_a"
        if g.startswith("B"):
            return "grade_b"
        if g.startswith("C"):
            return "grade_c"
        return "grade_d"

    def refresh_overview(self, data_list):
        for widget in self.overview_container.winfo_children():
            widget.destroy()

        total = len(data_list)
        grade_counts = {}
        grade_modules = {}
        completed = 0
        for item in data_list:
            g = item['grade'].strip().upper()
            if g in GRADE_POINTS:
                completed += 1
                grade_counts[g] = grade_counts.get(g, 0) + 1
                if g not in grade_modules:
                    grade_modules[g] = []
                grade_modules[g].append(item['code'])
        pending = total - completed
        overall_gpa, _ = self.calculate_gpa(data_list)

        stats_frame = tk.Frame(self.overview_container, bg=THEME["bg_primary"])
        stats_frame.pack(fill="x", padx=24, pady=(16, 12))

        def stat_card(parent, label, value, color):
            card = tk.Frame(parent, bg=THEME["bg_panel"], highlightbackground=color, highlightthickness=1)
            card.pack(side="left", expand=True, fill="both", padx=6, ipady=10)
            tk.Label(card, text=str(value), font=(FONT_FAMILY, 18, "bold"), fg=color, bg=THEME["bg_panel"]).pack(pady=(6, 0))
            tk.Label(card, text=label, font=(FONT_FAMILY, 8, "bold"), fg=THEME["text_secondary"], bg=THEME["bg_panel"]).pack(pady=(0, 6))

        stat_card(stats_frame, "TOTAL MODULES", total, THEME["accent_blue"])
        stat_card(stats_frame, "COMPLETED", completed, THEME["accent_emerald"])
        stat_card(stats_frame, "PENDING", pending, THEME["warning"])
        stat_card(stats_frame, "FILTERED GPA", f"{overall_gpa:.2f}", THEME["accent_mint"])

        chart_section = tk.Frame(self.overview_container, bg=THEME["bg_primary"])
        chart_section.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        chart_card = tk.Frame(chart_section, bg=THEME["bg_panel"], highlightbackground=THEME["border"], highlightthickness=1)
        chart_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            chart_card, text="📊 Grade Distribution & Visual Performance Metrics",
            font=(FONT_FAMILY, 11, "bold"), fg=THEME["accent_mint"], bg=THEME["bg_panel"]
        ).pack(anchor="w", padx=16, pady=(12, 4))

        chart_canvas = tk.Canvas(chart_card, bg=THEME["bg_panel"], highlightthickness=0)
        chart_canvas.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        info_card = tk.Frame(chart_section, bg=THEME["bg_panel"], highlightbackground=THEME["border"], highlightthickness=1, width=320)
        info_card.pack(side="right", fill="both", padx=(10, 0))

        tk.Label(
            info_card, text="📈 Grade Breakdown & Subjects",
            font=(FONT_FAMILY, 11, "bold"), fg=THEME["accent_cyan"], bg=THEME["bg_panel"]
        ).pack(anchor="w", padx=16, pady=(12, 8))

        canvas_info = tk.Canvas(info_card, bg=THEME["bg_panel"], highlightthickness=0)
        scrollbar_info = ttk.Scrollbar(info_card, orient="vertical", command=canvas_info.yview)
        scrollable_frame = tk.Frame(canvas_info, bg=THEME["bg_panel"])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_info.configure(scrollregion=canvas_info.bbox("all"))
        )
        canvas_info.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_info.configure(yscrollcommand=scrollbar_info.set)

        canvas_info.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        scrollbar_info.pack(side="right", fill="y", pady=(0, 12))

        grade_order = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E", "F"]

        for g in grade_order:
            cnt = grade_counts.get(g, 0)
            if cnt > 0:
                card_g = tk.Frame(scrollable_frame, bg=THEME["bg_secondary"], highlightbackground=THEME["border"], highlightthickness=1)
                card_g.pack(fill="x", expand=True, pady=4, padx=4)

                header_row = tk.Frame(card_g, bg=THEME["bg_secondary"])
                header_row.pack(fill="x", padx=8, pady=(4, 2))

                col_hex = THEME["accent_emerald"] if g.startswith("A") else (THEME["accent_cyan"] if g.startswith("B") else (THEME["warning"] if g.startswith("C") else THEME["error"]))
                tk.Label(header_row, text=f"Grade {g}", font=(FONT_FAMILY, 9, "bold"), fg=col_hex, bg=THEME["bg_secondary"]).pack(side="left")
                tk.Label(header_row, text=f"{cnt} Module(s)", font=(FONT_FAMILY, 8, "bold"), fg=THEME["text_primary"], bg=THEME["bg_secondary"]).pack(side="right")

                subjects_str = ", ".join(grade_modules.get(g, []))
                tk.Label(
                    card_g, text=subjects_str, font=(FONT_FAMILY, 8),
                    fg=THEME["text_secondary"], bg=THEME["bg_secondary"],
                    wraplength=220, justify="left"
                ).pack(anchor="w", padx=8, pady=(0, 6))

        def grade_color(g):
            if g.startswith("A"):
                return THEME["accent_emerald"]
            if g.startswith("B"):
                return THEME["accent_cyan"]
            if g.startswith("C"):
                return THEME["warning"]
            return THEME["error"]

        def draw_chart(event=None):
            chart_canvas.delete("all")
            w = chart_canvas.winfo_width()
            h = chart_canvas.winfo_height()
            if w < 40 or h < 40:
                return

            present_grades = [g for g in grade_order if grade_counts.get(g, 0) > 0]
            if not present_grades:
                chart_canvas.create_text(
                    w / 2, h / 2, text="No completed grades available for visual chart rendering.",
                    fill=THEME["text_muted"], font=(FONT_FAMILY, 10)
                )
                return

            max_count = max(grade_counts.get(g, 0) for g in present_grades) or 1
            bottom_margin, top_margin = 36, 30
            bar_area_h = h - bottom_margin - top_margin
            n = len(present_grades)
            gap = 20
            bar_w = max(24, (w - gap * (n + 1)) / n)

            for i in range(1, 4):
                grid_y = h - bottom_margin - (bar_area_h * (i / 3))
                chart_canvas.create_line(10, grid_y, w - 10, grid_y, fill=THEME["border"], dash=(2, 4))

            x = gap
            for g in present_grades:
                count = grade_counts.get(g, 0)
                bar_h = (count / max_count) * bar_area_h
                y1 = h - bottom_margin
                y0 = y1 - bar_h
                color = grade_color(g)
                
                chart_canvas.create_rectangle(x, y0, x + bar_w, y1, fill=color, outline=THEME["border"])
                chart_canvas.create_text(x + bar_w / 2, y0 - 12, text=str(count),
                                          fill=THEME["text_primary"], font=(FONT_FAMILY, 9, "bold"))
                chart_canvas.create_text(x + bar_w / 2, h - bottom_margin + 16, text=g,
                                          fill=THEME["accent_mint"], font=(FONT_FAMILY, 9, "bold"))
                x += bar_w + gap

        chart_canvas.bind("<Configure>", draw_chart)
        self.after(120, draw_chart)

    def create_treeview(self, parent_frame):
        frame = tk.Frame(parent_frame, bg=THEME["bg_primary"])
        frame.pack(fill="both", expand=True, pady=6)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        columns = ("code", "title", "grade", "credits")
        tree = ttk.Treeview(frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)

        tree.heading("code", text="Course Code")
        tree.heading("title", text="Course Title / Details")
        tree.heading("grade", text="Grade")
        tree.heading("credits", text="Credits")

        tree.column("code", width=140, anchor="center")
        tree.column("title", width=470, anchor="w")
        tree.column("grade", width=100, anchor="center")
        tree.column("credits", width=90, anchor="center")

        scrollbar.config(command=tree.yview)
        tree.pack(fill="both", expand=True)

        return tree

    def calculate_gpa(self, data_list):
        total_points = 0.0
        total_credits = 0

        for item in data_list:
            grade = item['grade'].upper()
            credits = item['credits']

            if grade in GRADE_POINTS and credits > 0:
                total_points += GRADE_POINTS[grade] * credits
                total_credits += credits

        if total_credits > 0:
            return round(total_points / total_credits, 2), total_credits
        return 0.0, 0

    def populate_trees(self, data_list):
        for tree in (self.tree_all, self.tree_sem1, self.tree_sem2):
            for item in tree.get_children():
                tree.delete(item)

        sem1_count, sem2_count = 0, 0

        for item in data_list:
            row_vals = (item['code'], item['title'], item['grade'], item['credits'])
            tag = self.grade_tag(item['grade'])

            self.tree_all.insert("", "end", values=row_vals, tags=(tag,))

            if item['semester'] == 2:
                self.tree_sem2.insert("", "end", values=row_vals, tags=(tag,))
                sem2_count += 1
            else:
                self.tree_sem1.insert("", "end", values=row_vals, tags=(tag,))
                sem1_count += 1

        if not data_list:
            self.tree_all.insert("", "end", values=("N/A", "No modules found", "N/A", "N/A"))
        if sem1_count == 0:
            self.tree_sem1.insert("", "end", values=("N/A", "No modules found for 1st Semester", "N/A", "N/A"))
        if sem2_count == 0:
            self.tree_sem2.insert("", "end", values=("N/A", "No modules found for 2nd Semester", "N/A", "N/A"))

        overall_gpa, overall_credits = self.calculate_gpa(self.all_results)
        self.lbl_overall_gpa.config(text=f"Overall {self.selected_year} GPA: {overall_gpa:.2f} ({overall_credits} Credits)")

        selected_subject = self.cmb_subject.get()
        if selected_subject != "All Subjects":
            sub_gpa, sub_credits = self.calculate_gpa(data_list)
            self.lbl_subject_gpa.config(text=f"{selected_subject} GPA: {sub_gpa:.2f} ({sub_credits} Credits)")
        else:
            self.lbl_subject_gpa.config(text="Subject GPA: (Select a Subject)")

        self.refresh_overview(data_list)

    def filter_data(self, event=None):
        selected_prefix = self.cmb_subject.get()
        if selected_prefix == "All Subjects":
            self.current_filtered_data = self.all_results
        else:
            self.current_filtered_data = [r for r in self.all_results if r['prefix'] == selected_prefix]

        self.populate_trees(self.current_filtered_data)

    def download_official_pdf(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"Official_Portal_Results_{self.student_no}_{self.selected_year.replace(' ', '_')}.pdf"
        )
        if not file_path or not self.driver:
            return

        try:
            pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "printBackground": True,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4
            })

            with open(file_path, "wb") as f:
                f.write(base64.b64decode(pdf_data['data']))

            messagebox.showinfo("Success", f"Official Website Result Sheet PDF Saved Successfully!\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Webpage PDF: {e}")

    def on_close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.destroy()


class ExamAdmissionDashboard(tk.Toplevel):
    def __init__(self, parent, student_no, student_name, timetable_data, driver):
        super().__init__(parent)
        self.title(f"Exam Admission & Timetable — {student_no}")
        self.geometry("900x640")
        self.minsize(780, 540)
        self.configure(bg=THEME["bg_primary"])

        self.student_no = student_no
        self.student_name = student_name if student_name else "Student"
        self.timetable_data = timetable_data
        self.driver = driver

        tk.Frame(self, bg=THEME["accent_mint"], height=4).pack(fill="x", side="top")

        header_frame = tk.Frame(self, bg=THEME["bg_secondary"])
        header_frame.pack(fill="x")

        tk.Label(
            header_frame, text="📅", font=(FONT_FAMILY, 28),
            bg=THEME["bg_secondary"], fg=THEME["accent_mint"]
        ).pack(side="left", padx=(20, 10), pady=14)

        title_box = tk.Frame(header_frame, bg=THEME["bg_secondary"])
        title_box.pack(side="left", pady=12)

        tk.Label(
            title_box, text="Exam Admission / Timetable Schedule",
            font=(FONT_FAMILY, 15, "bold"), fg=THEME["accent_mint"], bg=THEME["bg_secondary"]
        ).pack(anchor="w")

        user_info_str = f"👤 Student Name: {self.student_name}   |   🆔 Student No: {self.student_no}"
        tk.Label(
            title_box, text=user_info_str,
            font=(FONT_FAMILY, 9, "bold"), fg=THEME["accent_cyan"], bg=THEME["bg_secondary"]
        ).pack(anchor="w", pady=(2, 0))

        action_frame = tk.Frame(self, bg=THEME["bg_primary"])
        action_frame.pack(fill="x", padx=24, pady=(16, 8))

        btn_pdf = tk.Button(
            action_frame,
            text="📄  Save Official Admission Sheet (PDF)",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#0b0f19",
            bg=THEME["accent_mint"],
            activebackground=THEME["accent_mint_hover"],
            activeforeground="#0b0f19",
            bd=0, cursor="hand2", padx=14, pady=6,
            command=self.download_official_pdf
        )
        btn_pdf.pack(side="right")
        add_hover(btn_pdf, THEME["accent_mint"], THEME["accent_mint_hover"])

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=THEME["bg_panel"],
            foreground=THEME["text_primary"],
            fieldbackground=THEME["bg_panel"],
            rowheight=32,
            font=(FONT_FAMILY, 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=THEME["bg_panel_alt"],
            foreground=THEME["accent_mint"],
            font=(FONT_FAMILY, 10, "bold"),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[('selected', THEME["accent_blue"])],
            foreground=[('selected', "#ffffff")],
        )

        table_frame = tk.Frame(self, bg=THEME["bg_primary"])
        table_frame.pack(fill="both", expand=True, padx=24, pady=(4, 20))

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        columns = ("date", "time", "code", "details")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        self.tree.heading("date", text="Date")
        self.tree.heading("time", text="Time")
        self.tree.heading("code", text="Module Code")
        self.tree.heading("details", text="Subject / Hall / Details")

        self.tree.column("date", width=120, anchor="center")
        self.tree.column("time", width=120, anchor="center")
        self.tree.column("code", width=140, anchor="center")
        self.tree.column("details", width=440, anchor="w")

        scrollbar.config(command=self.tree.yview)
        self.tree.pack(fill="both", expand=True)

        if self.timetable_data:
            for item in self.timetable_data:
                self.tree.insert("", "end", values=(item['date'], item['time'], item['code'], item['details']))
        else:
            self.tree.insert(
                "", "end",
                values=("N/A", "N/A", "N/A", "No timetable entries detected on this page.")
            )

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def download_official_pdf(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"Official_Exam_Admission_{self.student_no}.pdf"
        )
        if not file_path or not self.driver:
            return

        try:
            pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "printBackground": True,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4
            })

            with open(file_path, "wb") as f:
                f.write(base64.b64decode(pdf_data['data']))

            messagebox.showinfo("Success", f"Official Exam Admission PDF Saved Successfully!\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Webpage PDF: {e}")

    def on_close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.destroy()


class AutoLoginApp:
    def __init__(self, root, authenticated_user="User"):
        self.root = root
        self.authenticated_user = authenticated_user
        self.root.title("University of Kelaniya — Science Portal Auto Login & Results Viewer")
        self.root.geometry("520x720")
        self.root.resizable(False, False)
        self.root.configure(bg=THEME["bg_primary"])

        self.is_running = False
        self.active_driver = None

        tk.Frame(root, bg=THEME["accent_mint"], height=4).pack(fill="x", side="top")

        header = tk.Frame(root, bg=THEME["bg_secondary"])
        header.pack(fill="x")

        tk.Label(
            header, text="🎓", font=(FONT_FAMILY, 30),
            bg=THEME["bg_secondary"], fg=THEME["accent_mint"]
        ).pack(pady=(18, 2))

        tk.Label(
            header, text="UNIVERSITY OF KELANIYA",
            font=(FONT_FAMILY, 17, "bold"), fg=THEME["accent_mint"], bg=THEME["bg_secondary"]
        ).pack()

        tk.Label(
            header, text="Faculty of Science — Exam Portal Auto-Login Suite",
            font=(FONT_FAMILY, 9, "italic"), fg=THEME["text_secondary"], bg=THEME["bg_secondary"]
        ).pack(pady=(2, 6))

        tk.Label(
            header, text=f"🔑 Logged in System Account: {self.authenticated_user}",
            font=(FONT_FAMILY, 8, "bold"), fg=THEME["accent_cyan"], bg=THEME["bg_secondary"]
        ).pack(pady=(0, 14))

        tk.Frame(root, bg=THEME["border"], height=1).pack(fill="x")

        card = tk.Frame(root, bg=THEME["bg_panel"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(padx=32, pady=(20, 10), fill="x")

        input_frame = tk.Frame(card, bg=THEME["bg_panel"])
        input_frame.pack(pady=18, padx=24, fill="x")

        lbl_student = tk.Label(
            input_frame, text="Student Number / Username  *",
            font=(FONT_FAMILY, 9, "bold"), fg=THEME["text_primary"], bg=THEME["bg_panel"], anchor="w"
        )
        lbl_student.pack(fill="x", pady=(0, 4))

        self.txt_student = tk.Entry(
            input_frame, font=("Consolas", 11), bg=THEME["bg_secondary"], fg=THEME["text_primary"],
            insertbackground=THEME["accent_mint"], bd=0, relief="flat",
            highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["accent_mint"]
        )
        self.txt_student.pack(fill="x", ipady=7, pady=(0, 14))

        lbl_password = tk.Label(
            input_frame, text="Password  (Required if set for your account)",
            font=(FONT_FAMILY, 8, "bold"), fg=THEME["text_secondary"], bg=THEME["bg_panel"], anchor="w"
        )
        lbl_password.pack(fill="x", pady=(0, 4))

        self.txt_password = tk.Entry(
            input_frame, font=("Consolas", 11), bg=THEME["bg_secondary"], fg=THEME["text_primary"],
            insertbackground=THEME["accent_mint"], bd=0, relief="flat", show="*",
            highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["accent_mint"]
        )
        self.txt_password.pack(fill="x", ipady=7, pady=(0, 14))

        lbl_year = tk.Label(
            input_frame, text="Select Academic Year / Option  *",
            font=(FONT_FAMILY, 9, "bold"), fg=THEME["text_primary"], bg=THEME["bg_panel"], anchor="w"
        )
        lbl_year.pack(fill="x", pady=(0, 4))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Kln.TCombobox",
            fieldbackground=THEME["bg_secondary"],
            background=THEME["bg_secondary"],
            foreground=THEME["text_primary"],
            arrowcolor=THEME["accent_mint"],
            bordercolor=THEME["border"],
            lightcolor=THEME["bg_secondary"],
            darkcolor=THEME["bg_secondary"],
            padding=6,
        )
        style.map("Kln.TCombobox", fieldbackground=[("readonly", THEME["bg_secondary"])])

        self.cmb_year = ttk.Combobox(
            input_frame,
            values=["1st Year", "2nd Year", "3rd Year", "4th Year", "📅  Exam Admission / Timetable"],
            state="readonly",
            font=(FONT_FAMILY, 10),
            style="Kln.TCombobox"
        )
        self.cmb_year.current(0)
        self.cmb_year.pack(fill="x", ipady=5)
        self.cmb_year.bind("<<ComboboxSelected>>", self.on_year_change)

        self.lbl_hint = tk.Label(
            input_frame, text="Student number & year are required to fetch results.",
            font=(FONT_FAMILY, 8), fg=THEME["text_muted"], bg=THEME["bg_panel"], anchor="w", wraplength=380, justify="left"
        )
        self.lbl_hint.pack(fill="x", pady=(8, 0))

        self.lbl_status = tk.Label(
            root, text="Status: System Authorized & Ready",
            font=(FONT_FAMILY, 9, "italic"), fg=THEME["text_secondary"], bg=THEME["bg_primary"]
        )
        self.lbl_status.pack(pady=(10, 4))

        btn_container = tk.Frame(root, bg=THEME["bg_primary"])
        btn_container.pack(pady=4)

        self.btn_start = tk.Button(
            btn_container,
            text="🔐  START AUTO LOGIN & FETCH",
            font=(FONT_FAMILY, 11, "bold"),
            fg="#0b0f19",
            bg=THEME["accent_mint"],
            activebackground=THEME["accent_mint_hover"],
            activeforeground="#0b0f19",
            bd=0, cursor="hand2",
            command=self.start_thread
        )
        self.btn_start.pack(pady=2, ipadx=24, ipady=8)
        add_hover(self.btn_start, THEME["accent_mint"], THEME["accent_mint_hover"])

        self.btn_cancel = tk.Button(
            btn_container,
            text="⛔  CANCEL / STOP FETCHING",
            font=(FONT_FAMILY, 10, "bold"),
            fg="#ffffff",
            bg=THEME["error"],
            activebackground="#dc2626",
            activeforeground="#ffffff",
            bd=0, cursor="hand2",
            command=self.stop_process
        )
        add_hover(self.btn_cancel, THEME["error"], "#dc2626")

        footer = tk.Label(
            root, text="© University of Kelaniya  •  Faculty of Science",
            font=(FONT_FAMILY, 8), fg=THEME["text_muted"], bg=THEME["bg_primary"]
        )
        footer.pack(side="bottom", pady=12)

    def on_year_change(self, event=None):
        selected = self.cmb_year.get()
        if "Admission" in selected or "Timetable" in selected:
            self.btn_start.config(text="📅  FETCH EXAM ADMISSION / TIMETABLE")
            self.lbl_hint.config(
                text="Logs into the portal and opens the Exam Admission / Timetable page "
                     "right inside this app. Student number is required."
            )
        else:
            self.btn_start.config(text="🔐  START AUTO LOGIN & FETCH")
            self.lbl_hint.config(text="Student number & year are required to fetch results.")

    def update_status(self, text, color=None):
        if color is None:
            color = THEME["text_secondary"]
        self.lbl_status.config(text=text, fg=color)

    def start_thread(self):
        student_no = self.txt_student.get().strip()
        password = self.txt_password.get().strip()
        selected_year = self.cmb_year.get().strip()

        if not selected_year:
            messagebox.showwarning("Input Error", "Please select an option from the list!")
            return

        if not student_no:
            messagebox.showwarning("Input Error", "Please enter your Student Number!")
            return

        # -------------------------------------------------------------------
        # PASSWORD VALIDATION LOGIC
        # -------------------------------------------------------------------
        # 1. Password සෙට් කර ඇති student කෙනෙක්දැයි පරීක්ෂා කිරීම
        if student_no in STUDENT_DATABASE:
            correct_password = STUDENT_DATABASE[student_no]
            # Password එකක් දී නැත්නම් Error එකක් පෙන්වීම
            if not password:
                messagebox.showwarning("Password Required", "This account requires a password!\nPlease enter your password.")
                return
            # Password එක වැරදි නම් Access Denied කිරීම
            elif password != correct_password:
                messagebox.showerror("Access Denied", "Incorrect Password for this Student Number!")
                return

        if self.is_running:
            return

        self.is_running = True
        self.btn_start.config(state="disabled", bg=THEME["text_muted"])
        
        self.btn_cancel.pack(pady=6, ipadx=20, ipady=6)

        if "Admission" in selected_year or "Timetable" in selected_year:
            self.update_status("Status: Launching Background Fetcher for Timetable...", THEME["warning"])
            threading.Thread(target=self.run_selenium_timetable, args=(student_no, password), daemon=True).start()
            return

        self.update_status("Status: Launching Background Fetcher...", THEME["warning"])
        threading.Thread(target=self.run_selenium, args=(student_no, password, selected_year), daemon=True).start()

    def stop_process(self):
        if not self.is_running:
            return

        self.is_running = False
        self.update_status("Status: ⛔ Cancelling Process...", THEME["error"])

        if self.active_driver:
            try:
                self.active_driver.quit()
            except Exception:
                pass
            self.active_driver = None

        self.reset_ui_state()
        self.update_status("Status: Process Cancelled by User", THEME["error"])

    def reset_ui_state(self):
        self.btn_cancel.pack_forget()
        self.btn_start.config(state="normal", bg=THEME["accent_mint"])

    def parse_student_name(self, html_source):
        """Extracts the exact 'Student Name with Initial' from portal HTML."""
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

        text_nodes = soup.find_all(text=re.compile(r'Student Name|Name with Initial', re.IGNORECASE))
        for node in text_nodes:
            parent = node.parent
            if parent:
                row_or_container = parent.find_parent(['tr', 'div', 'td'])
                if row_or_container:
                    full_text = row_or_container.get_text(strip=True)
                    if ":" in full_text:
                        parts = full_text.split(":")
                        if len(parts) > 1 and parts[1].strip():
                            clean_name = parts[1].strip().split("Student No")[0].split("Academic")[0].strip()
                            if clean_name:
                                return clean_name

        return ""

    def parse_results_page(self, html_source):
        soup = BeautifulSoup(html_source, 'html.parser')
        results_data = []
        seen_codes = set()

        grade_regex = re.compile(r'^(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D|E|F|MC|I|P|PASS|FAIL)$', re.IGNORECASE)

        header_code_words = {"course code", "code", "module code", "subject code"}
        header_title_words = {"course title", "course title / details", "course name",
                               "title", "subject", "module", "module title", "course"}

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

                    if code.strip().lower() in header_code_words or title.strip().lower() in header_title_words:
                        continue

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

    def navigate_to_year(self, driver, year_str):
        if not self.is_running:
            return
        year_num = year_str[0]
        time.sleep(1.5)

        select_elements = driver.find_elements(By.TAG_NAME, "select")
        for sel in select_elements:
            if not self.is_running:
                return
            select = Select(sel)
            for option in select.options:
                if year_num in option.text or year_str.lower() in option.text.lower():
                    select.select_by_visible_text(option.text)
                    time.sleep(1.5)
                    return

        clickables = driver.find_elements(By.XPATH, "//a | //input[@type='submit' or @type='button'] | //button")
        for elem in clickables:
            if not self.is_running:
                return
            text = (elem.text or elem.get_attribute("value") or "").lower()
            if f"{year_num}st" in text or f"{year_num}nd" in text or f"{year_num}rd" in text or f"{year_num}th" in text or f"year {year_num}" in text or f"level {year_num}" in text:
                elem.click()
                time.sleep(2)
                return

    def try_login(self, driver, student_number, password):
        if not self.is_running:
            return False

        driver.get(PORTAL_URL)
        time.sleep(1)

        student_input = None
        password_input = None
        login_button = None

        inputs = driver.find_elements(By.TAG_NAME, "input")
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
            inp_type = (inp.get_attribute("type") or "").lower()
            if inp_type in ["submit", "button"] or "btn" in (inp.get_attribute("id") or "").lower():
                login_button = inp
                break

        if student_input and login_button:
            student_input.clear()
            student_input.send_keys(student_number)

            if password_input:
                password_input.clear()
                if password:
                    password_input.send_keys(password)

            login_button.click()
            time.sleep(2)

            current_url = driver.current_url
            page_source = driver.page_source.lower()

            if "sfkn.aspx" not in current_url or "result" in page_source or "welcome" in page_source or "logout" in page_source:
                return True

        return False

    def navigate_to_timetable(self, driver):
        if not self.is_running:
            return False
        time.sleep(1.5)
        clickables = driver.find_elements(By.XPATH, "//a | //input[@type='submit' or @type='button'] | //button")
        for elem in clickables:
            if not self.is_running:
                return False
            text = (elem.text or elem.get_attribute("value") or "").strip().lower()
            if not text:
                continue
            for keyword in TIMETABLE_LINK_KEYWORDS:
                if keyword in text:
                    try:
                        elem.click()
                        time.sleep(2)
                        return True
                    except Exception:
                        continue
        return False

    def parse_timetable_page(self, html_source):
        soup = BeautifulSoup(html_source, 'html.parser')
        timetable_data = []
        header_words = {"date", "day", "time", "module", "code", "subject", "hall", "venue", "course", "details"}

        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                cols = [c for c in cols if c]
                if len(cols) < 2:
                    continue

                if all(c.lower() in header_words for c in cols):
                    continue

                date_val, time_val, code_val, rest_vals = "", "", "", []
                for col in cols:
                    if not date_val and DATE_REGEX.search(col):
                        date_val = col
                    elif not time_val and TIME_REGEX.search(col):
                        time_val = col
                    elif not code_val and re.search(r'[A-Za-z]{2,5}\s*\d{3,5}', col):
                        code_val = col
                    else:
                        rest_vals.append(col)

                if date_val or time_val or code_val or rest_vals:
                    timetable_data.append({
                        'date': date_val if date_val else "-",
                        'time': time_val if time_val else "-",
                        'code': code_val if code_val else "-",
                        'details': " | ".join(rest_vals) if rest_vals else "-"
                    })

        return timetable_data

    def run_selenium_timetable(self, student_number, password):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1920,1080")

            self.active_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver = self.active_driver

            attempt = 1
            while self.is_running:
                self.update_status(f"Status: Attempt #{attempt} - Connecting for Timetable...", THEME["warning"])
                try:
                    logged_in = self.try_login(driver, student_number, password)

                    if not self.is_running:
                        break

                    if logged_in:
                        self.update_status("Status: Fetching Exam Admission / Timetable...", THEME["warning"])
                        student_name = self.parse_student_name(driver.page_source)
                        found_link = self.navigate_to_timetable(driver)

                        if not self.is_running:
                            break

                        timetable_data = self.parse_timetable_page(driver.page_source)

                        if not timetable_data and not found_link:
                            self.root.after(0, lambda: self.offer_timetable_fallback(driver))
                        else:
                            self.root.after(
                                0,
                                lambda: ExamAdmissionDashboard(self.root, student_number, student_name, timetable_data, driver)
                            )
                            self.update_status("Status: 🎉 Exam Admission / Timetable Loaded!", THEME["success"])
                        break
                    else:
                        self.update_status(f"Status: Attempt #{attempt} - Server Busy. Retrying...", THEME["warning"])

                except Exception:
                    if not self.is_running:
                        break
                    self.update_status(f"Status: Attempt #{attempt} - Network Error. Retrying...", THEME["error"])

                attempt += 1
                time.sleep(3)

        except Exception as err:
            if self.is_running:
                self.update_status(f"Error: {err}", THEME["error"])
                messagebox.showerror("System Error", str(err))

        finally:
            if self.is_running:
                self.is_running = False
                self.root.after(0, self.reset_ui_state)

    def offer_timetable_fallback(self, driver):
        self.update_status("Status: Could not auto-detect Timetable page", THEME["warning"])
        open_it = messagebox.askyesno(
            "Timetable Page Not Found",
            "Couldn't automatically detect the Exam Admission / Timetable page inside the portal.\n\n"
            "Would you like to open the official Faculty of Science website instead?"
        )
        if open_it:
            webbrowser.open(TIMETABLE_URL)
        try:
            driver.quit()
        except Exception:
            pass

    def run_selenium(self, student_number, password, selected_year):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1920,1080")

            self.active_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver = self.active_driver

            attempt = 1
            while self.is_running:
                self.update_status(f"Status: Attempt #{attempt} - Connecting silently...", THEME["warning"])
                try:
                    driver.get(PORTAL_URL)
                    time.sleep(1)

                    if not self.is_running:
                        break

                    student_input = None
                    password_input = None
                    login_button = None

                    inputs = driver.find_elements(By.TAG_NAME, "input")
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
                        inp_type = (inp.get_attribute("type") or "").lower()
                        if inp_type in ["submit", "button"] or "btn" in (inp.get_attribute("id") or "").lower():
                            login_button = inp
                            break

                    if student_input and login_button:
                        student_input.clear()
                        student_input.send_keys(student_number)

                        if password_input:
                            password_input.clear()
                            if password:
                                password_input.send_keys(password)

                        login_button.click()
                        time.sleep(2)

                        if not self.is_running:
                            break

                        current_url = driver.current_url
                        page_source = driver.page_source.lower()

                        if "sfkn.aspx" not in current_url or "result" in page_source or "welcome" in page_source or "logout" in page_source:
                            self.update_status(f"Status: Fetching {selected_year} Results...", THEME["warning"])

                            self.navigate_to_year(driver, selected_year)

                            if not self.is_running:
                                break

                            student_name = self.parse_student_name(driver.page_source)
                            results_data = self.parse_results_page(driver.page_source)

                            self.root.after(0, lambda: ResultsDashboard(self.root, student_number, student_name, selected_year, results_data, driver))
                            self.update_status("Status: 🎉 Results Loaded Successfully!", THEME["success"])
                            break
                        else:
                            self.update_status(f"Status: Attempt #{attempt} - Server Busy. Retrying...", THEME["warning"])
                    else:
                        self.update_status(f"Status: Attempt #{attempt} - Page Load Error. Retrying...", THEME["warning"])

                except Exception as e:
                    if not self.is_running:
                        break
                    self.update_status(f"Status: Attempt #{attempt} - Network Error. Retrying...", THEME["error"])

                attempt += 1
                time.sleep(3)

        except Exception as err:
            if self.is_running:
                self.update_status(f"Error: {err}", THEME["error"])
                messagebox.showerror("System Error", str(err))

        finally:
            if self.is_running:
                self.is_running = False
                self.root.after(0, self.reset_ui_state)


if __name__ == "__main__":
    auth_app = SystemAuthGuard()
    auth_app.mainloop()