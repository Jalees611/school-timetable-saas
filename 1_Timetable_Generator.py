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

@st.cache_data
def get_resource_template():
    df = pd.DataFrame({
        "resource_name": ["CL-1", "CL-2", "Comp-Lab", "Wastewater-Lab"],
        "resource_type": ["classroom", "classroom", "lab", "lab"]
    })
    return df.to_csv(index=False).encode('utf-8')


# ==========================================
# UI TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🏫 School Timetable", "🎓 College Timetable", "🖨️ View & Download Timetables"])

# --- TAB 1: SCHOOL ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Download School Workload Template", get_school_template(), "school_template.csv", "text/csv")
    with col2:
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
                        st.success("✅ Timetable Generated Successfully! Go to the 'View & Download' tab to see it.")
                    else:
                        st.error("❌ Infeasible! The AI could not fit the schedule. Please check for impossible restrictions.")
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
        else:
            st.warning("⚠️ Please upload the School Workload CSV first.")


# --- TAB 2: COLLEGE ---
with tab2:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📥 Download Workload Template", get_college_template(), "college_template.csv", "text/csv")
    with col2:
        st.download_button("📥 Download Resource Template", get_resource_template(), "resource_template.csv", "text/csv")
    with col3:
        st.download_button("📥 Download Restrictions Template", get_restriction_template(), "restrictions_template.csv", "text/csv", key="college_rest_btn")

    st.markdown("---")
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
                        st.success("✅ Timetable Generated Successfully! Go to the 'View & Download' tab to see it.")
                    else:
                        st.error("❌ Infeasible! Check restrictions or ensure no teacher is mathematically overbooked.")
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
        else:
            st.warning("⚠️ Please upload BOTH the College Workload and the Resource files.")


# --- TAB 3: MASTER DOWNLOADS & VIEWER ---
with tab3:
    st.header("🖨️ View & Download Generated Timetables")
    
    if os.path.exists('final_timetable_result.csv'):
        # Ignore excel character decoding errors just to be safe
        try:
            df = pd.read_csv('final_timetable_result.csv', encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv('final_timetable_result.csv', encoding='windows-1252')
            
        st.success("✅ A generated timetable is currently available in memory!")

        # --- DATA FORMATTING FOR BEAUTIFUL GRIDS ---
        days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        df['Day'] = pd.Categorical(df['Day'], categories=days_order, ordered=True)
        df['Period_Num'] = df['Period'].str.extract(r'(\d+)').astype(int)
        df = df.sort_values(['Day', 'Period_Num'])

        df['Class_View'] = df['Subject'] + " (" + df['Teacher'] + ") [" + df['Room'] + "]"
        df['Teacher_View'] = df['Subject'] + " (" + df['Class'] + ") [" + df['Room'] + "]"

        # Pivot the Tables
        class_grid = df.pivot_table(index=['Day', 'Period'], columns='Class', values='Class_View', aggfunc=lambda x: " / ".join(x)).fillna("---")
        teacher_grid = df.pivot_table(index=['Day', 'Period'], columns='Teacher', values='Teacher_View', aggfunc=lambda x: " / ".join(x)).fillna("---")

        # --- DISPLAY SUB-TABS ---
        grid_tab1, grid_tab2, grid_tab3 = st.tabs(["🎒 Class View", "👨‍🏫 Teacher View", "📄 Raw List & Filters"])

        # 1. CLASS VIEWER WITH DROPDOWN
        with grid_tab1:
            st.subheader("🎒 Class Timetable Viewer")
            all_classes = sorted(df['Class'].dropna().unique())
            selected_class = st.selectbox("Select a Class to view:", all_classes, key="view_class")
            
            # Show ONLY the selected class on the screen
            st.dataframe(class_grid[[selected_class]], use_container_width=True)
            
            st.markdown("---")
            st.markdown("⬇️ **Download Complete Data**")
            # The download button still downloads the ENTIRE master grid
            st.download_button("💾 Download COMPLETE Master Classes Grid (CSV)", class_grid.to_csv().encode('utf-8'), "Master_Classes_Grid.csv", "text/csv", key="cg_dl")

        # 2. TEACHER VIEWER WITH DROPDOWN
        with grid_tab2:
            st.subheader("👨‍🏫 Teacher Timetable Viewer")
            all_teachers = sorted(df['Teacher'].dropna().unique())
            selected_teacher = st.selectbox("Select a Teacher to view:", all_teachers, key="view_teacher")
            
            # Show ONLY the selected teacher on the screen
            st.dataframe(teacher_grid[[selected_teacher]], use_container_width=True)
            
            st.markdown("---")
            st.markdown("⬇️ **Download Complete Data**")
            # The download button still downloads the ENTIRE master grid
            st.download_button("💾 Download COMPLETE Master Teachers Grid (CSV)", teacher_grid.to_csv().encode('utf-8'), "Master_Teachers_Grid.csv", "text/csv", key="tg_dl")

        # 3. RAW DATA & INDIVIDUAL LIST DOWNLOADS
        with grid_tab3:
            st.subheader("Raw List Data")
            clean_df = df.drop(columns=['Period_Num', 'Class_View', 'Teacher_View'])
            st.dataframe(clean_df, use_container_width=True)
            st.download_button("💾 Download Raw List", clean_df.to_csv(index=False).encode('utf-8'), "Raw_Timetable_List.csv", "text/csv", key="raw_dl")

            st.markdown("---")
            colA, colB = st.columns(2)
            with colA:
                st.subheader("🎒 Download Single Class")
                selected_class_list = st.selectbox("Select a Class:", all_classes, key="dl_class")
                class_df = clean_df[clean_df['Class'] == selected_class_list]
                st.download_button(f"💾 Download {selected_class_list} List", class_df.to_csv(index=False).encode('utf-8'), f"{selected_class_list}_Timetable.csv", "text/csv", key="class_dl")

            with colB:
                st.subheader("👨‍🏫 Download Single Teacher")
                selected_teacher_list = st.selectbox("Select a Teacher:", all_teachers, key="dl_teacher")
                teacher_df = clean_df[clean_df['Teacher'] == selected_teacher_list]
                st.download_button(f"💾 Download {selected_teacher_list} List", teacher_df.to_csv(index=False).encode('utf-8'), f"{selected_teacher_list}_Timetable.csv", "text/csv", key="teacher_dl")

    else:
        st.info("ℹ️ No timetable has been generated yet. Please go to the School or College tab, upload your files, and click Generate first!")