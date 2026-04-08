import streamlit as st
import pandas as pd
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="AI School Timetable", page_icon="🏫", layout="wide")

st.title("🏫 AI School Timetable Dashboard")

# --- SIDEBAR: TEMPLATE & UPLOAD ---
st.sidebar.header("1. Data Setup")
st.sidebar.info("Upload your school's data to generate a custom timetable.")

# Generate a safe, dummy template on the fly using YOUR engine's required column names
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

# The File Uploader
uploaded_file = st.sidebar.file_uploader("2. Upload your CSV", type=["csv"])

# --- MAIN LOGIC ---
if uploaded_file is None:
    # What the user sees when they first visit the site
    st.info("👆 Please upload a CSV file from the sidebar menu to begin.")
    st.write("### How it works:")
    st.write("1. Download the template from the sidebar to see the required format.")
    st.write("2. Fill in your own school's Classes, Teachers, and Subjects in Excel.")
    st.write("3. Save as a CSV and upload it here to generate your conflict-free schedule!")

else:
    # What happens AFTER they upload a file
    
    # 1. Read their uploaded file
    input_df = pd.read_csv(uploaded_file)
    
    # 2. Overwrite the default 'school_data.csv' so your engine uses the NEW data
    input_df.to_csv("school_data.csv", index=False)
    
    # 3. Run the AI Engine
    with st.spinner("🧠 AI is calculating the perfect conflict-free timetable... Please wait..."):
        
        # This triggers your main_engine.py exactly like you would in the terminal
        os.system("python main_engine.py") 
        
        st.success("🎉 Your conflict-free schedule is ready!")
        
        # 4. Display the newly generated results!
        if os.path.exists("final_timetable_result.csv"):
            result_df = pd.read_csv("final_timetable_result.csv")
            
            # Create a combined display column (Subject + Teacher OR Subject + Class)
            # This handles different output formats from your engine
            if 'Subject' in result_df.columns and 'Teacher' in result_df.columns:
                 result_df['Subject_Teacher'] = result_df['Subject'] + " (" + result_df['Teacher'] + ")"
                 result_df['Subject_Class'] = result_df['Subject'] + " (" + result_df['Class'] + ")"
            elif 'subject_name' in result_df.columns and 'teacher_name' in result_df.columns:
                 result_df['Subject_Teacher'] = result_df['subject_name'] + " (" + result_df['teacher_name'] + ")"
                 result_df['Subject_Class'] = result_df['subject_name'] + " (" + result_df['class_name'] + ")"
                 
            # Find the correct column names for filtering
            class_col = 'Class' if 'Class' in result_df.columns else 'class_name'
            teacher_col = 'Teacher' if 'Teacher' in result_df.columns else 'teacher_name'
            
            # --- FILTERS & DISPLAY ---
            st.sidebar.header("3. Filters")
            
            # Added "Teacher" option here!
            view_by = st.sidebar.selectbox("View Timetable By:", ["Class", "Teacher"])
            
            if view_by == "Class":
                class_list = result_df[class_col].unique()
                selected_class = st.sidebar.selectbox("Select Class:", class_list)
                
                st.subheader(f"Viewing Schedule for Class: {selected_class}")
                
                # Filter data for the selected class
                display_df = result_df[result_df[class_col] == selected_class]
                
                # Show Subject and Teacher in the grid
                value_col = 'Subject_Teacher' if 'Subject_Teacher' in display_df.columns else display_df.columns[-1]
                
                pivot_df = display_df.pivot(index='Period', columns='Day', values=value_col)
                
            elif view_by == "Teacher":
                teacher_list = result_df[teacher_col].unique()
                selected_teacher = st.sidebar.selectbox("Select Teacher:", teacher_list)
                
                st.subheader(f"Viewing Schedule for Teacher: {selected_teacher}")
                
                # Filter data for the selected teacher
                display_df = result_df[result_df[teacher_col] == selected_teacher]
                
                # Show Subject and Class in the grid
                value_col = 'Subject_Class' if 'Subject_Class' in display_df.columns else display_df.columns[-1]
                
                pivot_df = display_df.pivot(index='Period', columns='Day', values=value_col)

            # Keep days in the correct order for a 5-day school week
            days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
            days_present = [day for day in days_order if day in pivot_df.columns]
            pivot_df = pivot_df[days_present]
            
            # Replace empty slots with a dash instead of NaN
            pivot_df = pivot_df.fillna("-")
            
            # Display the beautiful grid
            st.table(pivot_df)
        else:
            st.error("⚠️ The engine ran, but couldn't create the final_timetable_result.csv file. Check your data formatting.")