import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable

st.set_page_config(page_title="AI Timetable Generator", page_icon="📅", layout="wide")

# ==========================================
# ☁️ CLOUD STORAGE (DISABLED FOR TESTING)
# ==========================================
# We have set supabase to None to force local-only mode.
supabase = None 

def restore_from_cloud(file_name):
    return os.path.exists(file_name)

def backup_to_cloud(file_name):
    pass # Do nothing during testing

# ==========================================
# ⚙️ SIDEBAR SETTINGS
# ==========================================
with st.sidebar:
    st.header("⚙️ Schedule Settings")
    num_working_days = st.slider("Number of Working Days", min_value=4, max_value=7, value=5)
    num_periods = st.slider("Periods per Day", min_value=4, max_value=12, value=8)
    
    st.markdown("---")
    st.warning("🛠️ TEST MODE: Cloud Storage Disabled")
    st.info("Files will be cleared if the server restarts or code is updated.")

# ==========================================
# 📖 MAIN UI & INSTRUCTIONS
# ==========================================
st.title("📅 AI-Powered Timetable Generator")
st.markdown("---")

# --- TEMPLATE HELPERS ---
@st.cache_data
def get_school_template():
    return pd.DataFrame({"teacher_name": ["John Doe"], "subject_name": ["Maths"], "class_name": ["9-A"], "weekly_period": [6], "institutiontype": ["School"]}).to_csv(index=False).encode('utf-8')

@st.cache_data
def get_college_template():
    return pd.DataFrame({"teacher_name": ["Dr. Jalees"], "subject_name": ["Ecology"], "class_name": ["BS 2024"], "weekly_period": [3], "required_resource_type": ["classroom"], "institutiontype": ["College"]}).to_csv(index=False).encode('utf-8')

@st.cache_data
def get_restriction_template():
    return pd.DataFrame({"teacher_name": ["Dr. Jalees"], "day": ["Mon"], "period": ["Period 2"], "restriction_type": ["Unavailable"]}).to_csv(index=False).encode('utf-8')

@st.cache_data
def get_resource_template():
    return pd.DataFrame({"resource_name": ["CL-1", "Comp-Lab"], "resource_type": ["classroom", "lab"]}).to_csv(index=False).encode('utf-8')

def clear_old_files():
    for f in [f for f in os.listdir('.') if f.endswith('.csv')]:
        try: os.remove(f)
        except: pass

def save_uploaded_file(uploaded_file, default_name):
    if uploaded_file:
        with open(default_name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    return False

# ==========================================
# TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🏫 School Timetable", "🎓 College Timetable", "🖨️ View & Download"])

with tab1:
    st.subheader("School Configuration")
    col1, col2 = st.columns(2)
    with col1: st.download_button("📥 Download School Template", get_school_template(), "school_template.csv")
    with col2: st.download_button("📥 Restrictions Template", get_restriction_template(), "restrictions.csv")
    
    school_data = st.file_uploader("Upload Workload (CSV)", type=['csv'], key="s_data")
    school_rest = st.file_uploader("Upload Restrictions (CSV) - Optional", type=['csv'], key="s_rest")
    
    if st.button("🚀 Generate School Timetable", type="primary"):
        if school_data:
            clear_old_files()
            save_uploaded_file(school_data, "school_data.csv")
            if school_rest: save_uploaded_file(school_rest, "restrictions.csv")
            with st.spinner("AI is thinking..."):
                solve_timetable(num_periods, num_working_days)
                if os.path.exists('final_timetable_result.csv'):
                    st.success("✅ Success! Go to View tab.")
                else:
                    st.error("❌ No solution found. Check for teacher overbooking.")

with tab2:
    st.subheader("College Configuration")
    col1, col2, col3 = st.columns(3)
    with col1: st.download_button("📥 College Workload Template", get_college_template(), "college_template.csv")
    with col2: st.download_button("📥 Resource Template", get_resource_template(), "resource_template.csv")
    with col3: st.download_button("📥 Restrictions Template", get_restriction_template(), "college_rest.csv")
    
    c_data = st.file_uploader("Upload College Workload", type=['csv'], key="c_data")
    c_res = st.file_uploader("Upload Resources/Rooms", type=['csv'], key="c_res")
    c_rest = st.file_uploader("Upload Restrictions (Optional)", type=['csv'], key="c_rest")
    
    if st.button("🚀 Generate College Timetable", type="primary"):
        if c_data and c_res:
            clear_old_files()
            save_uploaded_file(c_data, "workload.csv")
            save_uploaded_file(c_res, "resources.csv")
            if c_rest: save