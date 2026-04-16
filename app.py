import streamlit as st
import pandas as pd
import io
import os
from main_engine import solve_timetable

st.set_page_config(page_title="AI Timetable Generator Pro", layout="wide")

if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Institution Configuration")

num_periods = st.sidebar.slider("Periods per Day", 5, 12, 8)
num_days = st.sidebar.slider("Working Days per Week", 1, 7, 5)

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

# --- SAFE CSV LOADER ---
def load_csv_safe(file):
    try:
        return pd.read_csv(file, encoding='utf-8')
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, encoding='latin-1')

# --- DATA PROCESSING ---
def run_generation(institution_type, workload_file, rest_file, res_file=None):
    df = load_csv_safe(workload_file)
    df['institution_type'] = institution_type.lower()
    df.to_csv('school_data.csv', index=False)
    
    if rest_file:
        load_csv_safe(rest_file).to_csv('restrictions_data.csv', index=False)
    else:
        if os.path.exists('restrictions_data.csv'): os.remove('restrictions_data.csv')
    
    if res_file:
        load_csv_safe(res_file).to_csv('resource_data.csv', index=False)

    with st.spinner(f"AI calculating strict blocks... this may take up to 60 seconds."):
        solve_timetable(num_periods=num_periods, num_working_days=num_days)
        
        if os.path.exists('final_timetable_result.csv'):
            st.session_state['generated_data'] = pd.read_csv('final_timetable_result.csv')
            os.remove('final_timetable_result.csv')
        else:
            st.error(f"Infeasible! Check restrictions or ensure no teacher/class is assigned more than {total_slots} periods.")

# --- UI TABS ---
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

# --- SECURE DISPLAY LOGIC ---
if st.session_state['generated_data'] is not None:
    st.divider()
    res_df = st.session_state['generated_data']
    
    # Create Display Strings
    res_df['Teacher_Display'] = res_df['Class'] + " (" + res_df['Subject'] + ") [" + res_df['Room'] + "]"
    res_df['Class_Display'] = res_df['Subject'] + " (" + res_df['Teacher'] + ") [" + res_df['Room'] + "]"
    
    p_list = [f'Period {i}' for i in range(1, num_periods + 1)]
    full_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    d_list = full_days[:num_days]

    # --- GENERATE EXPORT FILES ---
    # 1. Master Raw CSV
    csv_buf_raw = io.StringIO()
    res_df.drop(columns=['Teacher_Display', 'Class_Display'], errors='ignore').to_csv(csv_buf_raw, index=False)
    
    # 2. Teacher Grid CSV
    t_rows = []
    for t in sorted(res_df['Teacher'].unique()):
        t_pivot = res_df[res_df['Teacher']==t].pivot(index='Day', columns='Period', values='Teacher_Display').reindex(index=d_list, columns=p_list).fillna("-")
        for d in d_list:
            row = {"Teacher": t, "Day": d}
            for p in p_list: row[p] = t_pivot.loc[d, p]
            t_rows.append(row)
    csv_buf_teacher = io.StringIO()
    pd.DataFrame(t_rows).to_csv(csv_buf_teacher, index=False)
    
    # 3. Class Grid CSV
    c_rows = []
    for c in sorted(res_df['Class'].unique()):
        c_pivot = res_df[res_df['Class']==c].pivot(index='Day', columns='Period', values='Class_Display').reindex(index=d_list, columns=p_list).fillna("-")
        for d in d_list:
            row = {"Class": c, "Day": d}
            for p in p_list: row[p] = c_pivot.loc[d, p]
            c_rows.append(row)
    csv_buf_class = io.StringIO()
    pd.DataFrame(c_rows).to_csv(csv_buf_class, index=False)

    # --- UI DOWNLOAD BUTTONS ---
    st.markdown("### 📥 Export Timetables")
    dl1, dl2, dl3 = st.columns(3)
    with dl1: st.download_button("📋 Download Master CSV (Raw)", csv_buf_raw.getvalue(), "master_timetable.csv", "text/csv", use_container_width=True)
    with dl2: st.download_button("👨‍🏫 Download All Teachers CSV", csv_buf_teacher.getvalue(), "teachers_timetable.csv", "text/csv", use_container_width=True)
    with dl3: st.download_button("📚 Download All Classes CSV", csv_buf_class.getvalue(), "classes_timetable.csv", "text/csv", use_container_width=True)
    
    st.divider()

    # --- UI VISUAL TABLES ---
    st.subheader("👨‍🏫 Teacher Schedule")
    t = st.selectbox("Select Teacher", sorted(res_df['Teacher'].unique()))
    st.table(res_df[res_df['Teacher']==t].pivot(index='Period', columns='Day', values='Teacher_Display').reindex(index=p_list, columns=d_list).fillna("-"))
    
    st.divider()
    
    st.subheader("📚 Class Schedule")
    cl_val = st.selectbox("Select Class", sorted(res_df['Class'].unique()))
    st.table(res_df[res_df['Class']==cl_val].pivot(index='Period', columns='Day', values='Class_Display').reindex(index=p_list, columns=d_list).fillna("-"))

# --- TEMPLATES ---
st.divider()
st.subheader("📥 Templates")
t1, t2, t3 = st.columns(3)
with t1: st.download_button("Workload Template", pd.DataFrame({'teacher_name':['T1'],'subject_name':['Sub1'],'class_name':['C1'],'weekly_period':[5],'required_resource_type':['classroom']}).to_csv(index=False), "workload.csv")
with t2: st.download_button("Restrictions Template", pd.DataFrame({'teacher_name':['T1'],'day':['Mon'],'period':['Period 1'],'restriction_type':['Must Teach']}).to_csv(index=False), "rest.csv")
with t3: st.download_button("Resource Template (College Only)", pd.DataFrame({'resource_name':['Lab1'],'resource_type':['lab']}).to_csv(index=False), "res.csv")