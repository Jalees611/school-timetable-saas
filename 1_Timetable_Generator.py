import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable

st.set_page_config(page_title="AI Timetable Generator", page_icon="📅", layout="wide")

# ==========================================
# ⚙️ SIDEBAR SETTINGS
# ==========================================
with st.sidebar:
    st.header("⚙️ Schedule Settings")
    st.markdown("Adjust these sliders to match your school/college hours:")
    num_working_days = st.slider("Number of Working Days", min_value=4, max_value=7, value=5)
    num_periods = st.slider("Periods per Day", min_value=4, max_value=12, value=8)
    
    st.markdown("---")
    st.markdown("**Note:** If you change these sliders, be sure your uploaded data matches! (e.g. don't assign a teacher 40 periods if your sliders only create 30 total slots).")

# ==========================================
# 📖 MAIN INSTRUCTIONS
# ==========================================
st.title("📅 AI-Powered Timetable Generator")
st.markdown("""
### 📖 How to use this app:
1. **Choose your Tab:** Select either 'School' or 'College' below.
2. **Download Templates:** Get the required CSV templates. **Do not change the column names!**
3. **Fill the Data:** Ensure the `institutiontype` column says *School* or *College* for every row.
4. **Upload:** Upload your workload, optional restrictions, and physical room resources (College only).
5. **Generate:** Let the AI solve the mathematical puzzle for you!
""")
st.markdown("---")

# --- HELPER FUNCTIONS ---
def clear_old_files():
    """Deletes old CSV files so School and College data don't mix up."""
    files_to_remove = [f for f in os.listdir('.') if f.endswith('.csv')]
    for f in files_to_remove:
        try: os.remove(f)
        except: pass

def save_uploaded_file(uploaded_file, default_name):
    """Saves the uploaded file to the server."""
    if uploaded_file is not None:
        with open(default_name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    return False

# --- DOWNLOADABLE TEMPLATES ---
@st.cache_data
def get_school_template():
    df = pd.DataFrame({
        "teacher_name": ["John Doe", "Jane Smith"],
        "subject_name": ["Maths", "English"],
        "class_name": ["Pre-IX BI", "VII-BI"],
        "weekly_period": [6, 5],
        "institutiontype": ["School", "School"] 
    })
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def get_college_template():
    df = pd.DataFrame({
        "teacher_name": ["Dr. Jalees", "Hafiza Aroosa"],
        "subject_name": ["Ecology", "Final Year Project Lab"],
        "class_name": ["BS 2024", "BS 2022"],
        "weekly_period": [3, 9],
        "required_resource_type": ["classroom", "lab"],
        "institutiontype": ["College", "College"] 
    })
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def get_restriction_template():
    df = pd.DataFrame({
        "teacher_name": ["Dr. Jalees", "John Doe"],
        "day": ["Mon", "Tue"],
        "period": ["Period 2", "Period 3"],
        "restriction_type": ["Must Teach", "Unavailable"]
    })
    return df.to_csv(index=False).encode('utf-8')


# ==========================================
# UI TABS
# ==========================================
tab1, tab2 = st.tabs(["🏫 School Timetable", "🎓 College Timetable"])

# --- TAB 1: SCHOOL ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Download School Workload Template", get_school_template(), "school_template.csv", "text/csv")
    with col2:
        # ADDED KEY HERE
        st.download_button("📥 Download Restrictions Template", get_restriction_template(), "restrictions_template.csv", "text/csv", key="school_rest_btn")

    school_data = st.file_uploader("1️⃣ Upload School Workload (CSV)", type=['csv'], key="school_data")
    school_rest = st.file_uploader("2️⃣ Upload Restrictions (CSV) - Optional", type=['csv'], key="school_rest")

    if st.button("🚀 Generate School Timetable", type="primary"):
        if school_data is not None:
            with st.spinner("Brainstorming millions of combinations..."):
                clear_old_files() 
                save_uploaded_file(school_data, "school_data.csv")
                save_uploaded_file(school_rest, "restrictions-school.csv")
                
                try:
                    solve_timetable(num_periods=num_periods, num_working_days=num_working_days)
                    
                    if os.path.exists('final_timetable_result.csv'):
                        st.success("✅ Timetable Generated Successfully!")
                        result_df = pd.read_csv('final_timetable_result.csv')
                        st.dataframe(result_df, use_container_width=True)
                        csv = result_df.to_csv(index=False).encode('utf-8')
                        st.download_button("💾 Download Final Timetable", csv, "Final_School_Timetable.csv", "text/csv", key="school_download")
                    else:
                        st.error("❌ Infeasible! The AI could not fit the schedule. Please check for impossible restrictions.")
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
        else:
            st.warning("⚠️ Please upload the School Workload CSV first.")


# --- TAB 2: COLLEGE ---
with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Download College Workload Template", get_college_template(), "college_template.csv", "text/csv")
    with col2:
        # ADDED KEY HERE
        st.download_button("📥 Download Restrictions Template", get_restriction_template(), "restrictions_template.csv", "text/csv", key="college_rest_btn")

    col_data = st.file_uploader("1️⃣ Upload College Workload (CSV)", type=['csv'], key="col_data")
    col_res = st.file_uploader("2️⃣ Upload Resource/Rooms (CSV)", type=['csv'], key="col_res")
    col_rest = st.file_uploader("3️⃣ Upload Restrictions (CSV) - Optional", type=['csv'], key="col_rest")

    if st.button("🚀 Generate College Timetable ", type="primary"):
        if col_data is not None and col_res is not None:
            with st.spinner("Solving complex lab constraints and room allocations..."):
                clear_old_files() 
                save_uploaded_file(col_data, "workload-IEER.csv")
                save_uploaded_file(col_res, "resource_template-IEER.csv")
                save_uploaded_file(col_rest, "restrictons-IEER.csv")
                
                try:
                    solve_timetable(num_periods=num_periods, num_working_days=num_working_days)
                    
                    if os.path.exists('final_timetable_result.csv'):
                        st.success("✅ Timetable Generated Successfully!")
                        result_df = pd.read_csv('final_timetable_result.csv')
                        st.dataframe(result_df, use_container_width=True)
                        csv = result_df.to_csv(index=False).encode('utf-8')
                        # ADDED KEY HERE TO PREVENT FUTURE CRASHES
                        st.download_button("💾 Download Final Timetable", csv, "Final_College_Timetable.csv", "text/csv", key="college_download")
                    else:
                        st.error("❌ Infeasible! Check restrictions or ensure no teacher is mathematically overbooked.")
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
        else:
            st.warning("⚠️ Please upload BOTH the College Workload and the Resource files.")