import streamlit as st
import pandas as pd
import io
import os
from main_engine import solve_timetable

# 1. Page Configuration
st.set_page_config(page_title="AI Timetable Generator Pro", layout="wide")

# 2. Initialize Private Session Memory
if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None

# 3. Sidebar Settings
st.sidebar.header("⚙️ Institution Settings")
num_periods = st.sidebar.slider("Number of Periods per Day", 5, 12, 8)

# 4. Secure Data Processing Function
def run_generation(institution_type, workload_file, rest_file, res_file=None):
    # Prepare files for the engine
    df = pd.read_csv(workload_file)
    df['institution_type'] = institution_type.lower()
    df.to_csv('school_data.csv', index=False)
    
    if rest_file:
        pd.read_csv(rest_file).to_csv('restrictions_data.csv', index=False)
    else:
        # Clear any old restrictions if a new one isn't provided
        if os.path.exists('restrictions_data.csv'): os.remove('restrictions_data.csv')
    
    if res_file:
        pd.read_csv(res_file).to_csv('resource_data.csv', index=False)

    with st.spinner(f"AI is calculating {institution_type} constraints..."):
        solve_timetable(num_periods=num_periods)
        
        # Move result to private memory and DELETE the server file for privacy
        if os.path.exists('final_timetable_result.csv'):
            st.session_state['generated_data'] = pd.read_csv('final_timetable_result.csv')
            os.remove('final_timetable_result.csv')
        else:
            st.error("AI could not find a valid solution. Try reducing constraints.")

# 5. User Interface Tabs
tab1, tab2 = st.tabs(["🏫 School Mode", "🎓 College/University Mode"])

with tab1:
    st.header("School Setup")
    col1, col2 = st.columns(2)
    with col1:
        s_work = st.file_uploader("Upload School Workload", key="s_work")
    with col2:
        s_rest = st.file_uploader("Upload School Restrictions (Optional)", key="s_rest")
    
    if st.button("🚀 Generate School Timetable"):
        if s_work: 
            run_generation('school', s_work, s_rest)
        else:
            st.error("Please upload the workload file.")

with tab2:
    st.header("College Setup")
    c_col1, c_col2, c_col3 = st.columns(3)
    with c_col1:
        c_work = st.file_uploader("Upload College Workload", key="c_work")
    with c_col2:
        c_rest = st.file_uploader("Upload Restrictions (Optional)", key="c_rest")
    with c_col3:
        c_res = st.file_uploader("Upload Resource Registry", key="c_res")
        
    if st.button("🧠 Generate College Timetable"):
        if c_work and c_res: 
            run_generation('college', c_work, c_rest, c_res)
        else:
            st.error("College mode requires both Workload and Resource files.")

# 6. Secure Results Display
if st.session_state['generated_data'] is not None:
    st.divider()
    st.header("🔍 View & Filter Timetables")
    res_df = st.session_state['generated_data']
    
    csv_buffer = io.StringIO()
    res_df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download Full CSV", csv_buffer.getvalue(), "timetable.csv", "text/csv")
    
    col_left, col_right = st.columns(2)
    p_list = [f'Period {i}' for i in range(1, num_periods + 1)]

    with col_left:
        teacher = st.selectbox("View by Teacher", sorted(res_df['Teacher'].unique()))
        t_view = res_df[res_df['Teacher'] == teacher].pivot(index='Period', columns='Day', values='Class')
        st.table(t_view.reindex(p_list).fillna("-"))

    with col_right:
        cls = st.selectbox("View by Class", sorted(res_df['Class'].unique()))
        c_view = res_df[res_df['Class'] == cls].pivot(index='Period', columns='Day', values='Subject')
        st.table(c_view.reindex(p_list).fillna("-"))

# 7. TEMPLATE SECTION (RESTORED)
st.divider()
st.subheader("📥 Step 1: Download Sample Templates")
t1, t2, t3 = st.columns(3)
with t1:
    st.markdown("**Workload Template**")
    st.download_button("Download CSV", pd.DataFrame({'teacher_name': ['Dr. Salman'], 'subject_name': ['Chemistry'], 'class_name': ['1st Year'], 'weekly_period': [6], 'required_resource_type': ['lab']}).to_csv(index=False), "workload.csv")
with t2:
    st.markdown("**Restrictions Template**")
    st.download_button("Download CSV", pd.DataFrame({'teacher_name': ['Dr. Salman'], 'day': ['Mon'], 'period': ['Period 1'], 'restriction_type': ['Unavailable']}).to_csv(index=False), "rest.csv")
with t3:
    st.markdown("**Resource Template**")
    st.download_button("Download CSV", pd.DataFrame({'resource_name': ['Lab 1'], 'resource_type': ['lab']}).to_csv(index=False), "res.csv")