import streamlit as st
import pandas as pd
import io
import os
from main_engine import solve_timetable

st.set_page_config(page_title="AI Timetable Generator Pro", layout="wide")

if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None

# --- 1. SIDEBAR WITH DUAL SLIDERS & DYNAMIC COUNTING ---
st.sidebar.header("⚙️ Institution Configuration")

num_periods = st.sidebar.slider("Periods per Day", 5, 12, 8)
num_days = st.sidebar.slider("Working Days per Week", 1, 7, 5)

# Dynamic Weekly Count
total_slots = num_periods * num_days

st.sidebar.divider()
st.sidebar.subheader("📊 Capacity Overview")
st.sidebar.metric("Total Weekly Slots", total_slots)

st.sidebar.subheader("📖 Instructions")
st.sidebar.markdown(f"""
**Current Setup:**
- Schedule: **{num_days} days** x **{num_periods} periods**
- Total Capacity: **{total_slots} slots per class/teacher.**

**Steps:**
1. Adjust sliders to match your weekly bell schedule.
2. Upload **Workload CSV**. Ensure total `weekly_period` for any class/teacher does not exceed **{total_slots}**.
3. Upload **Restrictions** to force "Must Teach" or "Unavailable" slots.
4. For **College Mode**, upload a **Resource Registry**.
""")

st.sidebar.info("💡 Data is cleared on refresh for security.")

# 2. Secure Data Processing Function
def run_generation(institution_type, workload_file, rest_file, res_file=None):
    df = pd.read_csv(workload_file)
    df['institution_type'] = institution_type.lower()
    df.to_csv('school_data.csv', index=False)
    
    if rest_file:
        pd.read_csv(rest_file).to_csv('restrictions_data.csv', index=False)
    else:
        if os.path.exists('restrictions_data.csv'): os.remove('restrictions_data.csv')
    
    if res_file:
        pd.read_csv(res_file).to_csv('resource_data.csv', index=False)

    with st.spinner(f"AI calculating {total_slots} potential slots..."):
        # Pass both periods and days to the engine
        solve_timetable(num_periods=num_periods, num_working_days=num_days)
        
        if os.path.exists('final_timetable_result.csv'):
            st.session_state['generated_data'] = pd.read_csv('final_timetable_result.csv')
            os.remove('final_timetable_result.csv')
        else:
            st.error(f"Infeasible! Ensure no teacher/class is assigned more than {total_slots} periods.")

# 3. UI Tabs
tab1, tab2 = st.tabs(["🏫 School Mode", "🎓 College Mode"])

with tab1:
    st.header("School Setup")
    c1, c2 = st.columns(2)
    with c1: s_work = st.file_uploader("Upload Workload", key="sw")
    with c2: s_rest = st.file_uploader("Upload Restrictions (Optional)", key="sr")
    if st.button("🚀 Generate School"):
        if s_work: run_generation('school', s_work, s_rest)

with tab2:
    st.header("College Setup")
    c_c1, c_c2, c_c3 = st.columns(3)
    with c_c1: c_work = st.file_uploader("Upload Workload", key="cw")
    with c_c2: c_rest = st.file_uploader("Upload Restrictions (Optional)", key="cr")
    with c_c3: c_res = st.file_uploader("Upload Resource Registry", key="cre")
    if st.button("🧠 Generate College"):
        if c_work and c_res: run_generation('college', c_work, c_rest, c_res)

# 4. Display Logic
if st.session_state['generated_data'] is not None:
    st.divider()
    res_df = st.session_state['generated_data']
    csv_buf = io.StringIO()
    res_df.to_csv(csv_buf, index=False)
    st.download_button("📥 Download Timetable", csv_buf.getvalue(), "timetable.csv", "text/csv")
    
    cl, cr = st.columns(2)
    p_list = [f'Period {i}' for i in range(1, num_periods + 1)]
    # Use the selected number of days to define column order
    full_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    d_list = full_days[:num_days]

    with cl:
        t = st.selectbox("View Teacher Schedule", sorted(res_df['Teacher'].unique()))
        st.table(res_df[res_df['Teacher']==t].pivot(index='Period', columns='Day', values='Class').reindex(index=p_list, columns=d_list).fillna("-"))
    with cr:
        cl_val = st.selectbox("View Class Schedule", sorted(res_df['Class'].unique()))
        st.table(res_df[res_df['Class']==cl_val].pivot(index='Period', columns='Day', values='Subject').reindex(index=p_list, columns=d_list).fillna("-"))

# 5. Templates
st.divider()
st.subheader("📥 Templates")
t1, t2, t3 = st.columns(3)
with t1: st.download_button("Workload Template", pd.DataFrame({'teacher_name':['T1'],'subject_name':['Sub1'],'class_name':['C1'],'weekly_period':[5],'required_resource_type':['classroom']}).to_csv(index=False), "workload.csv")
with t2: st.download_button("Restrictions Template", pd.DataFrame({'teacher_name':['T1'],'day':['Mon'],'period':['Period 1'],'restriction_type':['Must Teach']}).to_csv(index=False), "rest.csv")
with t3: st.download_button("Resource Template (College Only)", pd.DataFrame({'resource_name':['Lab1'],'resource_type':['lab']}).to_csv(index=False), "res.csv")