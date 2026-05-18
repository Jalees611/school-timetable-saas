import streamlit as st

# Configure the page settings
st.set_page_config(
    page_title="SmartEd Tools | AI-Powered Education SaaS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a clean, professional SaaS look
st.markdown("""
    <style>
    .hero-container {text-align: center; padding: 3rem 1rem;}
    .hero-title {font-size: 3.5rem; font-weight: 800; color: #0d47a1; margin-bottom: 0.5rem;}
    .hero-subtitle {font-size: 1.5rem; color: #546e7a; margin-bottom: 2rem;}
    .feature-card {background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; height: 100%; border-top: 4px solid #0d47a1;}
    .tier-header {text-align: center; margin-top: 3rem; margin-bottom: 1.5rem;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🚀 HERO SECTION
# ==========================================
st.markdown('<div class="hero-container">', unsafe_allow_html=True)
st.markdown('<div class="hero-title">SmartEd Tools</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Automate timetables and analyze educational surveys in seconds with AI.</div>', unsafe_allow_html=True)

# Navigation Buttons
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    c1, c2 = st.columns(2)
    with c1:
        st.page_link("pages/1_Timetable_Generator.py", label="📅 Try Timetable AI", icon="🚀", use_container_width=True)
    with c2:
        st.page_link("pages/2_Survey_Analyzer.py", label="📊 Try Survey AI", icon="📈", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# ⭐ VALUE PROPOSITION (FEATURES)
# ==========================================
st.markdown("<h2 style='text-align: center;'>Why choose SmartEd Tools?</h2><br>", unsafe_allow_html=True)

f1, f2, f3 = st.columns(3)
with f1:
    st.markdown("""
    <div class="feature-card">
        <h3>⚡ Lightning Fast</h3>
        <p>Replace weeks of manual scheduling and Excel data entry with advanced optimization algorithms that solve constraints in seconds.</p>
    </div>
    """, unsafe_allow_html=True)
with f2:
    st.markdown("""
    <div class="feature-card">
        <h3>🤖 Gemini AI Insights</h3>
        <p>Don't just look at survey charts. Let our integrated Google Gemini AI write executive summaries and recommendations for you.</p>
    </div>
    """, unsafe_allow_html=True)
with f3:
    st.markdown("""
    <div class="feature-card">
        <h3>☁️ Secure Cloud Vault</h3>
        <p>Your institutional data is safely backed up to your private cloud vault. Access your workload and surveys from anywhere.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 💳 PRICING & TIER MATRIX
# ==========================================
st.markdown("<h2 class='tier-header'>Transparent Pricing & Tiers</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #546e7a; margin-bottom: 2rem;'>Start for free, upgrade when you need more power.</p>", unsafe_allow_html=True)

# The exact SaaS Matrix we planned
st.markdown("""
| Feature | 🟡 Guest (Free Trial) | 🔵 Standard (Institutional) | 🟢 PRO (Premium) |
| :--- | :--- | :--- | :--- |
| **Authentication Requirement** | Must Register | Must Register | Must Register |
| **Email Domain Rule** | **Any Domain** (e.g., @gmail.com) | **Institutional Only** (e.g., @school.edu) | **Any Domain** |
| **Timetable Uses** | **Max 5 Total** | Max 15 Total | ✅ **Unlimited** |
| **Timetable Size Limits** | 5 Classes / 20 Teachers | 15 Classes / 30 Teachers | ✅ **Unlimited** |
| **Survey Uses** | **Max 5 Total** | Max 15 Total | ✅ **Unlimited** |
| **Survey Size Limits** | 50 Rows / 10 Questions | 100 Rows / 15 Questions| ✅ **Unlimited** |
| **Cloud Vault Access** | ❌ No | ✅ Yes | ✅ Yes |
| **Excel & PDF Exports** | ❌ No | ❌ No | ✅ **Yes** |
| **Gemini AI Summaries** | ❌ No | ❌ No | ✅ **Yes** |
""")

st.markdown("<br>", unsafe_allow_html=True)
st.info("💡 **Ready to start?** Use the sidebar navigation on the left to open the Timetable Generator or Survey Analyzer and register your account today!")

# ==========================================
# 📝 FOOTER
# ==========================================
st.markdown("---")
st.markdown("<p style='text-align: center; color: grey; font-size: 0.8rem;'>© 2024 SmartEd Tools. All rights reserved.</p>", unsafe_allow_html=True)