import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit.components.v1 as components
import google.generativeai as genai
import warnings
from supabase import create_client

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Survey Analyzer Pro", layout="wide")

# ==========================================
# ☁️ SUPABASE & THE PRIVATE VAULT
# ==========================================
@st.cache_resource
def init_supabase():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None
supabase = init_supabase()

def backup_survey_to_cloud(file_name, file_bytes):
    if supabase is None or st.session_state.user is None: return
    user_id = st.session_state.user.id
    try:
        supabase.storage.from_("user_vaults").upload(
            file=file_bytes,
            path=f"{user_id}/surveys/{file_name}",
            file_options={"upsert": "true"}
        )
    except Exception as e: pass

# ==========================================
# 🧠 SESSION STATE SAFETY CHECK
# ==========================================
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_uses' not in st.session_state: st.session_state.guest_uses = 0
if 'combo_count' not in st.session_state: st.session_state['combo_count'] = 1

# --- INJECT PRINT CSS ---
st.markdown("""
    <style>
    @media print {
        header {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="stFileUploader"] {display: none !important;}
        .stDownloadButton {display: none !important;}
        .stButton {display: none !important;}
        div.element-container { page-break-inside: avoid !important; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    }
    </style>
""", unsafe_allow_html=True)

LIKERT_MAP = {"5": "Strongly Agree", "4": "Agree", "3": "Neutral", "2": "Disagree", "1": "Strongly Disagree"}
REVERSE_MAP = {"Strongly Agree": "5", "Agree": "4", "Neutral": "3", "Uncertain": "3", "Disagree": "2", "Strongly Disagree": "1"}

def parse_system_report(df):
    questions = {}
    current_q = None
    for index, row in df.iterrows():
        val_0, val_2, val_5 = str(row[0]).strip() if pd.notna(row[0]) else "", str(row[2]).strip() if pd.notna(row[2]) else "", row[5] if pd.notna(row[5]) else np.nan
        if val_0 and val_0[0].isdigit() and "." in val_0[:3]:
            current_q = val_0
            questions[current_q] = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}
            continue
        if current_q and val_2 in ["5", "4", "3", "2", "1", "5.0", "4.0", "3.0", "2.0", "1.0"]:
            try: questions[current_q][str(int(float(val_2)))] = round(float(val_5), 2) if pd.notna(val_5) else 0.0
            except ValueError: pass
    return {q: data for q, data in questions.items() if sum(data.values()) > 0}

def parse_google_forms(df):
    questions = {}
    skip_cols = ['timestamp', 'time', 'email', 'name', 'id', 'roll', 'section']
    for col in df.columns:
        if any(skip in str(col).lower() for skip in skip_cols): continue
        counts = df[col].value_counts(dropna=True)
        total_responses = counts.sum()
        if total_responses == 0: continue
        q_data, valid_likert_found = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}, False
        for val, count in counts.items():
            val_str = str(val).strip()
            if val_str in REVERSE_MAP:
                q_data[REVERSE_MAP[val_str]] += count
                valid_likert_found = True
            elif val_str in ["5", "4", "3", "2", "1", "5.0", "4.0", "3.0", "2.0", "1.0"]:
                q_data[str(int(float(val_str)))] += count
                valid_likert_found = True
        if valid_likert_found:
            for k in q_data: q_data[k] = round((q_data[k] / total_responses) * 100, 2)
            questions[str(col)] = q_data
    return questions

def process_file(file):
    df = pd.read_excel(file)
    if len(df.columns) > 1 and "Unnamed" in str(df.columns[1]):
        file.seek(0)
        return parse_system_report(pd.read_excel(file, header=None))
    return parse_google_forms(df)

# ==========================================
# 🛑 FREEMIUM LIMIT CHECKER
# ==========================================
def check_survey_limits(num_responses, num_questions):
    if st.session_state.user is not None: return True
    if st.session_state.guest_uses >= 5:
        st.error("🚫 You have reached your 5 free trial uses. Please return to the main page to Register/Login.")
        return False
    if num_responses > 50 or num_questions > 10:
        st.error(f"🚫 Limit Exceeded: File has {num_responses} rows and {num_questions} columns. Free limit is 50x10. Register on Main Page for PRO.")
        return False
    return True

def create_table_and_chart(q_name, q_data, unique_key):
    table_data = [{"Option": k, "Response Type": LIKERT_MAP[k], "Percentage (%)": q_data[k]} for k in sorted(q_data.keys(), reverse=True)]
    df_table, df_chart = pd.DataFrame(table_data), pd.DataFrame(table_data)[pd.DataFrame(table_data)["Percentage (%)"] > 0]
    
    st.subheader(q_name)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(df_table, use_container_width=True, hide_index=True)
        safe_name = "".join([c for c in q_name if c.isalnum() or c==' ']).rstrip()[:30]
        if st.session_state.user is not None:
            st.download_button("📥 Download Table", data=df_table.to_csv(index=False).encode('utf-8'), file_name=f"{safe_name}.csv", mime="text/csv", key=f"dl_{unique_key}")
        else: st.caption("🔒 *Login to download table data*")
    with col2:
        if not df_chart.empty:
            fig = px.pie(df_chart, values='Percentage (%)', names='Response Type', color='Response Type',
                         color_discrete_map={"Strongly Agree": "#1f77b4", "Agree": "#2ca02c", "Neutral": "#ff7f0e", "Disagree": "#d62728", "Strongly Disagree": "#9467bd"})
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True, key=unique_key)
    st.divider()

def generate_ai_summary(api_key, topic_name, data):
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not available_models: return "❌ AI Error: Region restricted."
        chosen_model = available_models[0]
        for pref in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
            if pref in available_models:
                chosen_model = pref; break
                
        model = genai.GenerativeModel(chosen_model)
        prompt = f"""You are an Educational Data Analyst. Analyze survey results for: "{topic_name}".
        Data: Strongly Agree: {data['5']}%, Agree: {data['4']}%, Neutral: {data['3']}%, Disagree: {data['2']}%, Strongly Disagree: {data['1']}%
        Task: 1. Identify argument. 2. Logical conclusion. 3. Actionable recommendation. Max 3 paragraphs. Bold headings."""
        return model.generate_content(prompt).text
    except Exception as e: return f"❌ AI Error: {e}"

# --- MAIN UI ---
st.title("📊 Survey Analyzer Pro")

with st.sidebar:
    if st.session_state.user is None:
        st.warning("⚠️ **GUEST MODE**")
        st.write("Free limits: Max 50 responses & 10 questions. Downloads locked.")
        st.progress(st.session_state.guest_uses / 5.0, text=f"Free Uses: {st.session_state.guest_uses}/5")
    else:
        user_meta = st.session_state.user.user_metadata
        st.success(f"✅ **PRO USER:** {user_meta.get('institution_name', 'Institution')}")
    st.markdown("---")

try: SYSTEM_API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError): SYSTEM_API_KEY = None

api_key_input = SYSTEM_API_KEY
if not api_key_input:
    with st.sidebar:
        st.header("🧠 AI Settings")
        api_key_input = st.text_input("Gemini API Key", type="password")

uploaded_file = st.file_uploader("Upload Google/MS Forms Response Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_check = pd.read_excel(uploaded_file)
        uploaded_file.seek(0)
        
        if not check_survey_limits(df_check.shape[0], df_check.shape[1]): st.stop()
            
        if st.session_state.user is None and f"counted_{uploaded_file.name}" not in st.session_state:
            st.session_state.guest_uses += 1
            st.session_state[f"counted_{uploaded_file.name}"] = True

        parsed_data = process_file(uploaded_file)
        if not parsed_data: st.stop()
        
        # --- MAGIC VAULT BACKUP (SURVEYS) ---
        if st.session_state.user is not None:
            uploaded_file.seek(0)
            backup_survey_to_cloud(uploaded_file.name, uploaded_file.read())
        
        st.markdown("### 📥 Export Options")
        if st.session_state.user is not None:
            c1, c2 = st.columns(2)
            with c1:
                df_master = pd.DataFrame([{"Question": q, **{f"{LIKERT_MAP[k]} (%)": data[k] for k in ["5","4","3","2","1"]}} for q, data in parsed_data.items()])
                st.download_button("📥 Download Master Report (CSV)", data=df_master.to_csv(index=False).encode('utf-8'), file_name="Master.csv", mime="text/csv", type="primary", use_container_width=True)
            with c2:
                components.html("""<script>function triggerPrint() {window.parent.print();}</script><button onclick="triggerPrint()" style="background-color:#ff4b4b; color:white; border:none; border-radius:8px; padding: 10px 15px; font-weight: 600; cursor: pointer; width: 100%; height: 42px; font-size: 16px;">🖨️ Print Dashboard to PDF</button>""", height=50)
        else:
            st.error("🔒 **PRO Feature:** Register or Login on the Main Page to download reports.")
            
        st.divider()

        tab1, tab2 = st.tabs(["📋 Individual Questions", "🔗 Custom Combiner & AI"])
        
        with tab1:
            st.header("Individual Question Results")
            for i, (q_name, q_data) in enumerate(parsed_data.items()): create_table_and_chart(q_name, q_data, unique_key=f"chart_tab1_{i}")
                
        with tab2:
            st.header("Dynamic Combiner & AI Analysis")
            if st.button("➕ Add Another Combination"): st.session_state['combo_count'] += 1
            st.divider()
            
            combo_configs = []
            for i in range(st.session_state['combo_count']):
                with st.container(border=True):
                    c_name = st.text_input("Label:", value=f"Combined Topic {i + 1}", key=f"name_{i}")
                    c_qs = st.multiselect("Select Questions:", options=list(parsed_data.keys()), key=f"qs_{i}")
                    combo_configs.append({"name": c_name, "questions": c_qs})
            
            if st.button("🚀 Generate All Combined Charts", type="primary"):
                st.markdown("---")
                for i, config in enumerate(combo_configs):
                    if config["questions"]:
                        combined_data = {k: sum(parsed_data[q][k] for q in config["questions"]) / len(config["questions"]) for k in ["5", "4", "3", "2", "1"]}
                        combined_data = {k: round(v, 2) for k, v in combined_data.items()}
                        create_table_and_chart(config["name"], combined_data, unique_key=f"chart_combo_{i}")
                        if api_key_input:
                            with st.expander(f"✨ AI Executive Summary for: {config['name']}", expanded=True):
                                with st.spinner("Analyzing data..."):
                                    st.markdown(generate_ai_summary(api_key_input, config["name"], combined_data))
                        else: st.info("💡 Enter your Gemini API key in the sidebar for AI summaries.")
    except Exception as e: st.error(f"Error processing file: {e}")