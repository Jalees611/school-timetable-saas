import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings

# Ignore openpyxl warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Survey Analyzer Pro", layout="wide")

# Custom dictionary to map number scores to Likert text
LIKERT_MAP = {
    "5": "Strongly Agree",
    "4": "Agree",
    "3": "Neutral",
    "2": "Disagree",
    "1": "Strongly Disagree"
}

def parse_survey_excel(file):
    """Parses the specific format of the Course Evaluation Excel file."""
    df = pd.read_excel(file, header=None)
    questions = {}
    current_q = None

    for index, row in df.iterrows():
        # Clean column values safely
        val_0 = str(row[0]).strip() if pd.notna(row[0]) else ""
        val_2 = str(row[2]).strip() if pd.notna(row[2]) else ""
        val_5 = row[5] if pd.notna(row[5]) else np.nan
        
        # Identify a question row (Starts with a number and a dot, e.g., "02.")
        if val_0 and val_0[0].isdigit() and "." in val_0[:3]:
            current_q = val_0
            # Initialize with default 0.0 for ALL options
            questions[current_q] = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}
            continue
            
        # If we are inside a question, capture the scores
        # We check against "5.0" and "5" to handle Excel formatting variations
        if current_q and val_2 in ["5", "4", "3", "2", "1", "5.0", "4.0", "3.0", "2.0", "1.0"]:
            try:
                clean_key = str(int(float(val_2))) # Forces "5.0" to "5"
                pct = round(float(val_5), 2) if pd.notna(val_5) else 0.0
                questions[current_q][clean_key] = pct
            except ValueError:
                pass

    # Filter out questions that have exactly 0.0 for all Likert options (like attendance)
    filtered_questions = {
        q: data for q, data in questions.items() 
        if sum(data.values()) > 0
    }
    
    return filtered_questions

def create_table_and_chart(q_name, q_data):
    """Generates the UI for a single question (Table + Pie Chart)"""
    # 1. Create the structured Dataframe (always contains 5 rows)
    table_data = []
    for key in sorted(q_data.keys(), reverse=True): # 5, 4, 3, 2, 1
        table_data.append({
            "Option": key,
            "Response Type": LIKERT_MAP.get(key, "Unknown"),
            "Percentage (%)": q_data[key]
        })
    df_table = pd.DataFrame(table_data)
    
    # 2. Filter out zeros for the visual Pie Chart
    df_chart = df_table[df_table["Percentage (%)"] > 0]
    
    st.subheader(q_name)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.dataframe(df_table, use_container_width=True, hide_index=True)
        
    with col2:
        if not df_chart.empty:
            fig = px.pie(
                df_chart, 
                values='Percentage (%)', 
                names='Response Type',
                color='Response Type',
                color_discrete_map={
                    "Strongly Agree": "#1f77b4", # Blue
                    "Agree": "#2ca02c",          # Green
                    "Neutral": "#ff7f0e",        # Orange
                    "Disagree": "#d62728",       # Red
                    "Strongly Disagree": "#9467bd" # Purple
                }
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid data to plot.")
    st.divider()

# --- MAIN UI ---
st.title("📊 Survey Analyzer Pro")

uploaded_file = st.file_uploader("Upload Google/MS Forms Response Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Load and Parse the data
        parsed_data = parse_survey_excel(uploaded_file)
        
        if not parsed_data:
            st.error("Could not find valid survey data. Please ensure the Excel format matches the system report.")
            st.stop()
            
        st.success(f"Successfully loaded {len(parsed_data)} Likert-scale questions!")
        
        # --- TABS ---
        tab1, tab2 = st.tabs(["📋 Individual Questions", "🔗 Custom Combiner"])
        
        with tab1:
            st.header("Individual Question Results")
            for q_name, q_data in parsed_data.items():
                create_table_and_chart(q_name, q_data)
                
        with tab2:
            st.header("Combine Questions")
            st.markdown("Select multiple questions below to calculate their average and generate a combined result.")
            
            combo_name = st.text_input("Label for Combined Chart:", "Overall Satisfaction")
            selected_qs = st.multiselect("Select Questions to Combine:", options=list(parsed_data.keys()))
            
            if st.button("Generate Combined Chart") and selected_qs:
                # Calculate the exact mathematical average of the selected questions
                combined_data = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}
                num_qs = len(selected_qs)
                
                for q in selected_qs:
                    for key in combined_data.keys():
                        combined_data[key] += parsed_data[q][key]
                
                # Average them out
                for key in combined_data.keys():
                    combined_data[key] = round(combined_data[key] / num_qs, 2)
                
                # Render it
                st.markdown("---")
                create_table_and_chart(combo_name, combined_data)

    except Exception as e:
        st.error(f"Error processing file: {e}")