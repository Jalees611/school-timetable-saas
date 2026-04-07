import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="AI School Timetable", layout="wide")

st.title("🏫 AI School Timetable Dashboard")
st.subheader("Your conflict-free schedule is ready!")

try:
    if not os.path.exists("final_timetable_result.csv"):
        st.error("Please run your 'main_engine.py' first!")
    else:
        df = pd.read_csv("final_timetable_result.csv")
        
        st.sidebar.header("Filters")
        view_type = st.sidebar.selectbox("View Timetable By:", ["Class", "Teacher"])
        
        if view_type == "Class":
            selected = st.sidebar.selectbox("Select Class:", sorted(df['Class'].unique()))
            filtered_df = df[df['Class'] == selected]
            # Group parallel subjects for the same period/day
            filtered_df = filtered_df.groupby(['Day', 'Period']).agg({
                'Subject': lambda x: ' / '.join(x),
                'Teacher': lambda x: ' & '.join(x)
            }).reset_index()
            filtered_df['display'] = filtered_df['Subject'] + " (" + filtered_df['Teacher'] + ")"
        else:
            selected = st.sidebar.selectbox("Select Teacher:", sorted(df['Teacher'].unique()))
            filtered_df = df[df['Teacher'] == selected]
            filtered_df['display'] = filtered_df['Subject'] + " (" + filtered_df['Class'] + ")"

        # Create Grid
        pivot_df = filtered_df.pivot(index='Period', columns='Day', values='display')
        pivot_df = pivot_df.reindex(index=range(1, 9), columns=range(1, 6)).fillna("-")
        pivot_df.columns = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        pivot_df.index = [f"Period {i}" for i in range(1, 9)]

        st.write(f"### Viewing Schedule for: **{selected}**")
        st.table(pivot_df)
        
except Exception as e:
    st.error(f"Error loading dashboard: {e}")