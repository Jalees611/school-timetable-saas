import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable
from supabase import create_client

st.set_page_config(page_title="Smart Timetable AI", page_icon="📅", layout="wide")

# ==========================================
# 🎨 CUSTOM THEME & PADDING FIX
# ==========================================
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background-color: white; padding: 1.5rem; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e0e0e0; }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    .stAlert { border-radius: 12px; border: none; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 AUTHENTICATION & SAAS TIER LOGIC
# ==========================================
if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("🔒 Please log in or register on the Home page to access the Timetable Generator.")
    st.page_link("Home.py", label="Go to Home Page", icon="🏠")
    st.stop()

PUBLIC_DOMAINS = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'aol.com']

def get_user_tier():
    if st.session_state.get('is_pro', False): return "Pro"
    email_domain = st.session_state.user.email.split('@')[1].lower() if st.session_state.user.email else ""
    if any(domain in email_domain for domain in PUBLIC_DOMAINS): return "Guest"
    return "Standard"

user_tier = get_user_tier()

if user_tier == "Pro":
    MAX_GENS, MAX_CLASSES, MAX_TEACHERS = float('inf'), float('inf'), float('inf')
    CAN_VAULT, CAN_EXPORT = True, True
elif user_tier == "Standard":
    MAX_GENS, MAX_CLASSES, MAX_TEACHERS = 15, 15, 30
    CAN_VAULT, CAN_EXPORT = True, False
else: # Guest
    MAX_GENS, MAX_CLASSES, MAX_TEACHERS = 5, 5, 20
    CAN_VAULT, CAN_EXPORT = False, False

if 'timetable_usage' not in st.session_state: st.session_state.timetable_usage = 0
if 'timetable_ready' not in st.session_state: st.session_state.timetable_ready = False

# ==========================================
# ☁️ SUPABASE & THE PRIVATE VAULT
# ==========================================
@st.cache_resource
def init_supabase():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None
supabase = init_supabase()

def backup_to_cloud(file_name, folder="timetables"):
    if supabase is None or st.session_state.user is None: return
    try:
        if os.path.exists(file_name):
            with open(file_name, 'rb') as f:
                supabase.storage.from_("user_vaults").upload(
                    file=f.read(), path=f"{st.session_state.user.id}/{folder}/{file_name}",
                    file_options={"upsert": "true"}
                )
    except: pass

def increment_usage_count():
    if st.session_state.user is None: return
    try:
        res = supabase.table("profiles").select("usage_count").eq("id", st.session_state.user.id).execute()
        if res.data:
            new_count = res.data[0].get("usage_count", 0) + 1
            supabase.table("profiles").update({"usage_count": new_count}).eq("id", st.session_state.user.id).execute()
    except: pass

# ==========================================
# 🧠 HELPERS, LOGIC & CSV SANITIZER
# ==========================================
def style_timetable(df):
    def get_colors(val):
        if val == "---" or pd.isna(val): return 'background-color: #ffffff; color: #d3d3d3;'
        colors = ['#e3f2fd', '#fffde7', '#f1f8e9', '#fce4ec', '#f3e5f5', '#efebe9']
        bg_color = colors[ord(str(val)[0]) % len(colors)]
        return f'background-color: {bg_color}; color: #0d47a1; font-weight: bold; border: 1px solid #bbdefb;'
    return df.style.applymap(get_colors)

def clear_old_files():
    for f in ['school_data.csv', 'workload.csv', 'resources.csv', 'restrictions.csv']:
        if os.path.exists(f): 
            try: os.remove(f)
            except: pass

def read_csv_safe(uploaded_file):
    uploaded_file.seek(0)
    try:
        return pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding='cp1252')

def save_file(uploaded_file, name):
    df = read_csv_safe(uploaded_file)
    df.to_csv(name, index=False, encoding='utf-8')

@st.cache_data
def get_template(mode):
    if mode == "school": df = pd.DataFrame({"teacher_name": ["John Doe"], "subject_name": ["Maths"], "class_name": ["9-A"], "weekly_period": [6], "institutiontype": ["School"]})
    elif mode == "college": df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "subject_name": ["Ecology"], "class_name": ["BS 2024"], "weekly_period": [3], "required_resource_type": ["classroom"], "institutiontype": ["College"]})
    elif mode == "res": df = pd.DataFrame({"resource_name": ["CL-1"], "resource_type": ["classroom"]})
    else: df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "day": ["Mon"], "period": ["Period 2"], "restriction_type": ["Unavailable"]})
    return df.to_csv(index=False).encode('utf-8')

def check_saas_limits(df):
    if st.session_state.timetable_usage >= MAX_GENS:
        st.error(f"🚫 **{user_tier} Tier Limit:** You have used all {MAX_GENS} generations for this session.")
        return False
    cols = [str(c).lower().replace('_', '').replace(' ', '') for c in df.columns]
    class_col = 'classname' if 'classname' in cols else cols[0]
    teacher_col = 'teachername' if 'teachername' in cols else cols[0]
    
    if df.iloc[:, cols.index(class_col)].nunique() > MAX_CLASSES:
        st.error(f"🚫 **{user_tier} Tier Limit:** Max {MAX_CLASSES} classes allowed. Please upgrade.")
        return False
    if df.iloc[:, cols.index(teacher_col)].nunique() > MAX_TEACHERS:
        st.error(f"🚫 **{user_tier} Tier Limit:** Max {MAX_TEACHERS} teachers allowed. Please upgrade.")
        return False
    return True

# ==========================================
# ⚙️ SIDEBAR (USER DASHBOARD)
# ==========================================
with st.sidebar:
    st.success(f"🏛️ {st.session_state.user.user_metadata.get('institution_name', 'My Dashboard')}")
    st.info(f"👤 **Account Tier:** {user_tier}")
    st.write(f"📊 **Usage:** {st.session_state.timetable_usage} / {MAX_GENS if MAX_GENS != float('inf') else 'Unlimited'}")
    
    if st.button("🚪 Log Out", use_container_width=True): 
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.timetable_ready = False
        clear_old_files()
        st.rerun()

    st.markdown("---")
    st.header("⚙️ Configuration")
    num_days = st.slider("Working Days", 4, 7, 5)
    num_periods = st.slider("Periods Per Day", 4, 12, 8)

# ==========================================
# 🏢 MAIN UI & BANNER
# ==========================================
with st.expander("📖 Application Guide & Account Limits", expanded=False):
    st.markdown("""
    ### 🛡️ User Tiers
    | Feature | 🟡 Guest (Free Trial) | 🔵 Standard (Institutional) | 🟢 PRO (Premium) |
    | :--- | :--- | :--- | :--- |
    | **Timetable Uses** | Max 5 Total | Max 15 Total | ✅ **Unlimited** |
    | **Timetable Size** | 5 Classes / 20 Teachers | 15 Classes / 30 Teachers | ✅ **Unlimited** |
    | **Cloud Vault** | ❌ No | ✅ Yes | ✅ Yes |
    | **Excel Exports**| ❌ No | ❌ No | ✅ **Yes** |
    """)

st.title("📅 Smart Timetable AI")

tab1, tab2, tab3 = st.tabs(["🏫 School Mode", "🎓 College Mode", "🖨️ View & Download"])

with tab1:
    with st.container():
        st.markdown("### 📝 School Data Input")
        c1, c2 = st.columns(2)
        with c1: st.download_button("📥 Workload Template", get_template("school"), "school_workload.csv")
        with c2: st.download_button("📥 Restrictions Template", get_template("rest"), "restrictions.csv")
        
        s_data = st.file_uploader("Upload Workload CSV", type=['csv'], key="s_up")
        s_rest = st.file_uploader("Upload Restrictions (Optional)", type=['csv'], key="sr_up")
        
        if st.button("🚀 Generate School Schedule", type="primary"):
            try:
                if os.path.exists('workload.csv'): os.remove('workload.csv')
                if os.path.exists('resources.csv'): os.remove('resources.csv')

                if s_data:
                    df_check = read_csv_safe(s_data)
                    if not check_saas_limits(df_check): st.stop() # SAAS LIMIT ENFORCER
                    save_file(s_data, "school_data.csv")
                    if not s_rest and os.path.exists('restrictions.csv'): os.remove('restrictions.csv')
                if s_rest:
                    save_file(s_rest, "restrictions.csv")
                
                with st.spinner("AI solving constraints..."):
                    solve_timetable(num_periods, num_days)
                    if os.path.exists('final_timetable_result.csv'):
                        st.session_state.timetable_ready = True
                        st.session_state.active_config = {"days": num_days, "periods": num_periods}
                        st.session_state.timetable_usage += 1 # INCREMENT USAGE
                        
                        if CAN_VAULT:
                            backup_to_cloud('school_data.csv')
                            if os.path.exists('restrictions.csv'): backup_to_cloud('restrictions.csv')
                            backup_to_cloud('final_timetable_result.csv')
                        
                        increment_usage_count()
                        st.success("✅ Generated! Switch to View tab.")
                    else: st.error("❌ No solution found.")
            except Exception as e: st.error(f"Generation Error: {str(e)}")

with tab2:
    with st.container():
        st.markdown("### 🎓 College Data Input")
        c1, c2, c3 = st.columns(3)
        with c1: st.download_button("📥 Workload", get_template("college"), "college_workload.csv")
        with c2: st.download_button("📥 Rooms", get_template("res"), "college_rooms.csv")
        with c3: st.download_button("📥 Restrictions", get_template("rest"), "college_rest.csv")

        c_data = st.file_uploader("Upload Workload", type=['csv'], key="c_up")
        c_res = st.file_uploader("Upload Rooms", type=['csv'], key="cr_up")
        c_rest = st.file_uploader("Upload Restrictions", type=['csv'], key="cre_up")

        if st.button("🚀 Generate College Schedule", type="primary"):
            try:
                if os.path.exists('school_data.csv'): os.remove('school_data.csv')

                if c_data:
                    df_check = read_csv_safe(c_data)
                    if not check_saas_limits(df_check): st.stop() # SAAS LIMIT ENFORCER
                    save_file(c_data, "workload.csv")
                    if not c_rest and os.path.exists('restrictions.csv'): os.remove('restrictions.csv')
                if c_res: save_file(c_res, "resources.csv")
                if c_rest: save_file(c_rest, "restrictions.csv")
                
                with st.spinner("AI solving labs & rooms..."):
                    solve_timetable(num_periods, num_days)
                    if os.path.exists('final_timetable_result.csv'):
                        st.session_state.timetable_ready = True
                        st.session_state.active_config = {"days": num_days, "periods": num_periods}
                        st.session_state.timetable_usage += 1 # INCREMENT USAGE
                        
                        if CAN_VAULT:
                            backup_to_cloud('workload.csv')
                            backup_to_cloud('resources.csv')
                            if os.path.exists('restrictions.csv'): backup_to_cloud('restrictions.csv')
                            backup_to_cloud('final_timetable_result.csv')
                        
                        increment_usage_count()
                        st.success("✅ Generated! Switch to View tab.")
                    else: st.error("❌ No solution found.")
            except Exception as e: st.error(f"Generation Error: {str(e)}")

with tab3:
    if st.session_state.timetable_ready and os.path.exists('final_timetable_result.csv'):
        df = pd.read_csv('final_timetable_result.csv')
        conf = st.session_state.get('active_config', {"days": 5, "periods": 8})
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][:conf['days']]
        periods = [f"Period {i}" for i in range(1, conf['periods'] + 1)]

        df['Day'] = pd.Categorical(df['Day'], categories=days, ordered=True)
        df['Class_View'] = df['Subject'] + " (" + df['Teacher'] + ") [" + df['Room'] + "]"
        df['Teacher_View'] = df['Subject'] + " (" + df['Class'] + ") [" + df['Room'] + "]"

        with st.container():
            st.markdown("### 🖨️ Interactive Grid & Macro Download")
            
            macro_class = df.pivot_table(index=['Day', 'Period'], columns='Class', values='Class_View', aggfunc=lambda x: x).reset_index()
            macro_class['Day'] = pd.Categorical(macro_class['Day'], categories=days, ordered=True)
            macro_class['Period'] = pd.Categorical(macro_class['Period'], categories=periods, ordered=True)
            macro_class = macro_class.sort_values(['Day', 'Period'])
            
            macro_teach = df.pivot_table(index=['Day', 'Period'], columns='Teacher', values='Teacher_View', aggfunc=lambda x: x).reset_index()
            macro_teach['Day'] = pd.Categorical(macro_teach['Day'], categories=days, ordered=True)
            macro_teach['Period'] = pd.Categorical(macro_teach['Period'], categories=periods, ordered=True)
            macro_teach = macro_teach.sort_values(['Day', 'Period'])
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if CAN_EXPORT:
                    st.download_button("📥 1. Download CSV (Classes)", macro_class.to_csv(index=False).encode('utf-8'), "Macro_Classes.csv", use_container_width=True, type="primary")
                else:
                    st.button("📥 Download CSV (Classes) - PRO", disabled=True, use_container_width=True)
            with c2:
                if CAN_EXPORT:
                    st.download_button("📥 1. Download CSV (Teachers)", macro_teach.to_csv(index=False).encode('utf-8'), "Macro_Teachers.csv", use_container_width=True, type="primary")
                else:
                    st.button("📥 Download CSV (Teachers) - PRO", disabled=True, use_container_width=True)
            with c3:
                if CAN_EXPORT:
                    try:
                        with open("Timetable_Macro_Tool.xlsm", "rb") as f:
                            macro_bytes = f.read()
                        st.download_button("🛠️ 2. Download Excel Macro Tool", macro_bytes, "Timetable_Macro_Tool.xlsm", use_container_width=True, type="secondary")
                    except FileNotFoundError:
                        st.button("🛠️ Macro Tool Offline", disabled=True, use_container_width=True)
                else:
                    st.button("🛠️ Excel Macro Tool - PRO Only", disabled=True, use_container_width=True)
            
            if not CAN_EXPORT:
                st.error("🔒 Upgrade to PRO to unlock Full Macro CSV Downloads & Excel Tools.")

            v1, v2 = st.tabs(["🎒 Class View", "👨‍🏫 Teacher View"])
            
            with v1:
                sel_class = st.selectbox("Select Class:", sorted(df['Class'].unique()))
                view_df = df[df['Class'] == sel_class].pivot_table(index='Period', columns='Day', values='Class_View', aggfunc=lambda x: x).reindex(index=periods, columns=days).fillna("---")
                st.table(style_timetable(view_df))

            with v2:
                sel_teach = st.selectbox("Select Teacher:", sorted(df['Teacher'].unique()))
                t_df = df[df['Teacher'] == sel_teach].pivot_table(index='Period', columns='Day', values='Teacher_View', aggfunc=lambda x: x).reindex(index=periods, columns=days).fillna("---")
                st.table(style_timetable(t_df))
    else: st.info("ℹ️ No active schedule. Upload data and Generate to begin.")