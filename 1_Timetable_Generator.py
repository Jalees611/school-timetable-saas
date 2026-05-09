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
    .block-container { padding-top: 2rem; padding-bottom: 2rem; } /* PULLS CONTENT UP */
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

def restore_from_cloud(file_name, folder="timetables"):
    if supabase is None or st.session_state.user is None: return False
    try:
        data = supabase.storage.from_("user_vaults").download(f"{st.session_state.user.id}/{folder}/{file_name}")
        with open(file_name, 'wb') as f: f.write(data)
        return True
    except: return False

# ==========================================
# 🧠 HELPERS & LOGIC
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

def save_file(uploaded_file, name):
    with open(name, "wb") as f: f.write(uploaded_file.getbuffer())

@st.cache_data
def get_template(mode):
    if mode == "school": df = pd.DataFrame({"teacher_name": ["John Doe"], "subject_name": ["Maths"], "class_name": ["9-A"], "weekly_period": [6], "institutiontype": ["School"]})
    elif mode == "college": df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "subject_name": ["Ecology"], "class_name": ["BS 2024"], "weekly_period": [3], "required_resource_type": ["classroom"], "institutiontype": ["College"]})
    elif mode == "res": df = pd.DataFrame({"resource_name": ["CL-1"], "resource_type": ["classroom"]})
    else: df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "day": ["Mon"], "period": ["Period 2"], "restriction_type": ["Unavailable"]})
    return df.to_csv(index=False).encode('utf-8')

# ==========================================
# 🔐 AUTH & FREEMIUM LIMITS
# ==========================================
if 'timetable_ready' not in st.session_state: st.session_state.timetable_ready = False
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_uses' not in st.session_state: st.session_state.guest_uses = 0
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'Login'

def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        with st.spinner("Restoring Vault..."):
            for f in ['school_data.csv', 'workload.csv', 'resources.csv', 'restrictions.csv']: restore_from_cloud(f)
            if restore_from_cloud('final_timetable_result.csv'): st.session_state.timetable_ready = True
        st.rerun()
    except Exception as e: st.error(f"Login Error: {e}")

def register(email, password, full_name, inst_type, inst_name):
    try:
        supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {"full_name": full_name, "institution_type": inst_type, "institution_name": inst_name}}})
        st.success("✅ Registration successful! Please log in.")
        st.session_state.auth_mode = 'Login'
    except Exception as e: st.error(f"Error: {e}")

def reset_password(email):
    try:
        supabase.auth.reset_password_for_email(email)
        st.success("✅ Password reset link sent to your email!")
        st.session_state.auth_mode = 'Login'
    except Exception as e: st.error(f"Error: {e}")

def check_freemium_limits(df):
    if st.session_state.user is not None: return True
    if st.session_state.guest_uses >= 5:
        st.error("🚫 Trial reached. Please register.")
        return False
    cols = [str(c).lower().replace('_', '').replace(' ', '') for c in df.columns]
    class_col = 'classname' if 'classname' in cols else cols[0]
    teacher_col = 'teachername' if 'teachername' in cols else cols[0]
    if df.iloc[:, cols.index(class_col)].nunique() > 10 or df.iloc[:, cols.index(teacher_col)].nunique() > 20:
        st.error(f"🚫 Limit Exceeded: 10 classes / 20 teachers max for guests.")
        return False
    return True

# ==========================================
# ⚙️ SIDEBAR (USER SETTINGS)
# ==========================================
with st.sidebar:
    if st.session_state.user is None:
        st.header("👋 Welcome, Guest")
        st.progress(st.session_state.guest_uses / 5.0, text=f"Free Uses: {st.session_state.guest_uses}/5")
        st.markdown("---")
        mode = st.radio("Account Access", ["Login", "Register", "Forgot Password"], index=["Login", "Register", "Forgot Password"].index(st.session_state.auth_mode))
        st.session_state.auth_mode = mode
        
        if mode == "Login":
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            if st.button("Log In", use_container_width=True): login(email, pwd)
        elif mode == "Register":
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            inst_type = st.selectbox("Type", ["School", "College"])
            inst_name = st.text_input("Institution Name")
            pwd = st.text_input("Password", type="password")
            if st.button("Create Account", use_container_width=True): register(email, pwd, name, inst_type, inst_name)
        elif mode == "Forgot Password":
            email = st.text_input("Enter your registered email")
            if st.button("Send Reset Link", use_container_width=True): reset_password(email)
    else:
        st.success(f"🏛️ {st.session_state.user.user_metadata.get('institution_name', 'My Dashboard')}")
        st.info("✅ PRO Status Active")
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
# 🏢 MAIN UI & INSTRUCTION BANNER
# ==========================================
with st.expander("📖 Application Guide & Account Limits (Click to expand)", expanded=False):
    st.markdown("""
    ### 🛡️ User Tiers
    * 🟡 **Guest Mode:** Maximum of 5 free trial generations. Data is limited to 10 classes and 20 teachers. Downloads and Cloud Vault are locked.
    * 🟢 **PRO Mode:** Unlimited generations, unlimited data size, active Cloud Vault memory, and full CSV exporting. (Register for free on the sidebar).

    ### 🤖 AI Scheduling Rules
    * **School Mode:** The AI automatically balances teacher workloads across the week and strictly respects your "Restrictions" file (e.g., if a teacher is unavailable on Monday mornings).
    * **College Mode:** The AI handles complex room allocation. It ensures subjects marked as "Lab" are placed in Lab rooms for 3-period continuous blocks, while standard classes are routed to standard classrooms.
    """)

st.title("📅 Smart Timetable AI")

if st.session_state.user is None: st.warning("⚠️ **GUEST MODE:** Register to unlock downloads and cloud vault.")

tab1, tab2, tab3 = st.tabs(["🏫 School Mode", "🎓 College Mode", "🖨️ View & Download"])

with tab1:
    with st.container():
        st.markdown("### 📝 School Data Input")
        c1, c2 = st.columns(2)
        with c1: st.download_button("📥 Workload Template", get_template("school"), "school_workload.csv")
        with c2: st.download_button("📥 Restrictions Template", get_template("rest"), "restrictions.csv")
        
        s_data = st.file_uploader("Upload Workload CSV", type=['csv'], key="s_up")
        s_rest = st.file_uploader("Upload Restrictions (Optional)", type=['csv'], key="sr_up")
        
        has_saved = os.path.exists('school_data.csv') and st.session_state.user is not None
        if has_saved and not s_data: st.info("☁️ Using saved Workload from Vault. Ready to Generate!")
        
        if st.button("🚀 Generate School Schedule", type="primary"):
            if s_data or has_saved:
                if s_data:
                    df_check = pd.read_csv(s_data)
                    if not check_freemium_limits(df_check): st.stop()
                    clear_old_files()
                    save_file(s_data, "school_data.csv")
                    if s_rest: save_file(s_rest, "restrictions.csv")
                
                with st.spinner("AI solving constraints..."):
                    solve_timetable(num_periods, num_days)
                    if os.path.exists('final_timetable_result.csv'):
                        st.session_state.timetable_ready = True
                        st.session_state.active_config = {"days": num_days, "periods": num_periods}
                        if st.session_state.user is None: st.session_state.guest_uses += 1
                        else:
                            backup_to_cloud('school_data.csv')
                            if os.path.exists('restrictions.csv'): backup_to_cloud('restrictions.csv')
                            backup_to_cloud('final_timetable_result.csv')
                        st.success("✅ Generated! Switch to View tab.")
                    else: st.error("❌ No solution found.")

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
        
        has_saved_c = os.path.exists('workload.csv') and os.path.exists('resources.csv') and st.session_state.user is not None
        if has_saved_c and not c_data: st.info("☁️ Using saved College Data from Vault. Ready to Generate!")

        if st.button("🚀 Generate College Schedule", type="primary"):
            if (c_data and c_res) or has_saved_c:
                if c_data and c_res:
                    df_check = pd.read_csv(c_data)
                    if not check_freemium_limits(df_check): st.stop()
                    clear_old_files()
                    save_file(c_data, "workload.csv")
                    save_file(c_res, "resources.csv")
                    if c_rest: save_file(c_rest, "restrictions.csv")
                
                with st.spinner("AI solving labs & rooms..."):
                    solve_timetable(num_periods, num_days)
                    if os.path.exists('final_timetable_result.csv'):
                        st.session_state.timetable_ready = True
                        st.session_state.active_config = {"days": num_days, "periods": num_periods}
                        if st.session_state.user is None: st.session_state.guest_uses += 1
                        else:
                            backup_to_cloud('workload.csv')
                            backup_to_cloud('resources.csv')
                            if os.path.exists('restrictions.csv'): backup_to_cloud('restrictions.csv')
                            backup_to_cloud('final_timetable_result.csv')
                        st.success("✅ Generated! Switch to View tab.")
                    else: st.error("❌ No solution found.")

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
            st.markdown("### 🖨️ Interactive Grid")
            v1, v2, v3 = st.tabs(["🎒 Class View", "👨‍🏫 Teacher View", "📄 Raw Data"])
            
            with v1:
                sel_class = st.selectbox("Select Class:", sorted(df['Class'].unique()))
                view_df = df[df['Class'] == sel_class].pivot_table(index='Period', columns='Day', values='Class_View', aggfunc=lambda x: x).reindex(index=periods, columns=days).fillna("---")
                st.table(style_timetable(view_df))
                if st.session_state.user: st.download_button("💾 Export Class CSV", view_df.to_csv().encode('utf-8'), f"{sel_class}.csv")
                else: st.caption("🔒 Login to download.")

            with v2:
                sel_teach = st.selectbox("Select Teacher:", sorted(df['Teacher'].unique()))
                t_df = df[df['Teacher'] == sel_teach].pivot_table(index='Period', columns='Day', values='Teacher_View', aggfunc=lambda x: x).reindex(index=periods, columns=days).fillna("---")
                st.table(style_timetable(t_df))
                if st.session_state.user: st.download_button("💾 Export Teacher CSV", t_df.to_csv().encode('utf-8'), f"{sel_teach}.csv")

            with v3:
                st.dataframe(df, use_container_width=True)
                if st.session_state.user: st.download_button("💾 Download All", df.to_csv(index=False).encode('utf-8'), "Full.csv")
    else: st.info("ℹ️ No active schedule. Upload data and Generate to begin.")