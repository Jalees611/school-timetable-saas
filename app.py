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
if 'current_periods' not in st.session_state:
    st.session_state['current_periods'] = 8

# 3. Sidebar Settings
st.sidebar.header("⚙️ Institution Settings")
num_periods = st.sidebar.slider("Number of Periods per Day", 5, 12, 8)
st.session_state['current_periods'] = num_periods

# 4. Secure Data Processing Function
def run_generation(institution_type, workload_file, rest_file, res_file=None):
    # Prepare files for the engine
    df = pd.read_csv(workload_file)
    df['institution_type'] = institution_type.lower()
    df.to_csv('school_data.csv', index=False)
    
    if rest_file:
        pd.read_csv(rest_file).to_csv('restrictions_data.csv', index=False)
    
    if res_file:
        pd.read_csv(res_file).to_csv('resource_data.csv', index=False)
    elif institution_type == 'college':
        st.error("⚠️ College mode requires a Resource Registry file!")
        return

    with st.spinner(f"AI is calculating {institution_type} constraints..."):
        # Run the engine
        solve_timetable(num_periods=st.session_state['current_periods'])
        
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
    s_work = st.file_uploader("Upload School Workload", key="s_work")
    if st.button("🚀 Generate School Timetable"):
        if s_work: run_generation('school', s_work, None)

with tab2:
    st.header("College Setup")
    c_work = st.file_uploader("Upload College Workload", key="c_work")
    c_res = st.file_uploader("Upload Resource Registry", key="c_res")
    if st.button("🧠 Generate College Timetable"):
        if c_work and c_res: run_generation('college', c_work, None, c_res)

# 6. Secure Results Display
if st.session_state['generated_data'] is not None:
    st.divider()
    res_df = st.session_state['generated_data']
    
    # Download button using in-memory buffer (No shared file)
    csv_buffer = io.StringIO()
    res_df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download Results", csv_buffer.getvalue(), "timetable.csv", "text/csv")
    
    col_left, col_right = st.columns(2)
    p_list = [f'Period {i}' for i in range(1, st.session_state['current_periods'] + 1)]

    with col_left:
        teacher = st.selectbox("View by Teacher", sorted(res_df['Teacher'].unique()))
        t_view = res_df[res_df['Teacher'] == teacher].pivot(index='Period', columns='Day', values='Class')
        st.table(t_view.reindex(p_list).fillna("-"))

    with col_right:
        cls = st.selectbox("View by Class", sorted(res_df['Class'].unique()))
        c_view = res_df[res_df['Class'] == cls].pivot(index='Period', columns='Day', values='Subject')
        st.table(c_view.reindex(p_list).fillna("-"))