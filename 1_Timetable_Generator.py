import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable

st.set_page_config(page_title="AI Timetable Generator", page_icon="📅", layout="wide")

# ==========================================
# ☁️ CLOUD STORAGE (TEST MODE)
# ==========================================
# Set to None for local testing. Change to init_supabase() later for production.
supabase = None 

def restore_from_cloud(file_name):
    return os.path.exists(file_name)

def backup_to_cloud(file_name):
    pass 

# ==========================================
# 🧠 SESSION STATE (The "Amnesia" Fix)
# ==========================================
if 'timetable_ready' not in st.session_state:
    st.session_state.timetable_ready = False

# ==========================================
# ⚙️ SIDEBAR SETTINGS
# ==========================================
with st.sidebar:
    st.header("⚙️ Schedule Settings")
    num_working_days = st.slider("Number of Working Days", 4, 7, 5)
    num_periods = st.slider("Periods per Day", 4, 12, 8)
    
    st.markdown("---")
    st.warning("🛠️ TEST MODE: Cloud Disabled")
    if st.button("🗑️ Clear All Progress"):
        st.session_state.timetable_ready = False
        if os.path.exists('final_timetable_result.csv'):
            os.remove('final_timetable_result.csv')
        st.rerun()

# ==========================================
# 📖 TEMPLATE HELPERS
# ==========================================
@st.cache_data
def get_template(mode):
    if mode == "school":
        df = pd.DataFrame({"teacher_name": ["John Doe"], "subject_name": ["Maths"], "class_name": ["9-A"], "weekly_period": [6], "institutiontype": ["School"]})
    elif mode == "college":
        df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "subject_name": ["Ecology"], "class_name": ["BS 2024"], "weekly_period": [3], "required_resource_type": ["classroom"], "institutiontype": ["College"]})
    elif mode == "res":
        df = pd.DataFrame({"resource_name": ["CL-1", "MKB"], "resource_type": ["classroom", "lab"]})
    else:
        df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "day": ["Mon"], "period": ["Period 2"], "restriction_type": ["Unavailable"]})
    return df.to_csv(index=False).encode('utf-8')

def clear_old_files():
    for f in [f for f in os.listdir('.') if f.endswith('.csv') and f != 'final_timetable_result.csv']:
        try: os.remove(f)
        except: pass

def save_file(uploaded_file, name):
    with open(name, "wb") as f:
        f.write(uploaded_file.getbuffer())

# ==========================================
# 🏢 MAIN UI TABS
# ==========================================
st.title("📅 AI-Powered Timetable Generator")
tab1, tab2, tab3 = st.tabs(["🏫 School Mode", "🎓 College Mode", "🖨️ View & Download"])

# --- TAB 1: SCHOOL ---
with tab1:
    st.info("Best for Standard K-12 schedules.")
    col1, col2 = st.columns(2)
    with col1: st.download_button("📥 Workload Template", get_template("school"), "school_workload.csv")
    with col2: st.download_button("📥 Restrictions Template", get_template("rest"), "restrictions.csv")
    
    s_data = st.file_uploader("Upload School Workload", type=['csv'], key="s_up")
    s_rest = st.file_uploader("Upload Restrictions (Optional)", type=['csv'], key="sr_up")
    
    if st.button("🚀 Generate School Timetable", type="primary"):
        if s_data:
            clear_old_files()
            save_file(s_data, "school_data.csv")
            if s_rest: save_file(s_rest, "restrictions.csv")
            with st.spinner("AI solving school constraints..."):
                solve_timetable(num_periods, num_working_days)
                if os.path.exists('final_timetable_result.csv'):
                    st.session_state.timetable_ready = True
                    st.success("✅ Timetable Ready! Switch to Tab 3.")
                else:
                    st.error("❌ No solution. Try reducing teacher workload.")

# --- TAB 2: COLLEGE ---
with tab2:
    st.info("Supports 3-period Labs and Room-specific assignments.")
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 Workload", get_template("college"), "college_workload.csv")
    with c2: st.download_button("📥 Resources", get_template("res"), "college_rooms.csv")
    with c3: st.download_button("📥 Restrictions", get_template("rest"), "college_rest.csv")
    
    c_data = st.file_uploader("College Workload", type=['csv'], key="c_up")
    c_res = st.file_uploader("Room Resources", type=['csv'], key="cr_up")
    c_rest = st.file_uploader("Restrictions (Optional)", type=['csv'], key="cre_up")
    
    if st.button("🚀 Generate College Timetable", type="primary"):
        if c_data and c_res:
            clear_old_files()
            save_file(c_data, "workload.csv")
            save_file(c_res, "resources.csv")
            if c_rest: save_file(c_rest, "restrictions.csv")
            with st.spinner("Solving Labs & Theory rooms..."):
                solve_timetable(num_periods, num_working_days)
                if os.path.exists('final_timetable_result.csv'):
                    st.session_state.timetable_ready = True
                    st.success("✅ Done! Check 'View & Download' tab.")
                else:
                    st.error("❌ Infeasible. Ensure you have enough rooms for all classes.")

# --- TAB 3: VIEW & DOWNLOAD ---
with tab3:
    if st.session_state.timetable_ready and os.path.exists('final_timetable_result.csv'):
        df = pd.read_csv('final_timetable_result.csv')
        
        # Grid Configuration
        days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        active_days = days_order[:num_working_days]
        active_periods = [f"Period {i}" for i in range(1, num_periods + 1)]

        df['Day'] = pd.Categorical(df['Day'], categories=days_order, ordered=True)
        df['Class_View'] = df['Subject'] + " (" + df['Teacher'] + ") [" + df['Room'] + "]"
        df['Teacher_View'] = df['Subject'] + " (" + df['Class'] + ") [" + df['Room'] + "]"

        v1, v2, v3 = st.tabs(["🎒 Class Schedule", "👨‍🏫 Teacher Schedule", "📄 Full Data"])
        
        with v1:
            sel_class = st.selectbox("Select Class:", sorted(df['Class'].unique()))
            c_matrix = df[df['Class'] == sel_class].pivot_table(index='Period', columns='Day', values='Class_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=active_days).fillna("---")
            st.dataframe(c_matrix, use_container_width=True)
            
            # Master Download
            master_c = df.pivot_table(index=['Day', 'Period'], columns='Class', values='Class_View', aggfunc=lambda x: x).fillna("---")
            st.download_button("💾 Download Master Class Grid", master_c.to_csv().encode('utf-8'), "Master_Classes.csv")

        with v2:
            sel_teach = st.selectbox("Select Teacher:", sorted(df['Teacher'].unique()))
            t_matrix = df[df['Teacher'] == sel_teach].pivot_table(index='Period', columns='Day', values='Teacher_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=active_days).fillna("---")
            st.dataframe(t_matrix, use_container_width=True)
            
            # Master Download
            master_t = df.pivot_table(index=['Day', 'Period'], columns='Teacher', values='Teacher_View', aggfunc=lambda x: x).fillna("---")
            st.download_button("💾 Download Master Teacher Grid", master_t.to_csv().encode('utf-8'), "Master_Teachers.csv")
            
        with v3:
            st.dataframe(df, use_container_width=True)
            st.download_button("💾 Download Raw Timetable", df.to_csv(index=False).encode('utf-8'), "Raw_Timetable.csv")
    else:
        st.info("ℹ️ No timetable active. Please generate one first.")