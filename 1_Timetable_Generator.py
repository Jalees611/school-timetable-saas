import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable
from supabase import create_client, Client

st.set_page_config(page_title="Smart Timetable AI", page_icon="📅", layout="wide")

# ==========================================
# ☁️ SUPABASE INITIALIZATION
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_supabase()

# ==========================================
# 🧠 SESSION STATE MANAGEMENT
# ==========================================
if 'timetable_ready' not in st.session_state:
    st.session_state.timetable_ready = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'guest_uses' not in st.session_state:
    st.session_state.guest_uses = 0
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'Login' # Can be 'Login', 'Register', 'Forgot'

# ==========================================
# 🔐 AUTHENTICATION FUNCTIONS
# ==========================================
def login(email, password):
    if supabase:
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = response.user
            st.success("Successfully logged in!")
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")

def register(email, password, full_name, inst_type, inst_name):
    if supabase:
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "institution_type": inst_type,
                        "institution_name": inst_name
                    }
                }
            })
            st.success("✅ Registration successful! Please check your email for the verification link.")
            st.session_state.auth_mode = 'Login'
        except Exception as e:
            st.error(f"Registration failed: {e}")

def reset_password(email):
    if supabase:
        try:
            supabase.auth.reset_password_for_email(email)
            st.success("✅ Password reset link sent to your email!")
            st.session_state.auth_mode = 'Login'
        except Exception as e:
            st.error(f"Failed to send reset link: {e}")

def logout():
    if supabase:
        supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.timetable_ready = False
    st.rerun()

# ==========================================
# 🛑 FREEMIUM LIMIT CHECKER
# ==========================================
def check_freemium_limits(df):
    if st.session_state.user is not None:
        return True # Pro/Logged-in users have no limits

    # Guest Limits
    if st.session_state.guest_uses >= 5:
        st.error("🚫 You have reached your 5 free trial generations. Please register to continue.")
        return False
    
    # Clean column names to find class and teacher safely
    cols = [str(c).lower().replace('_', '').replace(' ', '') for c in df.columns]
    df.columns = cols
    
    class_col = 'classname' if 'classname' in cols else cols[0]
    teacher_col = 'teachername' if 'teachername' in cols else cols[0]

    num_classes = df[class_col].nunique()
    num_teachers = df[teacher_col].nunique()

    if num_classes > 10 or num_teachers > 20:
        st.error(f"🚫 Freemium Limit Exceeded: Your file has {num_classes} classes and {num_teachers} teachers. The free limit is 10 classes and 20 teachers. Please register to unlock unlimited scheduling.")
        return False
        
    return True

# ==========================================
# ⚙️ SIDEBAR (THE FRONT DOOR)
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
            email = st.text_input("Email Address")
            inst_type = st.selectbox("Institution Type", ["School", "College", "University"])
            inst_name = st.text_input("Institution Name")
            pwd = st.text_input("Create Password", type="password")
            if st.button("Create Account", use_container_width=True):
                if name and email and pwd: register(email, pwd, name, inst_type, inst_name)
                else: st.warning("Please fill all fields.")
                
        elif mode == "Forgot Password":
            email = st.text_input("Enter your registered email")
            if st.button("Send Reset Link"): reset_password(email)

    else:
        user_meta = st.session_state.user.user_metadata
        st.header(f"🏛️ {user_meta.get('institution_name', 'My Dashboard')}")
        st.caption(f"Logged in as: {st.session_state.user.email}")
        st.success("✅ PRO Status: Unlimited Classes & Teachers")
        if st.button("🚪 Log Out", use_container_width=True): logout()

    st.markdown("---")
    st.header("⚙️ Schedule Settings")
    num_working_days = st.slider("Number of Working Days", 4, 7, 5)
    num_periods = st.slider("Periods per Day", 4, 12, 8)

# ==========================================
# 📖 TEMPLATE HELPERS & FILE MANAGEMENT
# ==========================================
@st.cache_data
def get_template(mode):
    if mode == "school": df = pd.DataFrame({"teacher_name": ["John Doe"], "subject_name": ["Maths"], "class_name": ["9-A"], "weekly_period": [6], "institutiontype": ["School"]})
    elif mode == "college": df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "subject_name": ["Ecology"], "class_name": ["BS 2024"], "weekly_period": [3], "required_resource_type": ["classroom"], "institutiontype": ["College"]})
    elif mode == "res": df = pd.DataFrame({"resource_name": ["CL-1", "MKB"], "resource_type": ["classroom", "lab"]})
    else: df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "day": ["Mon"], "period": ["Period 2"], "restriction_type": ["Unavailable"]})
    return df.to_csv(index=False).encode('utf-8')

def clear_old_files():
    for f in [f for f in os.listdir('.') if f.endswith('.csv') and f != 'final_timetable_result.csv']:
        try: os.remove(f)
        except: pass

def save_file(uploaded_file, name):
    with open(name, "wb") as f:
        f.write(uploaded_file.getbuffer())

# ==========================================
# 🏢 MAIN UI TABS
# ==========================================
st.title("📅 AI-Powered Timetable Generator")
if st.session_state.user is None:
    st.warning("⚠️ **GUEST MODE:** You can generate up to 5 timetables with a maximum of 10 classes and 20 teachers. **Downloads are locked.** Register for free to unlock your data.")

tab1, tab2, tab3 = st.tabs(["🏫 School Mode", "🎓 College Mode", "🖨️ View & Download"])

# --- TAB 1: SCHOOL ---
with tab1:
    col1, col2 = st.columns(2)
    with col1: st.download_button("📥 Workload Template", get_template("school"), "school_workload.csv")
    with col2: st.download_button("📥 Restrictions Template", get_template("rest"), "restrictions.csv")
    
    s_data = st.file_uploader("Upload School Workload", type=['csv'], key="s_up")
    s_rest = st.file_uploader("Upload Restrictions (Optional)", type=['csv'], key="sr_up")
    
    if st.button("🚀 Generate School Timetable", type="primary"):
        if s_data:
            df_check = pd.read_csv(s_data)
            if check_freemium_limits(df_check):
                clear_old_files()
                save_file(s_data, "school_data.csv")
                if s_rest: save_file(s_rest, "restrictions.csv")
                with st.spinner("AI solving school constraints..."):
                    solve_timetable(num_periods, num_working_days)
                    if os.path.exists('final_timetable_result.csv'):
                        st.session_state.timetable_ready = True
                        if st.session_state.user is None: st.session_state.guest_uses += 1
                        st.success("✅ Timetable Ready! Switch to Tab 3.")
                    else: st.error("❌ No solution. Try reducing teacher workload.")

# --- TAB 2: COLLEGE ---
with tab2:
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 Workload", get_template("college"), "college_workload.csv")
    with c2: st.download_button("📥 Resources", get_template("res"), "college_rooms.csv")
    with c3: st.download_button("📥 Restrictions", get_template("rest"), "college_rest.csv")
    
    c_data = st.file_uploader("College Workload", type=['csv'], key="c_up")
    c_res = st.file_uploader("Room Resources", type=['csv'], key="cr_up")
    c_rest = st.file_uploader("Restrictions (Optional)", type=['csv'], key="cre_up")
    
    if st.button("🚀 Generate College Timetable", type="primary"):
        if c_data and c_res:
            df_check = pd.read_csv(c_data)
            if check_freemium_limits(df_check):
                clear_old_files()
                save_file(c_data, "workload.csv")
                save_file(c_res, "resources.csv")
                if c_rest: save_file(c_rest, "restrictions.csv")
                with st.spinner("Solving Labs & Theory rooms..."):
                    solve_timetable(num_periods, num_working_days)
                    if os.path.exists('final_timetable_result.csv'):
                        st.session_state.timetable_ready = True
                        if st.session_state.user is None: st.session_state.guest_uses += 1
                        st.success("✅ Done! Check 'View & Download' tab.")
                    else: st.error("❌ Infeasible. Ensure you have enough rooms.")

# --- TAB 3: VIEW & DOWNLOAD ---
with tab3:
    if st.session_state.timetable_ready and os.path.exists('final_timetable_result.csv'):
        df = pd.read_csv('final_timetable_result.csv')
        days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][:num_working_days]
        active_periods = [f"Period {i}" for i in range(1, num_periods + 1)]

        df['Day'] = pd.Categorical(df['Day'], categories=days_order, ordered=True)
        df['Class_View'] = df['Subject'] + " (" + df['Teacher'] + ") [" + df['Room'] + "]"
        df['Teacher_View'] = df['Subject'] + " (" + df['Class'] + ") [" + df['Room'] + "]"

        v1, v2, v3 = st.tabs(["🎒 Class Schedule", "👨‍🏫 Teacher Schedule", "📄 Full Data"])
        
        with v1:
            sel_class = st.selectbox("Select Class:", sorted(df['Class'].unique()))
            c_matrix = df[df['Class'] == sel_class].pivot_table(index='Period', columns='Day', values='Class_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=days_order).fillna("---")
            st.dataframe(c_matrix, use_container_width=True)
            
            master_c = df.pivot_table(index=['Day', 'Period'], columns='Class', values='Class_View', aggfunc=lambda x: x).fillna("---")
            if st.session_state.user is not None:
                st.download_button("💾 Download Master Class Grid", master_c.to_csv().encode('utf-8'), "Master_Classes.csv")
            else:
                st.error("🔒 Downloads are locked in Demo Mode. Please register in the sidebar to download your files.")

        with v2:
            sel_teach = st.selectbox("Select Teacher:", sorted(df['Teacher'].unique()))
            t_matrix = df[df['Teacher'] == sel_teach].pivot_table(index='Period', columns='Day', values='Teacher_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=days_order).fillna("---")
            st.dataframe(t_matrix, use_container_width=True)
            
            master_t = df.pivot_table(index=['Day', 'Period'], columns='Teacher', values='Teacher_View', aggfunc=lambda x: x).fillna("---")
            if st.session_state.user is not None:
                st.download_button("💾 Download Master Teacher Grid", master_t.to_csv().encode('utf-8'), "Master_Teachers.csv")

        with v3:
            st.dataframe(df, use_container_width=True)
            if st.session_state.user is not None:
                st.download_button("💾 Download Raw Timetable", df.to_csv(index=False).encode('utf-8'), "Raw_Timetable.csv")
    else:
        st.info("ℹ️ No timetable active. Please generate one first.")