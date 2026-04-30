import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit.components.v1 as components
import warnings

# Ignore openpyxl warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Survey Analyzer Pro", layout="wide")

# --- INJECT PRINT CSS ---
# This CSS automatically hides the UI elements (buttons, uploaders, sidebars) when printing
st.markdown("""
    <style>
    @media print {
        header {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="stFileUploader"] {display: none !important;}
        .stDownloadButton {display: none !important;}
        .stButton {display: none !important;}
        
        /* Ensure charts and tables don't get cut in half across pages */
        div.element-container { page-break-inside: avoid !important; }
        
        /* Force backgrounds to print correctly */
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

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
    """Generates the UI for a single question (Table + Pie Chart + Individual Download)"""
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
        
        csv_data = df_table.to_csv(index=False).encode('utf-8')
        safe_name = "".join([c for c in q_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()[:30]
        
        st.download_button(
            label="📥 Download Table",
            data=csv_data,
            file_name=f"{safe_name}_results.csv",
            mime="text/csv",
            key=f"dl_{unique_key}" 
        )
        
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
        
        # --- EXPORT & PRINT CONTROLS ---
        st.markdown("### 📥 Export Options")
        
        c1, c2 = st.columns(2)
        with c1:
            # 1. Excel/CSV Download
            master_rows = []
            for q, data in parsed_data.items():
                row = {"Question": q}
                for key in ["5", "4", "3", "2", "1"]:
                    row[f"{LIKERT_MAP[key]} (%)"] = data[key]
                master_rows.append(row)
                
            df_master = pd.DataFrame(master_rows)
            master_csv = df_master.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Master Report (CSV)",
                data=master_csv,
                file_name="Master_Survey_Report.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
            
        with c2:
            # 2. Print to PDF Button (Injects Javascript to trigger browser print)
            components.html(
                """
                <script>
                function triggerPrint() {
                    window.parent.print();
                }
                </script>
                <button onclick="triggerPrint()" style="background-color:#ff4b4b; color:white; border:none; border-radius:8px; padding: 10px 15px; font-weight: 600; font-family: 'Source Sans Pro', sans-serif; cursor: pointer; width: 100%; height: 42px; font-size: 16px;">
                🖨️ Print Dashboard to PDF
                </button>
                """,
                height=50
            )
            
        st.divider()
        # -----------------------------

        tab1, tab2 = st.tabs(["📋 Individual Questions", "🔗 Custom Combiner"])
        
        with tab1:
            st.header("Individual Question Results")
            for i, (q_name, q_data) in enumerate(parsed_data.items()):
                create_table_and_chart(q_name, q_data, unique_key=f"chart_tab1_{i}")
                
        with tab2:
            st.header("Dynamic Combiner")
            st.markdown("Create multiple custom combinations. Click the **+** button to add more sections.")
            
            if st.button("➕ Add Another Combination"):
                st.session_state['combo_count'] += 1

            st.divider()
            
            combo_configs = []
            
            for i in range(st.session_state['combo_count']):
                with st.container(border=True):
                    st.markdown(f"**Combination {i + 1}**")
                    c_name = st.text_input(f"Label:", value=f"Combined Topic {i + 1}", key=f"name_{i}")
                    c_qs = st.multiselect(f"Select Questions:", options=list(parsed_data.keys()), key=f"qs_{i}")
                    
                    combo_configs.append({"name": c_name, "questions": c_qs})
            
            if st.button("🚀 Generate All Combined Charts", type="primary"):
                st.markdown("---")
                st.header("📊 Your Combined Results")
                
                for i, config in enumerate(combo_configs):
                    if config["questions"]:
                        combined_data = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}
                        num_qs = len(config["questions"])
                        
                        for q in config["questions"]:
                            for key in combined_data.keys():
                                combined_data[key] += parsed_data[q][key]
                        
                        for key in combined_data.keys():
                            combined_data[key] = round(combined_data[key] / num_qs, 2)
                        
                        create_table_and_chart(config["name"], combined_data, unique_key=f"chart_combo_{i}")
                    else:
                        st.warning(f"Skipped '{config['name']}' because no questions were selected.")

    except Exception as e:
        st.error(f"Error processing file: {e}")