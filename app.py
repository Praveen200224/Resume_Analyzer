import os
import sys
import subprocess
import base64
import io
import streamlit as st
from config.database import init_database, verify_admin, log_admin_action, get_database_connection, save_resume_data, save_analysis_data, save_ai_analysis_data, get_ai_analysis_stats, reset_ai_analysis_stats, get_detailed_ai_analysis_stats
from dashboard.admin_dashboard import admin_dashboard
from ui_components import apply_modern_styles, hero_section, feature_card, page_header
from feedback.feedback import FeedbackManager
from jobs.job_search import render_job_search
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
from dashboard.dashboard import DashboardManager
from config.courses import COURSES_BY_CATEGORY, RESUME_VIDEOS, INTERVIEW_VIDEOS, get_courses_for_role, get_category_for_role
from config.job_roles import JOB_ROLES
from utils.ai_resume_analyzer import AIResumeAnalyzer
from utils.resume_builder import ResumeBuilder
from utils.resume_analyzer import ResumeAnalyzer
import traceback
import plotly.express as px
import pandas as pd
import json
import datetime

# Ensure DB tables exist before starting Streamlit
init_database()

# Set page config at the very beginning
st.set_page_config(
    page_title="Smart Resume AI",
    page_icon="🚀",
    layout="wide"
)


class ResumeApp:
    def render_empty_state(self, icon, message):
        """Render an empty state with icon and message"""
        return f"""
            <div style='text-align: center; padding: 2rem; color: #666;'>
                <i class='{icon}' style='font-size: 2rem; margin-bottom: 1rem; color: #00bfa5;'></i>
                <p style='margin: 0;'>{message}</p>
            </div>
        """
    def __init__(self):
        """Initialize the application"""
        if 'form_data' not in st.session_state:
            st.session_state.form_data = {
                'personal_info': {
                    'full_name': '',
                    'email': '',
                    'phone': '',
                    'location': '',
                    'linkedin': '',
                    'portfolio': ''
                },
                'summary': '',
                'experiences': [],
                'education': [],
                'projects': [],
                'skills_categories': {
                    'technical': [],
                    'soft': [],
                    'languages': [],
                    'tools': []
                }
            }

        if 'page' not in st.session_state:
            st.session_state.page = 'home'

        if 'is_admin' not in st.session_state:
            st.session_state.is_admin = False

        self.pages = {
            "🏠 HOME": self.render_home,
            "🔍 RESUME ANALYZER": self.render_analyzer,
            "📝 RESUME BUILDER": self.render_builder,
            "📊 DASHBOARD": self.render_dashboard,
            "🎯 JOB SEARCH": self.render_job_search,
            "💬 FEEDBACK": self.render_feedback_page,
            "ℹ️ ABOUT": self.render_about
        }

        self.dashboard_manager = DashboardManager()
        self.analyzer = ResumeAnalyzer()
        self.ai_analyzer = AIResumeAnalyzer()
        self.builder = ResumeBuilder()
        self.job_roles = JOB_ROLES

        if 'user_id' not in st.session_state:
            st.session_state.user_id = 'default_user'
        if 'selected_role' not in st.session_state:
            st.session_state.selected_role = None

        init_database()

        with open('style/style.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        st.markdown("""
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        """, unsafe_allow_html=True)

        if 'resume_data' not in st.session_state:
            st.session_state.resume_data = []
        if 'ai_analysis_stats' not in st.session_state:
            st.session_state.ai_analysis_stats = {
                'score_distribution': {},
                'total_analyses': 0,
                'average_score': 0
            }

    # ================= MAIN ENTRY =================
    def main(self):
        self.apply_global_styles()
        self.render_sidebar()

        # If admin is logged in, show admin dashboard directly
        if st.session_state.get("is_admin", False):
            self.render_admin_dashboard()
            self.add_footer()
            return

        if 'initial_load' not in st.session_state:
            st.session_state.initial_load = True
            st.session_state.page = 'home'
            st.rerun()

        current_page = st.session_state.get('page', 'home')
        page_mapping = {name.lower().replace(" ", "_").replace("🏠", "").replace("🔍", "").replace("📝", "").replace("📊", "").replace("🎯", "").replace("💬", "").replace("ℹ️", "").strip(): name for name in self.pages.keys()}

        if current_page in page_mapping:
            self.pages[page_mapping[current_page]]()
        else:
            self.render_home()

        self.add_footer()

    # ================== UTILS ==================
    def apply_global_styles(self):
        st.markdown("""
        <style>
        body { font-family: 'Poppins', sans-serif; }
        </style>
        """, unsafe_allow_html=True)

    def load_lottie_url(self, url: str):
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()

    def add_footer(self):
        st.markdown("<hr style='margin-top: 50px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.markdown("""
            <p style='text-align: center;'>Powered by <b>Streamlit</b> and <b>Google Gemini AI</b> | Developed by <b>Praveen</b></p>
            """, unsafe_allow_html=True)

    def render_sidebar(self):
        with st.sidebar:
            st_lottie(self.load_lottie_url("https://assets5.lottiefiles.com/packages/lf20_xyadoh9h.json"), height=200, key="sidebar_animation")
            st.title("Smart Resume AI")
            st.markdown("---")
            # Always show all page buttons, including Resume Analyzer
            for page_name in self.pages.keys():
                button_label = page_name
                if st.button(button_label, use_container_width=True):
                    cleaned_name = page_name.lower().replace(" ", "_").replace("🏠", "").replace("🔍", "").replace("📝", "").replace("📊", "").replace("🎯", "").replace("💬", "").replace("ℹ️", "").strip()
                    st.session_state.page = cleaned_name
                    st.rerun()
            st.markdown("---")
            if st.session_state.get('is_admin', False):
                st.success(f"Logged in as: {st.session_state.get('current_admin_email')}")
                if st.button("Logout"):
                    log_admin_action(st.session_state.get('current_admin_email'), "logout")
                    st.session_state.is_admin = False
                    st.session_state.current_admin_email = None
                    st.rerun()
            else:
                with st.expander("👤 Admin Login"):
                    admin_email_input = st.text_input("Email")
                    admin_password = st.text_input("Password", type="password")
                    if st.button("Login"):
                        if verify_admin(admin_email_input, admin_password):
                            st.session_state.is_admin = True
                            st.session_state.current_admin_email = admin_email_input
                            log_admin_action(admin_email_input, "login")
                            st.rerun()
                        else:
                            st.error("Invalid credentials")

    # ============ PAGE RENDERING FUNCTIONS ============
    def render_home(self):
        apply_modern_styles()
        hero_section("Smart Resume AI", "Transform your career with AI-powered resume analysis and building.")
        st.markdown('<div class="feature-grid">', unsafe_allow_html=True)
        feature_card("fas fa-robot", "AI-Powered Analysis", "Get instant feedback on your resume.")
        feature_card("fas fa-magic", "Smart Resume Builder", "Create professional resumes.")
        feature_card("fas fa-chart-line", "Career Insights", "Access detailed analytics.")
        st.markdown('</div>', unsafe_allow_html=True)

    def render_analyzer(self):
        apply_modern_styles()
        page_header("Resume Analyzer", "Get instant AI-powered feedback to optimize your resume")
        # Add tabs for Standard Analyzer and AI Analyzer
        tab1, tab2 = st.tabs(["Standard Analyzer", "AI Analyzer"])

        with tab1:
            # Standard Analyzer UI (existing code)
            categories = list(self.job_roles.keys())
            selected_category = st.selectbox("Job Category", categories, key="standard_category")
            roles = list(self.job_roles[selected_category].keys())
            selected_role = st.selectbox("Specific Role", roles, key="standard_role")
            role_info = self.job_roles[selected_category][selected_role]

            st.markdown(f"""
            <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                <p>{role_info['description']}</p>
                <h4>Required Skills:</h4>
                <p>{', '.join(role_info['required_skills'])}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("Upload Your Resume")
            uploaded_file = st.file_uploader("Choose a PDF or DOCX resume to analyze", type=["pdf", "docx"], key="standard_upload")
            if uploaded_file:
                st.markdown("---")
                st.subheader("Resume Analysis Results")
                with st.spinner("Analyzing your resume..."):
                    try:
                        num_pages = 1
                        if uploaded_file.type == "application/pdf":
                            try:
                                from PyPDF2 import PdfReader
                                uploaded_file.seek(0)
                                reader = PdfReader(uploaded_file)
                                num_pages = len(reader.pages)
                            except Exception:
                                pass
                            uploaded_file.seek(0)
                            text = self.analyzer.extract_text_from_pdf(uploaded_file)
                        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                            try:
                                from docx import Document
                                uploaded_file.seek(0)
                                doc = Document(uploaded_file)
                                num_pages = len(doc.element.xpath('//w:sectPr'))
                                if num_pages == 0:
                                    num_pages = 1
                            except Exception:
                                pass
                            uploaded_file.seek(0)
                            text = self.analyzer.extract_text_from_docx(uploaded_file)
                        else:
                            st.error("Unsupported file type.")
                            return
                        if num_pages > 3:
                            st.warning("Please upload a resume file (max 2 pages). The uploaded document has more than 3 pages and does not appear to be a resume.")
                            st.stop()
                        # --- Resume content validation ---
                        import re
                        resume_keywords = ["experience", "education", "skills", "summary", "projects", "certification", "profile", "objective"]
                        found_keywords = [kw for kw in resume_keywords if kw in text.lower()]
                        # Check for name/email pattern near the top
                        first_500 = text[:500].lower()
                        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
                        # Only accept if an actual email is present near the top
                        email_like = bool(email_pattern.search(first_500))
                        # Check for main section in first 20% of text
                        main_sections = ["experience", "education", "skills"]
                        first_20pct = text[:max(1, int(len(text)*0.2))].lower()
                        has_main_section = any(kw in first_20pct for kw in main_sections)
                        # Block common report/assignment files if resume keywords are not present and no email is found
                        report_words = ["project report", "assignment", "main project"]
                        first_20pct = text[:max(1, int(len(text)*0.2))].lower()
                        is_report = any(w in first_20pct for w in report_words)
                        # Debug info removed for production
                        if (len(found_keywords) < 3 or len(text) < 600 or not email_like or not has_main_section or (is_report and not email_like)):
                            st.warning("Please upload the correct resume. The uploaded document does not appear to be a resume.")
                            st.stop()
                        resume_data = {'raw_text': text}
                        job_requirements = role_info
                        analysis = self.analyzer.analyze_resume(resume_data, job_requirements)
                    except Exception as e:
                        st.error(f"Error analyzing resume: {str(e)}")
                        return

                    # ATS Score
                    ats_score = analysis.get('ats_score', 0)
                    st.markdown(f"""
                    <div class='feature-card' style='margin-bottom:24px;'>
                        <h2>ATS Score</h2>
                        <div style='font-size:2.5rem;color:#4CAF50;font-weight:bold;'>{ats_score}</div>
                        <div style='color:#4CAF50;font-weight:bold;'>Excellent</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Format Analysis
                    format_score = analysis.get('format_score', 0)
                    section_score = analysis.get('section_score', 0)
                    st.markdown(f"""
                    <div class='feature-card' style='margin-bottom:24px;'>
                        <h2>Format Analysis</h2>
                        <div style='display:flex;gap:32px;'>
                            <div>
                                <div style='font-size:1.5rem;'>{format_score}%</div>
                            </div>
                            <div>
                                <div style='font-size:2rem;color:#4CAF50;font-weight:bold;'>Section Score</div>
                                <div style='font-size:1.5rem;'>{section_score}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Skills Match
                    score = int(analysis.get('keyword_match', {}).get('score', 0))
                    found_skills = analysis['keyword_match'].get('found_skills', [])
                    missing_skills = analysis['keyword_match'].get('missing_skills', [])
                    st.markdown(f"""
                    <div class='feature-card' style='margin-bottom:24px;'>
                        <h2>Skills Match</h2>
                        <div style='font-size:1.5rem;'>Keyword Match: <span style='color:#4CAF50;font-weight:bold;'>{score}%</span></div>
                        <div style='margin-top:12px;'>
                            <span style='font-weight:bold; color:#4CAF50;'>Found Skills:</span>
                            {' '.join([f"<span class='skill-tag' style='background:#e8f5e9;color:#388e3c;padding:6px 14px;border-radius:20px;'>{skill}</span>" for skill in found_skills])}
                        </div>
                        <div style='margin-top:12px;'>
                            <span style='font-weight:bold; color:#FF4444;'>Missing Skills:</span>
                            <ul>{''.join([f'<li>{skill}</li>' for skill in missing_skills])}</ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Resume Improvement Suggestions
                    suggestions = analysis.get('suggestions', {})
                    if isinstance(suggestions, list):
                        # If suggestions is a list, show all items
                        st.markdown(f"""
                        <div class='feature-card' style='margin-bottom:24px;'>
                            <h2>Resume Improvement Suggestions</h2>
                            <ul>{''.join([f'<li>{item}</li>' for item in suggestions])}</ul>
                        </div>
                        """, unsafe_allow_html=True)
                    elif isinstance(suggestions, dict):
                        st.markdown(f"""
                        <div class='feature-card' style='margin-bottom:24px;'>
                            <h2>Resume Improvement Suggestions</h2>
                            <div style='margin-bottom:12px;'>
                                <span style='color:#4CAF50;font-weight:bold;'>Contact Information</span>
                                <ul>{''.join([f'<li>{item}</li>' for item in suggestions.get('contact', [])])}</ul>
                            </div>
                            <div style='margin-bottom:12px;'>
                                <span style='color:#4CAF50;font-weight:bold;'>Skills</span>
                                <ul>{''.join([f'<li>{item}</li>' for item in suggestions.get('skills', [])])}</ul>
                            </div>
                            <div style='margin-bottom:12px;'>
                                <span style='color:#4CAF50;font-weight:bold;'>Formatting</span>
                                <ul>{''.join([f'<li>{item}</li>' for item in suggestions.get('formatting', [])])}</ul>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Recommended Courses and Videos
                    # Recommended Courses: use selected_role
                    recommended_courses = get_courses_for_role(selected_role) or []
                    if recommended_courses:
                        st.markdown("""
                        <div class='feature-card' style='margin-top:32px;'>
                            <h2 style='display:flex;align-items:center;font-size:2.2rem;margin-bottom:18px;'>
                                <span style='margin-right:12px;'>📚</span>Recommended Courses
                            </h2>
                            <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:24px;'>
                                {courses_html}
                            </div>
                        </div>
                        """.format(
                            courses_html=''.join([
                                f"<div style='background:#23272f;border-radius:10px;padding:24px;margin-bottom:8px;box-shadow:0 2px 8px rgba(76,175,80,0.08);min-height:120px;display:flex;flex-direction:column;justify-content:center;'><h3 style='color:#4CAF50;margin-bottom:12px;font-size:1.3rem;'>{course[0]}</h3><a href='{course[1]}' target='_blank' style='color:#2196F3;text-decoration:underline;font-size:1.1rem;'>View Course</a></div>"
                                for course in recommended_courses[:8]
                            ])
                        ), unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class='feature-card' style='margin-top:32px;'>
                            <h2 style='display:flex;align-items:center;font-size:2.2rem;margin-bottom:18px;'>
                                <span style='margin-right:12px;'>📚</span>Recommended Courses
                            </h2>
                            <div style='padding:24px;color:#aaa;'>No recommended courses found.</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Helpful Videos: tab control for Resume Tips and Interview Tips
                    video_tab = st.tabs(["Resume Tips", "Interview Tips"])

                    def to_embed_url(url):
                        if "youtube.com/watch?v=" in url:
                            return url.replace("watch?v=", "embed/")
                        elif "youtu.be/" in url:
                            return url.replace("youtu.be/", "youtube.com/embed/")
                        return url

                    with video_tab[0]:
                        resume_videos = []
                        for category, videos in RESUME_VIDEOS.items():
                            resume_videos.extend(videos)
                        if resume_videos:
                            st.markdown("""
                            <div class='feature-card' style='margin-top:32px;'>
                                <h2 style='display:flex;align-items:center;font-size:2.2rem;margin-bottom:18px;'>
                                    <span style='margin-right:12px;'>📺</span>Helpful Videos
                                </h2>
                                <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:24px;'>
                                    {videos_html}
                                </div>
                            </div>
                            """.format(
                                videos_html=''.join([
                                    f"<div style='margin-bottom:10px;'><iframe width='100%' height='320' src='{to_embed_url(video[1])}' frameborder='0' allowfullscreen></iframe></div>"
                                    for video in resume_videos[:4]
                                ])
                            ), unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='padding:24px;color:#aaa;'>No helpful videos found.</div>", unsafe_allow_html=True)

                    with video_tab[1]:
                        interview_videos = INTERVIEW_VIDEOS.get("Interview Tips", [])
                        if interview_videos:
                            st.markdown("""
                            <div class='feature-card' style='margin-top:32px;'>
                                <h2 style='display:flex;align-items:center;font-size:2.2rem;margin-bottom:18px;'>
                                    <span style='margin-right:12px;'>📺</span>Helpful Videos
                                </h2>
                                <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:24px;'>
                                    {videos_html}
                                </div>
                            </div>
                            """.format(
                                videos_html=''.join([
                                    f"<div style='margin-bottom:10px;'><iframe width='100%' height='320' src='{to_embed_url(video[1])}' frameborder='0' allowfullscreen></iframe></div>"
                                    for video in interview_videos[:4]
                                ])
                            ), unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='padding:24px;color:#aaa;'>No interview tips videos found.</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("---")
            st.subheader("AI-Powered Resume Analysis")
            st.markdown("""
                Get detailed insights from advanced AI models that analyze your resume and provide personalized recommendations.<br>
                <b>Upload your resume to get AI-powered analysis and recommendations.</b>
            """, unsafe_allow_html=True)

            # Step 1: Select AI Model
            ai_models = ["Google Gemini", "OpenAI GPT-4", "Custom Model"]
            selected_ai_model = st.selectbox("Select AI Model", ai_models, key="ai_model")

            # Step 2: Optionally use custom job description
            use_custom_job = st.checkbox("Use custom job description", key="ai_custom_job")

            # Step 3: Select Job Category and Role
            categories = list(self.job_roles.keys())
            selected_category = st.selectbox("Job Category", categories, key="ai_category")
            roles = list(self.job_roles[selected_category].keys())
            selected_role = st.selectbox("Specific Role", roles, key="ai_role")
            role_info = self.job_roles[selected_category][selected_role]

            st.markdown(f"""
            <div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                <h3>{selected_role}</h3>
                <p>{role_info['description']}</p>
                <h4>Required Skills:</h4>
                <p>{', '.join(role_info['required_skills'])}</p>
            </div>
            """, unsafe_allow_html=True)

            # Step 4: Resume upload (only after selections)
            uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx"], key="ai_upload")

            if uploaded_file:
                st.markdown("---")
                st.subheader("AI Analysis Results")
                with st.spinner("Analyzing your resume with AI..."):
                    try:
                        num_pages = 1
                        if uploaded_file.type == "application/pdf":
                            try:
                                from PyPDF2 import PdfReader
                                uploaded_file.seek(0)
                                reader = PdfReader(uploaded_file)
                                num_pages = len(reader.pages)
                            except Exception:
                                pass
                            uploaded_file.seek(0)
                            text = self.ai_analyzer.extract_text_from_pdf(uploaded_file)
                        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                            try:
                                from docx import Document
                                uploaded_file.seek(0)
                                doc = Document(uploaded_file)
                                num_pages = len(doc.element.xpath('//w:sectPr'))
                                if num_pages == 0:
                                    num_pages = 1
                            except Exception:
                                pass
                            uploaded_file.seek(0)
                            text = self.ai_analyzer.extract_text_from_docx(uploaded_file)
                        else:
                            st.error("Unsupported file type.")
                            return
                        if num_pages > 3:
                            st.warning("Please upload a resume file (max 2 pages). The uploaded document has more than 3 pages and does not appear to be a resume.")
                            st.stop()
                        # --- Resume content validation ---
                        import re
                        resume_keywords = ["experience", "education", "skills", "summary", "projects", "certification", "profile", "objective"]
                        found_keywords = [kw for kw in resume_keywords if kw in text.lower()]
                        # Check for name/email pattern near the top
                        first_500 = text[:500].lower()
                        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
                        name_like = bool(re.search(r"name|full name|candidate", first_500))
                        email_like = bool(email_pattern.search(first_500))
                        # Check for main section in first 20% of text
                        main_sections = ["experience", "education", "skills"]
                        first_20pct = text[:max(1, int(len(text)*0.2))].lower()
                        has_main_section = any(kw in first_20pct for kw in main_sections)
                        # Block common report/assignment files if resume keywords are not present
                        report_words = ["project report", "assignment", "semester", "main project", "lab manual"]
                        is_report = any(w in text.lower() for w in report_words)
                        # Debug info for validation
                        st.info(f"First 500 chars: {first_500}")
                        st.info(f"Found resume keywords: {found_keywords}")
                        st.info(f"Name-like: {name_like}, Email-like: {email_like}, Has main section: {has_main_section}, Is report: {is_report}")
                        if (len(found_keywords) < 3 or len(text) < 600 or not (name_like or email_like) or not has_main_section or (is_report and len(found_keywords) < 4)):
                            st.warning("Please upload the correct resume. The uploaded document does not appear to be a resume.")
                            st.stop()
                        analysis = self.ai_analyzer.analyze_resume(
                            text,
                            job_role=selected_role,
                            role_info=role_info,
                            model=selected_ai_model
                        )
                        if 'error' in analysis:
                            st.error(f"AI Analysis Error: {analysis['error']}")
                            return
                    except Exception as e:
                        st.error(f"Error in AI analysis: {str(e)}")
                        return

                    st.success("Analysis complete!")
                    st.markdown("## Full Analysis Report")
                    # Header
                    st.markdown(f"""
                        <div class='feature-card' style='margin-bottom:24px;'>
                            <h2>AI Resume Analysis Report</h2>
                            <div><b>Job Role:</b> {selected_role}</div>
                            <div><b>Analysis Date:</b> {datetime.datetime.now().strftime('%B %d, %Y')}</div>
                            <div><b>AI Model:</b> {selected_ai_model}</div>
                            <div><b>Overall Score:</b> {analysis.get('overall_score', 'N/A')}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Score charts
                    resume_score = analysis.get('resume_score')
                    if not resume_score or resume_score == 0:
                        resume_score = analysis.get('score', 0)
                    ats_score = analysis.get('ats_score', 0)
                    st.markdown(f"""
                        <div style='display:flex;gap:32px;'>
                            <div style='flex:1;'>
                                <h3>Resume Score</h3>
                                <div style='font-size:2.5rem;color:#4CAF50;font-weight:bold;'>{resume_score}</div>
                                <div style='color:#4CAF50;font-weight:bold;'>Good</div>
                            </div>
                            <div style='flex:1;'>
                                <h3>ATS Optimization Score</h3>
                                <div style='font-size:2.5rem;color:#FF4444;font-weight:bold;'>{ats_score}</div>
                                <div style='color:#FF4444;font-weight:bold;'>Needs Improvement</div>
                                    <div><b>Overall Score:</b> {analysis.get('score', 'N/A')}</div>
                        </div>
                    """, unsafe_allow_html=True)


                    def section(title, content, color):
                        return f"""
                        <div class='feature-card' style='margin-bottom:24px;background:{color};'>
                            <h3>{title}</h3>
                            <div>{content if content else '<span style=\'color:#aaa\'>No content available.</span>'}</div>
                        </div>
                        """

                    rendered_sections = set()
                    section_defs = [
                        ("📝 Overall Assessment", 'overall_assessment', "#2196F3", False),
                        ("👤 Professional Profile Analysis", 'professional_profile', "#00bfa5", False),
                        ("🛠 Skills Analysis", 'skills_analysis', "#7c4dff", False),
                        ("💼 Experience Analysis", 'experience_analysis', "#e53935", False),
                        ("🎓 Education Analysis", 'education_analysis', "#ffc107", False),
                        ("✅ Key Strengths", 'strengths', "#43a047", True),
                        ("❗ Areas for Improvement", 'weaknesses', "#ff5252", True),
                        ("🛡️ ATS Optimization Assessment", 'ats_optimization', "#00bcd4", False),
                        ("📚 Recommended Courses", 'suggestions', "#7c4dff", True),
                        ("⭐ Resume Score", 'resume_score', "#2196F3", False),
                    ]

                    for title, key, color, is_list in section_defs:
                        if key in rendered_sections:
                            continue
                        rendered_sections.add(key)
                        value = analysis.get(key)
                        if key == 'resume_score' and value is not None:
                            content = f": {value}/100"
                        elif is_list and isinstance(value, list):
                            content = '<br>'.join(value) if value else None
                        elif value:
                            content = value
                        else:
                            content = None
                        # Only render if content is not None and not empty
                        if content and str(content).strip():
                            st.markdown(section(title, content, color), unsafe_allow_html=True)

                    # Show the full AI report only once at the end (optional)
                    if analysis.get('full_response'):
                        st.markdown(section("📝 Full AI Report", analysis['full_response'], "#607d8b"), unsafe_allow_html=True)

    def render_dashboard(self):
        self.dashboard_manager.render_dashboard()

    def render_builder(self):
        st.title("Resume Builder 📝")
        st.write("Create your professional resume")

        # Template selection
        template_options = ["Modern", "Professional", "Minimal", "Creative"]
        selected_template = st.selectbox(
            "Select Resume Template", template_options)
        st.success(f"🎨 Currently using: {selected_template} Template")

        # Personal Information
        st.subheader("Personal Information")

        col1, col2 = st.columns(2)
        with col1:
            existing_name = st.session_state.form_data['personal_info']['full_name']
            existing_email = st.session_state.form_data['personal_info']['email']
            existing_phone = st.session_state.form_data['personal_info']['phone']
            full_name = st.text_input("Full Name", value=existing_name)
            email = st.text_input("Email", value=existing_email, key="email_input")
            phone = st.text_input("Phone", value=existing_phone)
            if 'email_input' in st.session_state:
                st.session_state.form_data['personal_info']['email'] = st.session_state.email_input

        with col2:
            existing_location = st.session_state.form_data['personal_info']['location']
            existing_linkedin = st.session_state.form_data['personal_info']['linkedin']
            existing_portfolio = st.session_state.form_data['personal_info']['portfolio']
            location = st.text_input("Location", value=existing_location)
            linkedin = st.text_input("LinkedIn URL", value=existing_linkedin)
            portfolio = st.text_input("Portfolio Website", value=existing_portfolio)

        st.session_state.form_data['personal_info'] = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'location': location,
            'linkedin': linkedin,
            'portfolio': portfolio
        }

        st.subheader("Professional Summary")
        summary = st.text_area("Professional Summary", value=st.session_state.form_data.get('summary', ''), height=150,
                             help="Write a brief summary highlighting your key skills and experience")

        st.subheader("Work Experience")
        if 'experiences' not in st.session_state.form_data:
            st.session_state.form_data['experiences'] = []
        if st.button("Add Experience"):
            st.session_state.form_data['experiences'].append({
                'company': '',
                'position': '',
                'start_date': '',
                'end_date': '',
                'description': '',
                'responsibilities': [],
                'achievements': []
            })
        for idx, exp in enumerate(st.session_state.form_data['experiences']):
            with st.expander(f"Experience {idx + 1}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    exp['company'] = st.text_input("Company Name", key=f"company_{idx}", value=exp.get('company', ''))
                    exp['position'] = st.text_input("Position", key=f"position_{idx}", value=exp.get('position', ''))
                with col2:
                    exp['start_date'] = st.text_input("Start Date", key=f"start_date_{idx}", value=exp.get('start_date', ''))
                    exp['end_date'] = st.text_input("End Date", key=f"end_date_{idx}", value=exp.get('end_date', ''))
                exp['description'] = st.text_area("Role Overview", key=f"desc_{idx}", value=exp.get('description', ''), help="Brief overview of your role and impact")
                st.markdown("##### Key Responsibilities")
                resp_text = st.text_area("Enter responsibilities (one per line)", key=f"resp_{idx}", value='\n'.join(exp.get('responsibilities', [])), height=100, help="List your main responsibilities, one per line")
                exp['responsibilities'] = [r.strip() for r in resp_text.split('\n') if r.strip()]
                st.markdown("##### Key Achievements")
                achv_text = st.text_area("Enter achievements (one per line)", key=f"achv_{idx}", value='\n'.join(exp.get('achievements', [])), height=100, help="List your notable achievements, one per line")
                exp['achievements'] = [a.strip() for a in achv_text.split('\n') if a.strip()]
                if st.button("Remove Experience", key=f"remove_exp_{idx}"):
                    st.session_state.form_data['experiences'].pop(idx)
                        # ...existing code...
                if st.button("Remove Project", key=f"remove_proj_{idx}"):
                    st.session_state.form_data['projects'].pop(idx)
                    st.rerun()

        st.subheader("Education")
        if 'education' not in st.session_state.form_data:
            st.session_state.form_data['education'] = []
        if st.button("Add Education"):
            st.session_state.form_data['education'].append({
                'school': '',
                'degree': '',
                'field': '',
                'graduation_date': '',
                'gpa': '',
                'achievements': []
            })
        for idx, edu in enumerate(st.session_state.form_data['education']):
            with st.expander(f"Education {idx + 1}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    edu['school'] = st.text_input("School/University", key=f"school_{idx}", value=edu.get('school', ''))
                    edu['degree'] = st.text_input("Degree", key=f"degree_{idx}", value=edu.get('degree', ''))
                with col2:
                    edu['field'] = st.text_input("Field of Study", key=f"field_{idx}", value=edu.get('field', ''))
                    edu['graduation_date'] = st.text_input("Graduation Date", key=f"grad_date_{idx}", value=edu.get('graduation_date', ''))
                edu['gpa'] = st.text_input("GPA (optional)", key=f"gpa_{idx}", value=edu.get('gpa', ''))
                st.markdown("##### Achievements & Activities")
                edu_achv_text = st.text_area("Enter achievements (one per line)", key=f"edu_achv_{idx}", value='\n'.join(edu.get('achievements', [])), height=100, help="List academic achievements, relevant coursework, or activities")
                edu['achievements'] = [a.strip() for a in edu_achv_text.split('\n') if a.strip()]
                if st.button("Remove Education", key=f"remove_edu_{idx}"):
                    st.session_state.form_data['education'].pop(idx)
                    st.rerun()

        st.subheader("Skills")
        if 'skills_categories' not in st.session_state.form_data:
            st.session_state.form_data['skills_categories'] = {
                'technical': [],
                'soft': [],
                'languages': [],
                'tools': []
            }
        col1, col2 = st.columns(2)
        with col1:
            tech_skills = st.text_area("Technical Skills (one per line)", value='\n'.join(st.session_state.form_data['skills_categories']['technical']), height=150, help="Programming languages, frameworks, databases, etc.")
            st.session_state.form_data['skills_categories']['technical'] = [s.strip() for s in tech_skills.split('\n') if s.strip()]
            soft_skills = st.text_area("Soft Skills (one per line)", value='\n'.join(st.session_state.form_data['skills_categories']['soft']), height=150, help="Leadership, communication, problem-solving, etc.")
            st.session_state.form_data['skills_categories']['soft'] = [s.strip() for s in soft_skills.split('\n') if s.strip()]
        with col2:
            languages = st.text_area("Languages (one per line)", value='\n'.join(st.session_state.form_data['skills_categories']['languages']), height=150, help="Programming or human languages with proficiency level")
            st.session_state.form_data['skills_categories']['languages'] = [l.strip() for l in languages.split('\n') if l.strip()]
            tools = st.text_area("Tools & Technologies (one per line)", value='\n'.join(st.session_state.form_data['skills_categories']['tools']), height=150, help="Development tools, software, platforms, etc.")
            st.session_state.form_data['skills_categories']['tools'] = [t.strip() for t in tools.split('\n') if t.strip()]

        st.session_state.form_data.update({'summary': summary})

        if st.button("Generate Resume 📄", type="primary"):
            current_name = st.session_state.form_data['personal_info']['full_name'].strip()
            current_email = st.session_state.email_input if 'email_input' in st.session_state else ''
            if not current_name:
                st.error("⚠️ Please enter your full name.")
                return
            if not current_email:
                st.error("⚠️ Please enter your email address.")
                return
            st.session_state.form_data['personal_info']['email'] = current_email
            try:
                resume_data = {
                    "personal_info": st.session_state.form_data['personal_info'],
                    "summary": st.session_state.form_data.get('summary', '').strip(),
                    "experience": st.session_state.form_data.get('experiences', []),
                    "projects": st.session_state.form_data.get('projects', []),
                    "education": st.session_state.form_data.get('education', []),
                    "skills": st.session_state.form_data.get('skills_categories', {
                        'technical': [],
                        'soft': [],
                        'languages': [],
                        'tools': []
                    }),
                    "template": selected_template
                }
                resume_buffer = self.builder.generate_resume(resume_data)
                if resume_buffer:
                    try:
                        save_resume_data(resume_data)
                        st.success("✅ Resume generated successfully!")
                        st.snow()
                        st.download_button(
                            label="Download Resume 📥",
                            data=resume_buffer,
                            file_name=f"{current_name.replace(' ', '_')}_resume.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            on_click=lambda: st.balloons()
                        )
                    except Exception as db_error:
                        st.warning("⚠️ Resume generated but couldn't be saved to database")
                        st.balloons()
                        st.download_button(
                            label="Download Resume 📥",
                            data=resume_buffer,
                            file_name=f"{current_name.replace(' ', '_')}_resume.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            on_click=lambda: st.balloons()
                        )
                else:
                    st.error("❌ Failed to generate resume. Please try again.")
            except Exception as e:
                st.error(f"❌ Error preparing resume data: {str(e)}")
        st.toast("Check out these repositories: [30-Days-Of-Rust](https://github.com/Hunterdii/30-Days-Of-Rust)", icon="ℹ️")

    def render_job_search(self):
        render_job_search()

    def render_feedback_page(self):
        """Render the feedback page"""
        apply_modern_styles()
        # Page Header
        page_header(
            "Feedback & Suggestions",
            "Help us improve by sharing your thoughts"
        )
        # Use self.feedback_manager to ensure persistent instance
        if not hasattr(self, 'feedback_manager') or self.feedback_manager is None:
            self.feedback_manager = FeedbackManager()
        # Create tabs for form and stats
        form_tab, stats_tab = st.tabs(["Submit Feedback", "Feedback Stats"])
        with form_tab:
            self.feedback_manager.render_feedback_form()
        with stats_tab:
            self.feedback_manager.render_feedback_stats()

    def render_about(self):
        apply_modern_styles()
        st.title("About Smart Resume AI")
        st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center;">
            <div style="background: #232323; border-radius: 24px; padding: 2.5rem 2rem; margin-bottom: 2rem; width: 70%; text-align: center;">
                <div style="font-size: 2.5rem; color: #7be87b; margin-bottom: 0.5rem;">💡</div>
                <h1 style="margin-bottom: 1rem;">Our Vision</h1>
                <p style="font-size: 1.2rem; color: #e0e0e0; font-style: italic;">
                    "Smart Resume AI represents my vision of democratizing career advancement through technology. By combining cutting-edge AI with intuitive design, this platform empowers job seekers at every career stage to showcase their true potential and stand out in today's competitive job market."
                </p>
            </div>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 2rem; width: 100%;">
                <div style="background: #232323; border-radius: 18px; padding: 2rem 1.5rem; width: 320px; text-align: center;">
                    <div style="font-size: 2.5rem; color: #7be87b; margin-bottom: 0.5rem;">🤖</div>
                    <h2>AI-Powered Analysis</h2>
                    <p>Advanced AI algorithms provide detailed insights and suggestions to optimize your resume for maximum impact.</p>
                </div>
                <div style="background: #232323; border-radius: 18px; padding: 2rem 1.5rem; width: 320px; text-align: center;">
                    <div style="font-size: 2.5rem; color: #7be87b; margin-bottom: 0.5rem;">📈</div>
                    <h2>Data-Driven Insights</h2>
                    <p>Make informed decisions with our analytics-based recommendations and industry insights.</p>
                </div>
                <div style="background: #232323; border-radius: 18px; padding: 2rem 1.5rem; width: 320px; text-align: center;">
                    <div style="font-size: 2.5rem; color: #7be87b; margin-bottom: 0.5rem;">🛡️</div>
                    <h2>Privacy First</h2>
                    <p>Your data security is our priority. We ensure your information is always protected and private.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def render_admin_dashboard(self):
        apply_modern_styles()
        st.title("Admin Dashboard")
        admin_dashboard()


if __name__ == "__main__":
    ResumeApp().main()
