import streamlit as st
import pandas as pd
import os
import sys
import subprocess

# --- PAGE SETUP ---
st.set_page_config(page_title="AI School Timetable", page_icon="🏫", layout="wide")

st.title("🏫 AI School Timetable Dashboard")

# --- SIDEBAR: TEMPLATE & UPLOAD ---
st.sidebar.header("1. Data Setup")

template_df = pd.DataFrame({
    "teacher_name": ["Mr. Smith", "Ms. Davis", "Mr. Smith"],
    "subject_name": ["Math", "Physics", "Math"],
    "class_name": ["IX-A", "IX-A", "IX-B"],
    "weekly_period": [5, 4, 5]
})
csv_template = template_df.to_csv(index=False).encode('utf-8')

st.sidebar.download_button(
    label="📄 Download Blank Template",
    data=csv_template,
    file_name="timetable_format_template.csv",
    mime="text/csv"
)

uploaded_file = st.sidebar.file_uploader("2. Upload your CSV", type=["csv"])

# --- MAIN LOGIC ---
if uploaded_file is None:
    st.info("👆 Please upload a CSV file from the sidebar menu to begin.")
else:
    input_df = pd.read_csv(uploaded_file)
    input_df.to_csv("school_data.csv", index=False)
    
    with st.spinner("🧠 AI is calculating the perfect timetable... Please wait..."):
        
        process = subprocess.run([sys.executable, "main_engine.py"], capture_output=True, text=True)
        
        if process.returncode != 0:
            st.error("🚨 CRASH DETECTED IN main_engine.py!")
            st.code(process.stderr)
            st.stop()
            
        st.success("🎉 Your conflict-free schedule is ready!")
        
        if os.path.exists("final_timetable_result.csv"):
            result_df = pd.read_csv("final_timetable_result.csv")
            
            # --- 🚀 THE TRANSLATOR FIX 🚀 ---
            # Convert computer numbers (0, 1, 2) back into human days (Mon, Tue, Wed)
            day_mapping = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri'}
            if pd.api.types.is_numeric_dtype(result_df['Day']) or result_df['Day'].astype(str).str.isnumeric().all():
                result_df['Day'] = result_df['Day'].astype(int).map(day_mapping)
            
            # Convert computer periods (0, 1) into (Period 1, Period 2)
            if pd.api.types.is_numeric_dtype(result_df['Period']) or result_df['Period'].astype(str).str.isnumeric().all():
                result_df['Period'] = result_df['Period'].astype(int).apply(lambda x: f"Period {x+1}")
            # --------------------------------
            
            if st.sidebar.checkbox("🔍 Show Raw Engine Data"):
                st.write("### Raw Output from Engine")
                st.dataframe(result_df)
            
            class_col = 'Class' if 'Class' in result_df.columns else 'class_name'
            teacher_col = 'Teacher' if 'Teacher' in result_df.columns else 'teacher_name'
            
            st.sidebar.header("3. Filters")
            view_by = st.sidebar.selectbox("View Timetable By:", ["Class", "Teacher"])
            
            try:
                if view_by == "Class":
                    class_list = result_df[class_col].unique()
                    selected_class = st.sidebar.selectbox("Select Class:", class_list)
                    st.subheader(f"Viewing Schedule for Class: {selected_class}")
                    
                    display_df = result_df[result_df[class_col] == selected_class]
                    
                    if 'Subject' in result_df.columns and 'Teacher' in result_df.columns:
                        display_df['Display_Val'] = display_df['Subject'] + " (" + display_df['Teacher'] + ")"
                    elif 'subject_name' in result_df.columns and 'teacher_name' in result_df.columns:
                        display_df['Display_Val'] = display_df['subject_name'] + " (" + display_df['teacher_name'] + ")"
                    else:
                        display_df['Display_Val'] = display_df.iloc[:, -1]
                        
                    pivot_df = display_df.pivot(index='Period', columns='Day', values='Display_Val')
                    
                elif view_by == "Teacher":
                    teacher_list = result_df[teacher_col].unique()
                    selected_teacher = st.sidebar.selectbox("Select Teacher:", teacher_list)
                    st.subheader(f"Viewing Schedule for Teacher: {selected_teacher}")
                    
                    display_df = result_df[result_df[teacher_col] == selected_teacher]
                    
                    if 'Subject' in result_df.columns and 'Class' in result_df.columns:
                        display_df['Display_Val'] = display_df['Subject'] + " (" + display_df['Class'] + ")"
                    elif 'subject_name' in result_df.columns and 'class_name' in result_df.columns:
                        display_df['Display_Val'] = display_df['subject_name'] + " (" + display_df['class_name'] + ")"
                    else:
                        display_df['Display_Val'] = display_df.iloc[:, -1]
                        
                    pivot_df = display_df.pivot(index='Period', columns='Day', values='Display_Val')

                # Force the correct order for the grid
                days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
                days_present = [day for day in days_order if day in pivot_df.columns]
                pivot_df = pivot_df[days_present]
                pivot_df = pivot_df.fillna("-")
                
                # Display the beautiful grid
                st.table(pivot_df)
                
            except Exception as e:
                st.error("⚠️ The table couldn't be drawn.")
                st.write(f"Display Error: {e}")
        else:
            st.error("⚠️ The engine ran, but final_timetable_result.csv is missing.")