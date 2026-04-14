import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable

# 1. Page Configuration
st.set_page_config(page_title="AI Timetable Generator Pro", layout="wide")

# 2. Sidebar Settings
st.sidebar.header("⚙️ Institution Settings")
num_periods = st.sidebar.slider("Number of Periods per Day", min_value=5, max_value=12, value=8)

st.sidebar.divider()
st.sidebar.markdown("""
**How to use:**
1. Select Periods in the slider.
2. Choose your Institution Tab.
3. Upload your CSV files.
4. Click 'Generate'.
""")

# 3. Main UI Header
st.title("📅 Smart Timetable Generator")

# 4. Data Processing Helper Function
def run_generation(institution_type, workload_file, rest_file, res_file=None):
    # Read the uploaded workload
    df = pd.read_csv(workload_file)
    
    # CRITICAL: This line tells the engine which rules to use (School vs College)
    df['institution_type'] = institution_type.lower()
    df.to_csv('school_data.csv', index=False)
    
    # Handle Restrictions
    if rest_file:
        pd.read_csv(rest_file).to_csv('restrictions_data.csv', index=False)
    else:
        if os.path.exists('restrictions_data.csv'): 
            os.remove('restrictions_data.csv')

    # Handle Resources (Required for College)
    if res_file:
        pd.read_csv(res_file).to_csv('resource_data.csv', index=False)
    elif institution_type == 'college':
        st.error("⚠️ College mode requires a Resource Registry file!")
        return

    # Call the AI Engine
    with st.spinner(f"AI is calculating {institution_type} constraints for {num_periods} periods..."):
        solve_timetable(num_periods=num_periods)

# 5. The Tabs Interface
tab1, tab2 = st.tabs(["🏫 School Mode", "🎓 College/University Mode"])

# --- SCHOOL TAB ---
with tab1:
    st.header("School Timetable Setup")
    st.info("Single-period mode: No consecutive blocks forced.")
    col1, col2 = st.columns(2)
    with col1:
        school_workload = st.file_uploader("Upload School Workload (CSV)", key="school_work")
    with col2:
        school_rest = st.file_uploader("Upload School Restrictions (Optional)", key="school_rest")
        
    if st.button("🚀 Generate School Timetable"):
        if school_workload:
            run_generation('school', school_workload, school_rest)
        else:
            st.error("Please upload the workload file.")

# --- COLLEGE TAB ---
with tab2:
    st.header("College/University Timetable Setup")
    st.warning("University Rules: Forces 2-hour Theory blocks and 3-hour Lab blocks.")
    c1, c2, c3 = st.columns(3)
    with c1:
        college_workload = st.file_uploader("Upload College Workload", key="coll_work")
    with c2:
        college_rest = st.file_uploader("Upload Restrictions", key="coll_rest")
    with c3:
        college_res = st.file_uploader("Upload Room/Lab Registry", key="coll_res")
        
    if st.button("🧠 Generate College Timetable"):
        if college_workload and college_res:
            run_generation('college', college_workload, college_rest, college_res)
        else:
            st.error("College mode requires both Workload and Resource files.")

# --- 6. RESULTS DISPLAY SECTION ---
if os.path.exists('final_timetable_result.csv'):
    st.divider()
    st.header("🔍 View & Filter Timetables")
    
    res_df = pd.read_csv('final_timetable_result.csv')
    
    with open("final_timetable_result.csv", "rb") as file:
        st.download_button("📥 Download Full CSV", file, "timetable_results.csv", "text/csv")
    
    disp_col1, disp_col2 = st.columns(2)
    
    with disp_col1:
        teacher_list = sorted(res_df['Teacher'].unique())
        selected_teacher = st.selectbox("Select Teacher", teacher_list)
        teacher_view = res_df[res_df['Teacher'] == selected_teacher].pivot(
            index='Period', columns='Day', values='Class'
        ).reindex([f'Period {i}' for i in range(1, num_periods + 1)])
        st.subheader(f"Schedule: {selected_teacher}")
        st.table(teacher_view.fillna("-"))

    with disp_col2:
        class_list = sorted(res_df['Class'].unique())
        selected_class = st.selectbox("Select Class", class_list)
        class_view = res_df[res_df['Class'] == selected_class].pivot(
            index='Period', columns='Day', values='Subject'
        ).reindex([f'Period {i}' for i in range(1, num_periods + 1)])
        st.subheader(f"Schedule: {selected_class}")
        st.table(class_view.fillna("-"))

# --- 7. TEMPLATE SECTION ---
st.divider()
st.subheader("📥 Templates")
t_col1, t_col2, t_col3 = st.columns(3)
with t_col1:
    st.download_button("Workload Template", pd.DataFrame({'teacher_name': ['A', 'B'], 'subject_name': ['X', 'Y'], 'class_name': ['1', '2'], 'weekly_period': [5, 6], 'required_resource_type': ['classroom', 'lab']}).to_csv(index=False), "workload.csv")
with t_col2:
    st.download_button("Restrictions Template", pd.DataFrame({'teacher_name': ['A'], 'day': ['Mon'], 'period': ['Period 1'], 'restriction_type': ['Unavailable']}).to_csv(index=False), "rest.csv")
with t_col3:
    st.download_button("Resource Template", pd.DataFrame({'resource_name': ['Lab 1'], 'resource_type': ['lab']}).to_csv(index=False), "res.csv")