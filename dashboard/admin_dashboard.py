# admin_dashboard.py
import streamlit as st

from config.database import (
    get_resume_stats,
    get_all_resume_data,
    get_admin_logs,
    get_ai_analysis_stats,
    get_all_feedback,
    delete_feedback,
    log_admin_action
)

def admin_dashboard():
    """
    Call this after admin login.
    Precondition: st.session_state['is_admin'] == True
    and st.session_state['admin_email'] set.
    """
    if not st.session_state.get("is_admin"):
        st.error("Access denied — admin only. Please login as admin.")
        return

    admin_email = st.session_state.get("admin_email", "admin")
    st.set_page_config(page_title="Admin Dashboard - ResumeAI", layout="wide")
    st.sidebar.title("ResumeAI — Admin")
    st.sidebar.write(f"Logged in as: **{admin_email}**")
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Resumes", "Feedback", "Settings", "Logout"])

    if menu == "Dashboard":
        st.title("📊 Admin Dashboard")
        stats = get_resume_stats() or {}
        ai_stats = get_ai_analysis_stats() or {}

        c1, c2, c3 = st.columns([1,1,1])
        c1.metric("Total Resumes", stats.get("total_resumes", 0))
        c2.metric("Avg ATS Score", stats.get("avg_ats_score", 0))
        c3.metric("Recent Analyses", ai_stats.get("total_analyses", 0))

        st.markdown("### Recent uploads")
        recent = stats.get("recent_activity", [])
        if recent:
            st.table([{"name": r[0], "target_role": r[1], "created_at": r[2]} for r in recent])
        else:
            st.info("No recent uploads yet.")

    elif menu == "Resumes":
        st.title("🗂️ All Resumes")
        rows = get_all_resume_data()
        if rows:
            # Convert to a simple table view - adapt columns if your tuple structure differs
            st.dataframe(rows)
        else:
            st.info("No resume data available.")

    elif menu == "Feedback":
        st.title("💬 User Feedback")
        feedback_rows = get_all_feedback()
        if not feedback_rows:
            st.info("No feedback yet.")
        else:
            # Show a table and allow deletion
            st.write("**Feedback list (most recent first)**")
            for row in feedback_rows:
                (
                    fid, name, email, message, created,
                    rating, usability_score, feature_satisfaction, missing_features, improvement_suggestions, user_experience
                ) = row
                with st.expander(f"{name or '—'} — {email or '—'} — {created}"):
                    st.markdown(f"**Rating:** {rating if rating is not None else 'N/A'}")
                    st.markdown(f"**Usability Score:** {usability_score if usability_score is not None else 'N/A'}")
                    st.markdown(f"**Feature Satisfaction:** {feature_satisfaction if feature_satisfaction is not None else 'N/A'}")
                    st.markdown(f"**Missing Features:** {missing_features if missing_features else 'N/A'}")
                    st.markdown(f"**Improvement Suggestions:** {improvement_suggestions if improvement_suggestions else 'N/A'}")
                    st.markdown(f"**User Experience:** {user_experience if user_experience else 'N/A'}")
                    st.markdown(f"**Message:** {message if message else 'N/A'}")
                    if st.button("Delete Feedback", key=f"del_{fid}"):
                        ok = delete_feedback(fid)
                        if ok:
                            st.success("Feedback deleted")
                            st.rerun()
                        else:
                            st.error("Failed to delete feedback")

    # Removed Admin Logs and AI Stats sections as requested

    elif menu == "Settings":
        st.title("⚙️ Settings")
        st.write("Add admin-only configuration here (e.g. add admin).")

    elif menu == "Logout":
        # log the logout action
        admin_email = st.session_state.get("admin_email", "admin")
        log_admin_action(admin_email, "logout")
        # clear admin session and reload the app
        st.session_state.clear()
        st.success("Logged out")
        st.rerun()
