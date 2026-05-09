import streamlit as st
import pandas as pd
import os
from main_engine import solve_timetable
from supabase import create_client, Client

st.set_page_config(page_title="Smart Timetable AI", page_icon="📅", layout="wide")

# ==========================================
# ☁️ SUPABASE & THE PRIVATE VAULT
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_supabase()

def backup_to_cloud(file_name, folder="timetables"):
    if supabase is None or st.session_state.user is None:
        return
    user_id = st.session_state.user.id
    try:
        if os.path.exists(file_name):
            with open(file_name, 'rb') as f:
                supabase.storage.from_("user_vaults").upload(
                    file=f.read(),
                    path=f"{user_id}/{folder}/{file_name}",
                    file_options={"upsert": "true"}
                )
    except Exception as e:
        print(f"Cloud backup failed: {e}")

def restore_from_cloud(file_name, folder="timetables"):
    if supabase is None or st.session_state.user is None:
        return False
    user_id = st.session_state.user.id
    try:
        data = supabase.storage.from_("user_vaults").download(f"{user_id}/{folder}/{file_name}")
        with open(file_name, 'wb') as f:
            f.write(data)
        return True
    except Exception:
        return False

# ==========================================
# 🧠 SESSION STATE MANAGEMENT
# ==========================================
if 'timetable_ready' not in st.session_state: st.session_state.timetable_ready = False
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_uses' not in st.session_state: st.session_state.guest_uses = 0
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'Login'

# ==========================================
# 🔐 AUTHENTICATION FUNCTIONS
# ==========================================
def login(email, password):
    if supabase:
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = response.user
            
            # --- THE MAGIC VAULT RESTORE (Restore all inputs + result) ---
            with st.spinner("Restoring your workspace from the cloud..."):
                restore_from_cloud('school_data.csv')
                restore_from_cloud('workload.csv')
                restore_from_cloud('resources.csv')
                restore_from_cloud('restrictions.csv')
                if restore_from_cloud('final_timetable_result.csv'):
                    st.session_state.timetable_ready = True
                
            st.success("Successfully logged in!")
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")

def register(email, password, full_name, inst_type, inst_name):
    if supabase:
        try:
            supabase.auth.sign_up({
                "email": email, "password": password,
                "options": {"data": {"full_name": full_name, "institution_type": inst_type, "institution_name": inst_name}}
            })
            st.success("✅ Registration successful! Check your email for the verification link.")
            st.session_state.auth_mode = 'Login'
        except Exception as e: st.error(f"Registration failed: {e}")

def reset_password(email):
    if supabase:
        try:
            supabase.auth.reset_password_for_email(email)
            st.success("✅ Password reset link sent!")
            st.session_state.auth_mode = 'Login'
        except Exception as e: st.error(f"Failed: {e}")

def logout():
    if supabase: supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.timetable_ready = False
    # Clear local temporary files on logout
    clear_old_files()
    if os.path.exists('final_timetable_result.csv'): os.remove('final_timetable_result.csv')
    st.rerun()

# ==========================================
# 🛑 FREEMIUM LIMIT CHECKER
# ==========================================
def check_freemium_limits(df):
    if st.session_state.user is not None: return True
    if st.session_state.guest_uses >= 5:
        st.error("🚫 Trial reached. Please register.")
        return False
    
    cols = [str(c).lower().replace('_', '').replace(' ', '') for c in df.columns]
    df.columns = cols
    class_col = 'classname' if 'classname' in cols else cols[0]
    teacher_col = 'teachername' if 'teachername' in cols else cols[0]

    if df[class_col].nunique() > 10 or df[teacher_col].nunique() > 20:
        st.error(f"🚫 Limit Exceeded: 10 classes / 20 teachers max for guests.")
        return False
    return True

# ==========================================
# ⚙️ SIDEBAR
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
    else:
        user_meta = st.session_state.user.user_metadata
        st.header(f"🏛️ {user_meta.get('institution_name', 'My Dashboard')}")
        st.success("✅ PRO Status Active")
        if st.button("🚪 Log Out", use_container_width=True): logout()

    st.markdown("---")
    num_working_days = st.slider("Working Days", 4, 7, 5)
    num_periods = st.slider("Periods", 4, 12, 8)

# ==========================================
# 📖 HELPERS
# ==========================================
@st.cache_data
def get_template(mode):
    if mode == "school": df = pd.DataFrame({"teacher_name": ["John Doe"], "subject_name": ["Maths"], "class_name": ["9-A"], "weekly_period": [6], "institutiontype": ["School"]})
    elif mode == "college": df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "subject_name": ["Ecology"], "class_name": ["BS 2024"], "weekly_period": [3], "required_resource_type": ["classroom"], "institutiontype": ["College"]})
    elif mode == "res": df = pd.DataFrame({"resource_name": ["CL-1"], "resource_type": ["classroom"]})
    else: df = pd.DataFrame({"teacher_name": ["Dr. Jalees"], "day": ["Mon"], "period": ["Period 2"], "restriction_type": ["Unavailable"]})
    return df.to_csv(index=False).encode('utf-8')

def clear_old_files():
    # Only clear input data, leave result alone unless specifically requested
    for f in ['school_data.csv', 'workload.csv', 'resources.csv', 'restrictions.csv']:
        if os.path.exists(f): 
            try: os.remove(f)
            except: pass

def save_file(uploaded_file, name):
    with open(name, "wb") as f: f.write(uploaded_file.getbuffer())

# ==========================================
# 🏢 MAIN UI
# ==========================================
st.title("📅 Smart Timetable AI")
if st.session_state.user is None:
    st.warning("⚠️ **GUEST MODE:** Register to unlock downloads and cloud storage.")

tab1, tab2, tab3 = st.tabs(["🏫 School Mode", "🎓 College Mode", "🖨️ View & Download"])

# --- TAB 1: SCHOOL ---
with tab1:
    st.download_button("📥 School Template", get_template("school"), "school_workload.csv")
    s_data = st.file_uploader("Upload Workload", type=['csv'], key="s_up")
    s_rest = st.file_uploader("Upload Restrictions", type=['csv'], key="sr_up")
    
    has_saved_school = os.path.exists('school_data.csv') and st.session_state.user is not None
    if has_saved_school and not s_data:
        st.info("☁️ Saved School Workload loaded from Vault. You can click Generate directly!")

    if st.button("🚀 Generate School Timetable", type="primary"):
        if s_data or has_saved_school:
            if s_data:
                df_check = pd.read_csv(s_data)
                if not check_freemium_limits(df_check): st.stop()
                clear_old_files()
                save_file(s_data, "school_data.csv")
                if s_rest: save_file(s_rest, "restrictions.csv")
                
            with st.spinner("AI solving..."):
                solve_timetable(num_periods, num_working_days)
                if os.path.exists('final_timetable_result.csv'):
                    st.session_state.timetable_ready = True
                    if st.session_state.user is None: st.session_state.guest_uses += 1
                    else:
                        backup_to_cloud('school_data.csv')
                        if os.path.exists('restrictions.csv'): backup_to_cloud('restrictions.csv')
                        backup_to_cloud('final_timetable_result.csv')
                    st.success("✅ Success! Go to View & Download.")
                else: st.error("❌ No solution found.")

# --- TAB 2: COLLEGE ---
with tab2:
    st.download_button("📥 College Template", get_template("college"), "college_workload.csv")
    c_data = st.file_uploader("Upload Workload", type=['csv'], key="c_up")
    c_res = st.file_uploader("Upload Rooms", type=['csv'], key="cr_up")
    c_rest = st.file_uploader("Upload Restrictions", type=['csv'], key="cre_up")
    
    has_saved_college = os.path.exists('workload.csv') and os.path.exists('resources.csv') and st.session_state.user is not None
    if has_saved_college and not c_data:
        st.info("☁️ Saved College Data loaded from Vault. Ready to Generate!")
    
    if st.button("🚀 Generate College Timetable", type="primary"):
        if (c_data and c_res) or has_saved_college:
            if c_data and c_res:
                df_check = pd.read_csv(c_data)
                if not check_freemium_limits(df_check): st.stop()
                clear_old_files()
                save_file(c_data, "workload.csv")
                save_file(c_res, "resources.csv")
                if c_rest: save_file(c_rest, "restrictions.csv")
                
            with st.spinner("Solving Labs & Theory..."):
                solve_timetable(num_periods, num_working_days)
                if os.path.exists('final_timetable_result.csv'):
                    st.session_state.timetable_ready = True
                    if st.session_state.user is None: st.session_state.guest_uses += 1
                    else:
                        backup_to_cloud('workload.csv')
                        backup_to_cloud('resources.csv')
                        if os.path.exists('restrictions.csv'): backup_to_cloud('restrictions.csv')
                        backup_to_cloud('final_timetable_result.csv')
                    st.success("✅ Done! Saved to Vault.")
                else: st.error("❌ Infeasible.")

# --- TAB 3: VIEW & DOWNLOAD ---
with tab3:
    if st.session_state.timetable_ready and os.path.exists('final_timetable_result.csv'):
        df = pd.read_csv('final_timetable_result.csv')
        days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][:num_working_days]
        active_periods = [f"Period {i}" for i in range(1, num_periods + 1)]

        df['Day'] = pd.Categorical(df['Day'], categories=days_order, ordered=True)
        df['Class_View'] = df['Subject'] + " (" + df['Teacher'] + ") [" + df['Room'] + "]"
        df['Teacher_View'] = df['Subject'] + " (" + df['Class'] + ") [" + df['Room'] + "]"

        v1, v2, v3 = st.tabs(["🎒 Class View", "👨‍🏫 Teacher View", "📄 Full Data"])
        
        with v1:
            sel_class = st.selectbox("Class:", sorted(df['Class'].unique()))
            c_matrix = df[df['Class'] == sel_class].pivot_table(index='Period', columns='Day', values='Class_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=days_order).fillna("---")
            st.dataframe(c_matrix, use_container_width=True)
            if st.session_state.user is not None:
                st.download_button("💾 Export Class CSV", c_matrix.to_csv().encode('utf-8'), f"{sel_class}_Schedule.csv")
            else: st.error("🔒 Downloads Locked.")

        with v2:
            sel_teach = st.selectbox("Teacher:", sorted(df['Teacher'].unique()))
            t_matrix = df[df['Teacher'] == sel_teach].pivot_table(index='Period', columns='Day', values='Teacher_View', aggfunc=lambda x: x).reindex(index=active_periods, columns=days_order).fillna("---")
            st.dataframe(t_matrix, use_container_width=True)
            if st.session_state.user is not None:
                st.download_button("💾 Export Teacher CSV", t_matrix.to_csv().encode('utf-8'), f"{sel_teach}_Schedule.csv")

        with v3:
            st.dataframe(df, use_container_width=True)
            if st.session_state.user is not None:
                st.download_button("💾 Download All Data", df.to_csv(index=False).encode('utf-8'), "Full_Timetable.csv")
    else:
        st.info("ℹ️ No active schedule. Upload data and Generate to begin.")