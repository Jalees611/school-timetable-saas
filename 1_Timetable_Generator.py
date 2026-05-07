import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable
from supabase import create_client, Client

st.set_page_config(page_title="AI Timetable Generator", page_icon="📅", layout="wide")

# ==========================================
# ☁️ SUPABASE CLOUD CONNECTION
# ==========================================
@st.cache_resource
def init_supabase():
    """Connects to your permanent cloud database."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.sidebar.error(f"🔍 Database Connection Issue: {e}")
        return None

supabase = init_supabase()

def restore_from_cloud(file_name):
    """Restores files from Supabase if Streamlit local memory is wiped."""
    if supabase and not os.path.exists(file_name):
        try:
            data = supabase.storage.from_('user_uploads').download(file_name)
            with open(file_name, "wb") as f:
                f.write(data)
            return True
        except Exception:
            return False
    return os.path.exists(file_name)

def backup_to_cloud(file_name):
    """Saves a permanent copy to Supabase storage."""
    if supabase and os.path.exists(file_name):
        try:
            with open(file_name, "rb") as f:
                supabase.storage.from_('user_uploads').upload(
                    file=f.read(), 
                    path=file_name, 
                    file_options={"upsert": "true"}
                )
        except Exception:
            pass

# ==========================================
# ⚙️ SIDEBAR SETTINGS
# ==========================================
with st.sidebar:
    st.header("⚙️ Schedule Settings")
    num_working_days = st.slider("Number of Working Days", 4, 7, 5)
    num_periods = st.slider("Periods per Day", 4, 12, 8)
    
    st.markdown("---")
    if supabase:
        st.success("☁️ Cloud Database Connected")
    else:
        st.warning("⚠️ Cloud Offline (Local Mode)")

# ==========================================
# 📖 MAIN UI
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
        backup_to_cloud(default_name)
        return True
    return False

# ==========================================
# TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🏫 School", "🎓 College", "🖨️ View & Download"])

with tab1:
    col1, col2 = st.columns(2)
    with col1: st.download_button("📥 School Workload Template", get_school_template(), "school_template.csv")
    with col2: st.download_button("📥 Restrictions Template", get_restriction_template(), "restrictions.csv")
    
    school_data = st.file_uploader("Upload Workload (CSV)", type=['csv'], key="s_data")
    school_rest = st.file_uploader("Upload Restrictions (CSV) - Optional", type=['csv'], key="s_rest")
    
    if st.button("🚀 Generate School Timetable"):
        if school_data:
            clear_old_files()
            save_uploaded_file(school_data, "school_data.csv")
            if school_rest: save_uploaded_file(school_rest, "restrictions.csv")
            with st.spinner("AI Solving..."):
                solve_timetable(num_periods, num_working_days)
                if os.path.exists('final_timetable_result.csv'):
                    backup_to_cloud('final_timetable_result.csv')
                    st.success("✅ Success! Go to View tab.")

with tab2:
    col1, col2, col3 = st.columns(3)
    with col1: st.download_button("📥 College Template", get_college_template(), "college_template.csv")
    with col2: st.download_button("📥 Resource Template", get_resource_template(), "resource_template.csv")
    with col3: st.download_button("📥 Restrictions Template", get_restriction_template(), "rest.csv")
    
    c_data = st.file_uploader("Upload Workload", type=['csv'], key="c_data")
    c_res = st.file_uploader("Upload Resources", type=['csv'], key="c_res")
    c_rest = st.file_uploader("Upload Restrictions", type=['csv'], key="c_rest")
    
    if st.button("🚀 Generate College Timetable"):
        if c_data and c_res:
            clear_old_files()
            save_uploaded_file(c_data, "workload.csv")
            save_uploaded_file(c_res, "resources.csv")
            if c_rest: save_uploaded_file(c_rest, "restrictions.csv")
            with st.spinner("Solving..."):
                solve_timetable(num_periods, num_working_days)
                if os.path.exists('final_timetable_result.csv'):
                    backup_to_cloud('final_timetable_result.csv')
                    st.success("✅ Success!")

with tab3:
    st.header("🖨️ View & Download Timetables")
    restore_from_cloud('final_timetable_result.csv')
    
    if os.path.exists('final_timetable_result.csv'):
        df = pd.read_csv('final_timetable_result.csv')
        days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        active_days = days_order[:num_working_days]
        active_periods = [f"Period {i}" for i in range(1, num_periods + 1)]

        df['Day'] = pd.Categorical(df['Day'], categories=days_order, ordered=True)
        df['Class_View'] = df['Subject'] + " (" + df['Teacher'] + ") [" + df['Room'] + "]"
        df['Teacher_View'] = df['Subject'] + " (" + df['Class'] + ") [" + df['Room'] + "]"

        v_tab1, v_tab2 = st.tabs(["🎒 Class View", "👨‍🏫 Teacher View"])
        
        with v_tab1:
            sel_class = st.selectbox("Select Class:", sorted(df['Class'].unique()))
            c_matrix = df[df['Class'] == sel_class].pivot_table(index='Period', columns='Day', values='Class_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=active_days).fillna("---")
            st.dataframe(c_matrix, use_container_width=True)
            st.download_button("💾 Download Master Classes Grid", df.pivot_table(index=['Day', 'Period'], columns='Class', values='Class_View', aggfunc=lambda x: x).to_csv().encode('utf-8'), "Master_Classes.csv")

        with v_tab2:
            sel_teach = st.selectbox("Select Teacher:", sorted(df['Teacher'].unique()))
            t_matrix = df[df['Teacher'] == sel_teach].pivot_table(index='Period', columns='Day', values='Teacher_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=active_days).fillna("---")
            st.dataframe(t_matrix, use_container_width=True)
            st.download_button("💾 Download Master Teachers Grid", df.pivot_table(index=['Day', 'Period'], columns='Teacher', values='Teacher_View', aggfunc=lambda x: x).to_csv().encode('utf-8'), "Master_Teachers.csv")
    else:
        st.info("No timetable found. Generate one first!")