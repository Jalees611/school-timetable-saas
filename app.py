import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable

st.set_page_config(page_title="AI Timetable Generator", layout="wide")

st.title("📅 Smart Timetable Generator")
st.markdown("Choose your institution type to get started.")

# Create the Two Main Tabs
tab1, tab2 = st.tabs(["🏫 School Mode", "🎓 College/University Mode"])

# --- SCHOOL TAB ---
with tab1:
    st.header("School Timetable Setup")
    st.info("In School Mode, the AI focuses on Teacher and Class availability.")
    
    col1, col2 = st.columns(2)
    with col1:
        school_workload = st.file_uploader("Upload School Workload (CSV)", key="school_work")
    with col2:
        school_rest = st.file_uploader("Upload School Restrictions (Optional)", key="school_rest")
        
    if st.button("Generate School Timetable"):
        if school_workload:
            # Save files and inject 'school' tag
            df = pd.read_csv(school_workload)
            df['institution_type'] = 'school'
            df.to_csv('school_data.csv', index=False)
            
            if school_rest:
                pd.read_csv(school_rest).to_csv('restrictions_data.csv', index=False)
            
            with st.spinner("Generating..."):
                solve_timetable()
                if os.path.exists('final_timetable_result.csv'):
                    st.success("✅ School Timetable Ready!")
                    st.download_button("Download CSV", open("final_timetable_result.csv", "rb"), "school_timetable.csv")
        else:
            st.error("Please upload the workload file.")

# --- COLLEGE TAB ---
with tab2:
    st.header("College/University Timetable Setup")
    st.warning("College Mode requires a Resource (Room/Lab) list for proper allocation.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        college_workload = st.file_uploader("Upload Workload", key="coll_work")
    with c2:
        college_rest = st.file_uploader("Upload Restrictions", key="coll_rest")
    with c3:
        college_res = st.file_uploader("Upload Room/Lab Registry", key="coll_res")
        
    if st.button("Generate College Timetable"):
        if college_workload and college_res:
            # Save files and inject 'college' tag
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
                    st.download_button("Download CSV", open("final_timetable_result.csv", "rb"), "college_timetable.csv")
        else:
            st.error("College mode requires both Workload and Resource files.")