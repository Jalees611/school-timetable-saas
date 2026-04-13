import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable

st.set_page_config(page_title="AI Timetable Generator", layout="wide")

st.title("📅 Smart Timetable Generator")
st.markdown("Choose your institution type and upload your files to generate a conflict-free schedule.")

# --- THE NEW TABS ---
tab1, tab2 = st.tabs(["🏫 School Mode", "🎓 College/University Mode"])

# --- SCHOOL TAB ---
with tab1:
    st.header("School Timetable Setup")
    st.info("Best for schools where classes stay in fixed rooms. Room logic is disabled for speed.")
    
    col1, col2 = st.columns(2)
    with col1:
        school_workload = st.file_uploader("Upload School Workload (CSV)", key="school_work")
    with col2:
        school_rest = st.file_uploader("Upload School Restrictions (Optional)", key="school_rest")
        
    if st.button("Generate School Timetable"):
        if school_workload:
            df = pd.read_csv(school_workload)
            df['institution_type'] = 'school'
            df.to_csv('school_data.csv', index=False)
            if school_rest:
                pd.read_csv(school_rest).to_csv('restrictions_data.csv', index=False)
            
            with st.spinner("Generating School Schedule..."):
                solve_timetable()
                if os.path.exists('final_timetable_result.csv'):
                    st.success("✅ School Timetable Ready!")
                    st.download_button("Download Result", open("final_timetable_result.csv", "rb"), "school_timetable.csv")
        else:
            st.error("Please upload the workload file.")

# --- COLLEGE TAB ---
with tab2:
    st.header("College/University Timetable Setup")
    st.warning("College Mode requires a Resource (Room/Lab) list to prevent lab double-booking.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        college_workload = st.file_uploader("Upload Workload", key="coll_work")
    with c2:
        college_rest = st.file_uploader("Upload Restrictions", key="coll_rest")
    with c3:
        college_res = st.file_uploader("Upload Room/Lab Registry", key="coll_res")
        
    if st.button("Generate College Timetable"):
        if college_workload and college_res:
            df = pd.read_csv(college_workload)
            df['institution_type'] = 'college'
            df.to_csv('school_data.csv', index=False)
            pd.read_csv(college_res).to_csv('resource_data.csv', index=False)
            if college_rest:
                pd.read_csv(college_rest).to_csv('restrictions_data.csv', index=False)
            
            with st.spinner("Solving complex resource constraints..."):
                solve_timetable()
                if os.path.exists('final_timetable_result.csv'):
                    st.success("✅ College Timetable Generated!")
                    st.download_button("Download Result", open("final_timetable_result.csv", "rb"), "college_timetable.csv")
        else:
            st.error("College mode requires both Workload and Resource files.")

st.divider()

# --- TEMPLATE SECTION (Restored) ---
st.subheader("📥 Download Sample Templates")
st.write("Use these files as a starting point for your data.")

t_col1, t_col2, t_col3 = st.columns(3)

with t_col1:
    st.markdown("**1. Workload Template**")
    sample_workload = pd.DataFrame({
        'teacher_name': ['Shahid Saeed', 'Abdul Hanan'],
        'subject_name': ['English', 'Chemistry'],
        'class_name': ['IX-BI', 'X-BII'],
        'weekly_period': [5, 6],
        'required_resource_type': ['classroom', 'lab']
    })
    st.download_button("Download Workload CSV", sample_workload.to_csv(index=False), "workload_template.csv")

with t_col2:
    st.markdown("**2. Restrictions Template**")
    sample_rest = pd.DataFrame({
        'teacher_name': ['Shahid Saeed'],
        'day': ['Mon'],
        'period': ['Period 1'],
        'restriction_type': ['Unavailable']
    })
    st.download_button("Download Restrictions CSV", sample_rest.to_csv(index=False), "restrictions_template.csv")

with t_col3:
    st.markdown("**3. Resource Template (College Only)**")
    sample_res = pd.DataFrame({
        'resource_name': ['Lab 01', 'Lecture Hall A'],
        'resource_type': ['lab', 'hall']
    })
    st.download_button("Download Resource CSV", sample_res.to_csv(index=False), "resource_template.csv")