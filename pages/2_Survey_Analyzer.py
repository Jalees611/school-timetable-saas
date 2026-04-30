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
        val_0 = str(row[0]).strip() if pd.notna(row[0]) else ""
        val_2 = str(row[2]).strip() if pd.notna(row[2]) else ""
        val_5 = row[5] if pd.notna(row[5]) else np.nan
        
        if val_0 and val_0[0].isdigit() and "." in val_0[:3]:
            current_q = val_0
            questions[current_q] = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}
            continue
            
        if current_q and val_2 in ["5", "4", "3", "2", "1", "5.0", "4.0", "3.0", "2.0", "1.0"]:
            try:
                clean_key = str(int(float(val_2))) 
                pct = round(float(val_5), 2) if pd.notna(val_5) else 0.0
                questions[current_q][clean_key] = pct
            except ValueError:
                pass

    filtered_questions = {
        q: data for q, data in questions.items() 
        if sum(data.values()) > 0
    }
    return filtered_questions

def create_table_and_chart(q_name, q_data, unique_key):
    """Generates the UI for a single question (Table + Pie Chart)"""
    table_data = []
    for key in sorted(q_data.keys(), reverse=True):
        table_data.append({
            "Option": key,
            "Response Type": LIKERT_MAP.get(key, "Unknown"),
            "Percentage (%)": q_data[key]
        })
    df_table = pd.DataFrame(table_data)
    
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
                    "Strongly Agree": "#1f77b4",
                    "Agree": "#2ca02c",
                    "Neutral": "#ff7f0e",
                    "Disagree": "#d62728",
                    "Strongly Disagree": "#9467bd"
                }
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True, key=unique_key)
        else:
            st.info("No valid data to plot.")
    st.divider()

# --- MAIN UI ---
st.title("📊 Survey Analyzer Pro")

# Initialize session state for dynamic combiners
if 'combo_count' not in st.session_state:
    st.session_state['combo_count'] = 1

uploaded_file = st.file_uploader("Upload Google/MS Forms Response Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        parsed_data = parse_survey_excel(uploaded_file)
        
        if not parsed_data:
            st.error("Could not find valid survey data. Please ensure the Excel format matches the system report.")
            st.stop()
            
        st.success(f"Successfully loaded {len(parsed_data)} Likert-scale questions!")
        
        tab1, tab2 = st.tabs(["📋 Individual Questions", "🔗 Custom Combiner"])
        
        with tab1:
            st.header("Individual Question Results")
            for i, (q_name, q_data) in enumerate(parsed_data.items()):
                create_table_and_chart(q_name, q_data, unique_key=f"chart_tab1_{i}")
                
        with tab2:
            st.header("Dynamic Combiner")
            st.markdown("Create multiple custom combinations. Click the **+** button to add more sections.")
            
            # The "+" Button to add more sections
            if st.button("➕ Add Another Combination"):
                st.session_state['combo_count'] += 1

            st.divider()
            
            # Create a list to store user inputs
            combo_configs = []
            
            # Loop to generate the UI based on how many combiners the user wants
            for i in range(st.session_state['combo_count']):
                with st.container(border=True): # Adds a nice border around each section
                    st.markdown(f"**Combination {i + 1}**")
                    c_name = st.text_input(f"Label:", value=f"Combined Topic {i + 1}", key=f"name_{i}")
                    c_qs = st.multiselect(f"Select Questions:", options=list(parsed_data.keys()), key=f"qs_{i}")
                    
                    # Store their choices in our list
                    combo_configs.append({"name": c_name, "questions": c_qs})
            
            # The Master Generation Button
            if st.button("🚀 Generate All Combined Charts", type="primary"):
                st.markdown("---")
                st.header("📊 Your Combined Results")
                
                # Loop through all configured combiners
                for i, config in enumerate(combo_configs):
                    if config["questions"]: # Only generate if they actually selected questions
                        combined_data = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}
                        num_qs = len(config["questions"])
                        
                        for q in config["questions"]:
                            for key in combined_data.keys():
                                combined_data[key] += parsed_data[q][key]
                        
                        # Average them out
                        for key in combined_data.keys():
                            combined_data[key] = round(combined_data[key] / num_qs, 2)
                        
                        create_table_and_chart(config["name"], combined_data, unique_key=f"chart_combo_{i}")
                    else:
                        st.warning(f"Skipped '{config['name']}' because no questions were selected.")

    except Exception as e:
        st.error(f"Error processing file: {e}")