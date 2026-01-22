import streamlit as st
from lib.ui import apply_global_styles, top_navbar
from lib.db import init_db

st.set_page_config(
	page_title="Community Connect",
	page_icon="🫶",
	layout="wide",
	initial_sidebar_state="collapsed",
)

apply_global_styles()
init_db()

# Navbar
_ = top_navbar()

st.markdown("<div class='spacer-32'></div>", unsafe_allow_html=True)

# Hero Section
st.markdown("""
<div class='hero-container'>
	<h1 class='hero-title'>Community Connect</h1>
	<p class='hero-subtitle'>
		Empowering communities through meaningful connections. 
		Connect volunteers with NGOs using location-aware matching and streamlined task workflows.
	</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='spacer-48'></div>", unsafe_allow_html=True)

# Login Buttons - Integrated into cards
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
	btn_col1, btn_col2 = st.columns(2, gap="large")
	with btn_col1:
		st.markdown("""
		<div class='login-card'>
			<div class='login-icon'>🏢</div>
			<h3 class='login-title'>For NGOs</h3>
			<p class='login-description'>Post volunteer opportunities, manage tasks, and track impact</p>
		</div>
		""", unsafe_allow_html=True)
		st.page_link("pages/1_NGO_Dashboard.py", label="🏢 Login as NGO", icon=None, use_container_width=True)
	
	with btn_col2:
		st.markdown("""
		<div class='login-card login-card-volunteer'>
			<div class='login-icon'>🧑‍🤝‍🧑</div>
			<h3 class='login-title'>For Volunteers</h3>
			<p class='login-description'>Discover opportunities, make an impact, and grow your community</p>
		</div>
		""", unsafe_allow_html=True)
		st.page_link("pages/2_Volunteer_Dashboard.py", label="🧑‍🤝‍🧑 Login as Volunteer", icon=None, use_container_width=True)

st.markdown("<div class='spacer-48'></div>", unsafe_allow_html=True)

st.markdown("<div class='footer'>Made with ❤️ for communities. © 2025 Community Connect</div>", unsafe_allow_html=True)
