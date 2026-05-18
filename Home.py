import streamlit as st
from supabase import create_client

# Configure the page settings
st.set_page_config(page_title="SmartEd Tools | AI-Powered Education SaaS", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# ☁️ SUPABASE CONNECTION
# ==========================================
@st.cache_resource
def init_supabase():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None
supabase = init_supabase()

# ==========================================
# 🔐 AUTHENTICATION LOGIC
# ==========================================
if 'user' not in st.session_state: st.session_state.user = None
if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'Login'
PUBLIC_DOMAINS = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'aol.com']

def fetch_user_profile():
    if st.session_state.user is None: return
    try:
        res = supabase.table("profiles").select("is_pro").eq("id", st.session_state.user.id).execute()
        if res.data: st.session_state.is_pro = res.data[0].get("is_pro", False)
    except: pass

def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        fetch_user_profile()
        st.success("✅ Logged in successfully!")
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
        st.success("✅ 6-Digit Code sent to your email!")
    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# ⚙️ SIDEBAR (THE FRONT DOOR)
# ==========================================
with st.sidebar:
    if st.session_state.user is None:
        st.header("👋 Welcome to SmartEd")
        
        mode = st.radio("Account Access", ["Login", "Register", "Forgot Password"], index=["Login", "Register", "Forgot Password"].index(st.session_state.auth_mode))
        st.session_state.auth_mode = mode
        
        if mode == "Login":
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            if st.button("Log In", use_container_width=True, type="primary"): login(email, pwd)
            
        elif mode == "Register":
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            if any(domain in email.lower() for domain in PUBLIC_DOMAINS): st.caption("⚠️ Note: Public emails are limited to the Guest Tier.")
            inst_type = st.selectbox("Type", ["School", "College", "University"]) 
            inst_name = st.text_input("Institution Name")
            pwd = st.text_input("Password", type="password")
            if st.button("Create Account", use_container_width=True, type="primary"): register(email, pwd, name, inst_type, inst_name)
            
        elif mode == "Forgot Password":
            st.info("Step 1: Request a reset code.")
            reset_email = st.text_input("Registered Email")
            if st.button("Send Reset Code", use_container_width=True): 
                reset_password(reset_email)
            
            st.markdown("---")
            st.info("Step 2: Enter your code to set a new password.")
            reset_code = st.text_input("6-Digit Code")
            new_pwd = st.text_input("New Password", type="password")
            
            if st.button("Update Password", use_container_width=True, type="primary"):
                if len(new_pwd) < 6:
                    st.error("Password must be at least 6 characters.")
                elif not reset_email or not reset_code:
                    st.error("Please enter your email and the 6-digit code.")
                else:
                    try:
                        # 1. Verify the 6-digit code
                        supabase.auth.verify_otp({"email": reset_email, "token": reset_code, "type": "recovery"})
                        # 2. Update to the new password
                        supabase.auth.update_user({"password": new_pwd})
                        # 3. Log them out securely so they can log in fresh
                        supabase.auth.sign_out()
                        
                        st.success("✅ Password successfully updated! Please log in.")
                    except Exception as e:
                        st.error(f"Error: Invalid code or email. Please try again.")
            
    else:
        # What they see when logged in
        email_domain = st.session_state.user.email.split('@')[1].lower() if st.session_state.user.email else ""
        if st.session_state.is_pro: st.success("✅ PRO Status Active")
        elif email_domain in PUBLIC_DOMAINS: st.warning("🟡 Guest Tier (Free Trial)")
        else: st.info("🔵 Standard Tier Active")
            
        st.write(f"Logged in as: **{st.session_state.user.email}**")
        
        # Keep the logged-in update password box just in case they want to change it later
        with st.expander("🔐 Change Password"):
            new_pwd = st.text_input("Enter New Password", type="password", key="logged_in_pwd")
            if st.button("Save New Password", use_container_width=True, type="primary"):
                if len(new_pwd) >= 6:
                    try:
                        supabase.auth.update_user({"password": new_pwd})
                        st.success("✅ Password updated!")
                    except Exception as e: st.error(f"Error: {e}")
                else: st.error("Password must be at least 6 characters.")

        if st.button("🚪 Log Out", use_container_width=True): 
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# ==========================================
# 🎨 CUSTOM UI & HERO SECTION
# ==========================================
st.markdown("""
    <style>
    .hero-container {text-align: center; padding: 3rem 1rem;}
    .hero-title {font-size: 3.5rem; font-weight: 800; color: #0d47a1; margin-bottom: 0.5rem;}
    .hero-subtitle {font-size: 1.5rem; color: #546e7a; margin-bottom: 2rem;}
    .feature-card {background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; height: 100%; border-top: 4px solid #0d47a1;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-container">', unsafe_allow_html=True)
st.markdown('<div class="hero-title">SmartEd Tools</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Automate timetables and analyze educational surveys in seconds with AI.</div>', unsafe_allow_html=True)

if st.session_state.user is None:
    st.info("👈 **Please Register or Log In using the sidebar to unlock the tools.**")
else:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        c1, c2 = st.columns(2)
        with c1: st.page_link("pages/1_Timetable_Generator.py", label="📅 Launch Timetable AI", icon="🚀", use_container_width=True)
        with c2: st.page_link("pages/2_Survey_Analyzer.py", label="📊 Launch Survey AI", icon="📈", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("<h2 style='text-align: center;'>Transparent Pricing & Tiers</h2>", unsafe_allow_html=True)
st.markdown("""
| Feature | 🟡 Guest (Free Trial) | 🔵 Standard (Institutional) | 🟢 PRO (Premium) |
| :--- | :--- | :--- | :--- |
| **Email Domain Rule** | **Any Domain** (e.g., @gmail.com) | **Institutional Only** (e.g., @school.edu) | **Any Domain** |
| **Timetable Uses** | **Max 5 Total** | Max 15 Total | ✅ **Unlimited** |
| **Timetable Size** | 5 Classes / 20 Teachers | 15 Classes / 30 Teachers | ✅ **Unlimited** |
| **Survey Uses** | **Max 5 Total** | Max 15 Total | ✅ **Unlimited** |
| **Survey Size** | 50 Rows / 10 Questions | 100 Rows / 15 Questions| ✅ **Unlimited** |
| **Cloud Vault Access** | ❌ No | ✅ Yes | ✅ Yes |
| **Excel & PDF Exports**| ❌ No | ❌ No | ✅ **Yes** |
| **Gemini AI Insights** | ❌ No | ❌ No | ✅ **Yes** |
""")