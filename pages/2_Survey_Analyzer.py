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
# 🎨 MATERIAL DESIGN CSS, PADDING FIX & PRINT HACK
# ==========================================
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; } /* PULLS CONTENT UP */
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background-color: white; padding: 1.5rem; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    @media print {
        header, [data-testid="stSidebar"], [data-testid="stFileUploader"], .stDownloadButton, .stButton {display: none !important;}
        div.element-container { page-break-inside: avoid !important; }
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    }
    </style>
""", unsafe_allow_html=True)

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
    try:
        supabase.storage.from_("user_vaults").upload(
            file=file_bytes, path=f"{st.session_state.user.id}/surveys/{file_name}", file_options={"upsert": "true"}
        )
    except: pass

def restore_survey_from_cloud():
    if supabase is None or st.session_state.user is None: return None
    try:
        files = supabase.storage.from_("user_vaults").list(f"{st.session_state.user.id}/surveys")
        if files and len(files) > 0:
            file_name = files[0]['name']
            data = supabase.storage.from_("user_vaults").download(f"{st.session_state.user.id}/surveys/{file_name}")
            with open(file_name, 'wb') as f: f.write(data)
            return file_name
    except: return None
    return None

# ==========================================
# 🧠 STATE & LIKERT LOGIC
# ==========================================
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_uses' not in st.session_state: st.session_state.guest_uses = 0
if 'combo_count' not in st.session_state: st.session_state['combo_count'] = 1
if 'restored_survey' not in st.session_state: st.session_state['restored_survey'] = None

LIKERT_MAP = {"5": "Strongly Agree", "4": "Agree", "3": "Neutral", "2": "Disagree", "1": "Strongly Disagree"}
REVERSE_MAP = {"Strongly Agree": "5", "Agree": "4", "Neutral": "3", "Uncertain": "3", "Disagree": "2", "Strongly Disagree": "1"}

def parse_system_report(df):
    questions = {}
    current_q = None
    for index, row in df.iterrows():
        val_0, val_2, val_5 = str(row[0]).strip() if pd.notna(row[0]) else "", str(row[2]).strip() if pd.notna(row[2]) else "", row[5] if pd.notna(row[5]) else np.nan
        if val_0 and val_0[0].isdigit() and "." in val_0[:3]:
            current_q = val_0; questions[current_q] = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}; continue
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
        if counts.sum() == 0: continue
        q_data, valid = {"5": 0.0, "4": 0.0, "3": 0.0, "2": 0.0, "1": 0.0}, False
        for val, count in counts.items():
            val_str = str(val).strip()
            if val_str in REVERSE_MAP: q_data[REVERSE_MAP[val_str]] += count; valid = True
            elif val_str in ["5", "4", "3", "2", "1", "5.0", "4.0", "3.0", "2.0", "1.0"]: q_data[str(int(float(val_str)))] += count; valid = True
        if valid:
            for k in q_data: q_data[k] = round((q_data[k] / counts.sum()) * 100, 2)
            questions[str(col)] = q_data
    return questions

def process_file(file_obj_or_path):
    df = pd.read_excel(file_obj_or_path)
    if len(df.columns) > 1 and "Unnamed" in str(df.columns[1]):
        if hasattr(file_obj_or_path, 'seek'): file_obj_or_path.seek(0)
        return parse_system_report(pd.read_excel(file_obj_or_path, header=None))
    return parse_google_forms(df)

def check_survey_limits(num_responses, num_questions):
    if st.session_state.user is not None: return True
    if st.session_state.guest_uses >= 5: st.error("🚫 Trial limit reached."); return False
    if num_responses > 50 or num_questions > 10: st.error(f"🚫 Limit Exceeded: Free limit is 50x10."); return False
    return True

def create_table_and_chart(q_name, q_data, unique_key):
    table_data = [{"Option": k, "Response": LIKERT_MAP[k], "%": q_data[k]} for k in sorted(q_data.keys(), reverse=True)]
    df_table, df_chart = pd.DataFrame(table_data), pd.DataFrame(table_data)[pd.DataFrame(table_data)["%"] > 0]
    
    with st.container():
        st.markdown(f"#### {q_name}")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.dataframe(df_table, use_container_width=True, hide_index=True)
            if st.session_state.user: st.download_button("📥 CSV", data=df_table.to_csv(index=False).encode('utf-8'), file_name=f"Chart.csv", key=f"dl_{unique_key}")
        with c2:
            if not df_chart.empty:
                fig = px.pie(df_chart, values='%', names='Response', color='Response', color_discrete_map={"Strongly Agree": "#1f77b4", "Agree": "#2ca02c", "Neutral": "#ff7f0e", "Disagree": "#d62728", "Strongly Disagree": "#9467bd"})
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True, key=unique_key)

def generate_ai_summary(api_key, topic_name, data):
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not models: return "❌ AI Error: Region restricted."
        model = genai.GenerativeModel(models[0])
        prompt = f"""Educational Data Analyst. Analyze survey results for: "{topic_name}". Data: Strongly Agree: {data['5']}%, Agree: {data['4']}%, Neutral: {data['3']}%, Disagree: {data['2']}%, Strongly Disagree: {data['1']}%. 1. Identify argument. 2. Conclusion. 3. Recommendation. Max 3 paragraphs. Bold headings."""
        return model.generate_content(prompt).text
    except Exception as e: return f"❌ AI Error: {e}"

# ==========================================
# 🏢 MAIN UI & INSTRUCTION BANNER
# ==========================================
with st.sidebar:
    if st.session_state.user is None:
        st.warning("⚠️ GUEST MODE")
        st.progress(st.session_state.guest_uses / 5.0, text=f"Free Uses: {st.session_state.guest_uses}/5")
    else:
        st.success(f"✅ PRO USER")
        if st.button("☁️ Load Saved Workspace"):
            with st.spinner("Pulling from vault..."):
                restored = restore_survey_from_cloud()
                if restored: st.session_state['restored_survey'] = restored; st.success("Loaded!")
                else: st.warning("No saved data found.")
    st.markdown("---")

try: SYSTEM_API_KEY = st.secrets["GEMINI_API_KEY"]
except: SYSTEM_API_KEY = None

api_key_input = SYSTEM_API_KEY
if not api_key_input:
    with st.sidebar:
        st.header("🧠 AI Settings")
        api_key_input = st.text_input("Gemini API Key", type="password")

with st.expander("📖 Application Guide & Account Limits (Click to expand)", expanded=False):
    st.markdown("""
    ### 🛡️ User Tiers
    * 🟡 **Guest Mode:** Maximum of 5 free trial uses. Data is limited to 50 rows (responses) and 10 columns (questions). PDF and CSV downloads are locked.
    * 🟢 **PRO Mode:** Unlimited uses, massive dataset support, Gemini AI text summaries unlocked, and Print-to-PDF enabled. (Register for free on the sidebar).

    ### 🤖 AI Survey Rules
    * **Likert Processing:** The engine automatically detects standard 5-point scales (Strongly Agree to Strongly Disagree) and ignores irrelevant columns like Timestamps or Names.
    * **Dynamic Combiner:** You can select multiple related questions to merge them into a single "Topic" metric.
    * **Argumentative AI:** If you input a Gemini API Key, the AI will evaluate combined topics to determine the core argument, synthesize a conclusion, and provide actionable management recommendations.
    """)

st.title("📊 Survey Analyzer Pro")

with st.container():
    st.markdown("### 📥 Upload Data")
    uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    active_file = uploaded_file or st.session_state.get('restored_survey')

    if active_file:
        try:
            if isinstance(active_file, str): df_check = pd.read_excel(active_file)
            else:
                active_file.seek(0)
                df_check = pd.read_excel(active_file)
                active_file.seek(0)
            
            if not check_survey_limits(df_check.shape[0], df_check.shape[1]): st.stop()
                
            file_id = active_file if isinstance(active_file, str) else active_file.name
            if st.session_state.user is None and f"counted_{file_id}" not in st.session_state:
                st.session_state.guest_uses += 1
                st.session_state[f"counted_{file_id}"] = True

            parsed_data = process_file(active_file)
            if not parsed_data: st.stop()
            
            if st.session_state.user is not None and uploaded_file:
                uploaded_file.seek(0)
                backup_survey_to_cloud(uploaded_file.name, uploaded_file.read())
                st.session_state['restored_survey'] = uploaded_file.name
            
            st.markdown("### 📥 Global Export")
            if st.session_state.user:
                c1, c2 = st.columns(2)
                with c1:
                    df_master = pd.DataFrame([{"Question": q, **{f"{LIKERT_MAP[k]} (%)": data[k] for k in ["5","4","3","2","1"]}} for q, data in parsed_data.items()])
                    st.download_button("📥 Master Report (CSV)", df_master.to_csv(index=False).encode('utf-8'), "Master.csv", "text/csv", use_container_width=True)
                with c2:
                    components.html("""<script>function triggerPrint() {window.parent.print();}</script><button onclick="triggerPrint()" style="background-color:#0d47a1; color:white; border:none; border-radius:8px; padding: 10px; cursor: pointer; width: 100%; font-size: 16px;">🖨️ Print to PDF</button>""", height=50)
            else: st.error("🔒 Login to export Master CSV & PDF.")
                
            tab1, tab2 = st.tabs(["📋 Visuals", "🔗 Combiner & AI"])
            
            with tab1:
                for i, (q_name, q_data) in enumerate(parsed_data.items()): create_table_and_chart(q_name, q_data, f"c_{i}")
                    
            with tab2:
                with st.container():
                    st.markdown("### 🤖 Dynamic AI Summaries")
                    if st.button("➕ Add Combination"): st.session_state['combo_count'] += 1
                    
                    combos = []
                    for i in range(st.session_state['combo_count']):
                        st.markdown(f"**Combination {i+1}**")
                        c_name = st.text_input("Topic Label:", value=f"Topic {i + 1}", key=f"n_{i}")
                        c_qs = st.multiselect("Select Questions:", options=list(parsed_data.keys()), key=f"q_{i}")
                        combos.append({"name": c_name, "questions": c_qs})
                        st.divider()
                
                if st.button("🚀 Run AI Analysis", type="primary"):
                    for i, config in enumerate(combos):
                        if config["questions"]:
                            cmb_data = {k: round(sum(parsed_data[q][k] for q in config["questions"]) / len(config["questions"]), 2) for k in ["5", "4", "3", "2", "1"]}
                            create_table_and_chart(config["name"], cmb_data, f"cmb_{i}")
                            if api_key_input:
                                with st.container():
                                    st.markdown(f"#### ✨ AI Insight: {config['name']}")
                                    with st.spinner("Gemini is analyzing..."):
                                        st.write(generate_ai_summary(api_key_input, config["name"], cmb_data))
                            else: st.info("🔑 Add Gemini Key in sidebar for text summary.")
        except Exception as e: st.error(f"Error processing: {e}")