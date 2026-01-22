import streamlit as st


def apply_global_styles():
	css = """
	<style>
	@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
	
	:root {
		--primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		--secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
		--success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
		--card-gradient: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%);
		--bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		--text-primary: #1a202c;
		--text-secondary: #4a5568;
		--text-muted: #718096;
		--border-color: rgba(102, 126, 234, 0.25);
		--input-border: rgba(102, 126, 234, 0.3);
		--shadow-sm: 0 2px 8px rgba(102, 126, 234, 0.1);
		--shadow-md: 0 4px 16px rgba(102, 126, 234, 0.15);
		--shadow-lg: 0 8px 32px rgba(102, 126, 234, 0.2);
		--shadow-xl: 0 12px 48px rgba(102, 126, 234, 0.25);
	}
	
	* {
		font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
	}
	
	/* Light background for entire app */
	.stApp {
		background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
	}
	
	.block-container { 
		padding-top: 2rem;
		max-width: 1400px;
	}
	
	/* Hero Section */
	.hero-container {
		text-align: center;
		padding: 4rem 2rem;
		background: var(--bg-gradient);
		border-radius: 2rem;
		margin: 2rem 0;
		box-shadow: var(--shadow-xl);
		position: relative;
		overflow: hidden;
	}
	
	.hero-container::before {
		content: '';
		position: absolute;
		top: -50%;
		right: -50%;
		width: 200%;
		height: 200%;
		background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
		animation: pulse 8s ease-in-out infinite;
	}
	
	@keyframes pulse {
		0%, 100% { transform: scale(1); opacity: 0.5; }
		50% { transform: scale(1.1); opacity: 0.8; }
	}
	
	.hero-title { 
		font-size: 4rem; 
		font-weight: 900; 
		color: #ffffff;
		letter-spacing: -0.03em;
		margin-bottom: 1rem;
		text-shadow: 0 4px 12px rgba(0,0,0,0.2);
		position: relative;
		z-index: 1;
	}
	
	.hero-subtitle { 
		font-size: 1.4rem; 
		color: rgba(255,255,255,0.95);
		margin: 1.5rem auto;
		max-width: 700px;
		line-height: 1.6;
		font-weight: 500;
		position: relative;
		z-index: 1;
	}
	
	/* Login Cards */
	.login-card {
		text-align: center;
		padding: 2.5rem 2rem;
		background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
		border-radius: 1.5rem;
		border: 2px solid rgba(102, 126, 234, 0.25);
		transition: all 0.3s ease;
		margin-bottom: 1rem;
		box-shadow: var(--shadow-md);
	}
	
	.login-card:hover {
		transform: translateY(-8px);
		box-shadow: var(--shadow-xl);
		border-color: rgba(102, 126, 234, 0.4);
	}
	
	.login-card-volunteer {
		background: linear-gradient(135deg, rgba(240, 147, 251, 0.08) 0%, rgba(245, 87, 108, 0.08) 100%);
		border-color: rgba(240, 147, 251, 0.25);
	}
	
	.login-card-volunteer:hover {
		border-color: rgba(240, 147, 251, 0.4);
	}
	
	.login-icon {
		font-size: 3.5rem;
		margin-bottom: 1rem;
	}
	
	.login-title {
		font-size: 1.75rem;
		font-weight: 800;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		margin-bottom: 1rem;
	}
	
	.login-card-volunteer .login-title {
		background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
	}
	
	.login-description {
		color: #4a5568;
		margin-bottom: 0;
		line-height: 1.6;
		font-size: 1.05rem;
	}
	
	/* Modern Cards */
	.card { 
		background: var(--card-gradient);
		backdrop-filter: blur(10px);
		border: 2px solid var(--border-color);
		border-radius: 1.5rem;
		padding: 2rem;
		box-shadow: var(--shadow-md);
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		position: relative;
		overflow: hidden;
	}
	
	.card::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 4px;
		background: var(--primary-gradient);
		transform: scaleX(0);
		transition: transform 0.3s ease;
	}
	
	.card:hover::before {
		transform: scaleX(1);
	}
	
	.card:hover { 
		transform: translateY(-8px);
		box-shadow: var(--shadow-xl);
		border-color: rgba(102, 126, 234, 0.4);
	}
	
	.card-title { 
		font-size: 1.75rem;
		font-weight: 800;
		background: var(--primary-gradient);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		margin-bottom: 1rem;
	}
	
	.card-body { 
		color: var(--text-secondary);
		font-size: 1.05rem;
		line-height: 1.6;
		margin-bottom: 1.5rem;
	}
	
	/* Metric Cards */
	.metric-card {
		background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%);
		border: 2px solid rgba(102, 126, 234, 0.25);
		border-radius: 1.25rem;
		padding: 1.75rem;
		text-align: center;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
		box-shadow: var(--shadow-md);
	}
	
	.metric-card::before {
		content: '';
		position: absolute;
		top: -50%;
		left: -50%;
		width: 200%;
		height: 200%;
		background: radial-gradient(circle, rgba(102, 126, 234, 0.1) 0%, transparent 70%);
		opacity: 0;
		transition: opacity 0.3s ease;
	}
	
	.metric-card:hover::before {
		opacity: 1;
	}
	
	.metric-card:hover {
		transform: translateY(-4px);
		box-shadow: var(--shadow-lg);
		border-color: rgba(102, 126, 234, 0.4);
	}
	
	.metric-value {
		font-size: 2.5rem;
		font-weight: 900;
		background: var(--primary-gradient);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		margin-bottom: 0.5rem;
	}
	
	.metric-label {
		color: var(--text-secondary);
		font-weight: 600;
		font-size: 0.95rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	
	/* Navbar */
	.navbar { 
		background: rgba(255, 255, 255, 0.98);
		backdrop-filter: blur(12px);
		position: sticky;
		top: 0;
		z-index: 100;
		border-bottom: 2px solid var(--border-color);
		box-shadow: var(--shadow-sm);
		padding: 1rem 2rem;
		margin: -1rem -2rem 0 -2rem;
	}
	
	.nav-brand { 
		font-weight: 900;
		font-size: 1.5rem;
		background: var(--primary-gradient);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		letter-spacing: -0.02em;
	}
	
	.nav-links a { 
		margin-left: 2rem;
		text-decoration: none;
		color: var(--text-primary);
		font-weight: 600;
		font-size: 1rem;
		transition: all 0.2s ease;
		position: relative;
	}
	
	.nav-links a::after {
		content: '';
		position: absolute;
		bottom: -4px;
		left: 0;
		width: 0;
		height: 2px;
		background: var(--primary-gradient);
		transition: width 0.3s ease;
	}
	
	.nav-links a:hover::after {
		width: 100%;
	}
	
	.nav-links a:hover {
		color: #667eea;
	}
	
	/* Buttons */
	button[kind="primary"], .stButton > button[kind="primary"] {
		background: var(--primary-gradient) !important;
		color: white !important;
		border: none !important;
		border-radius: 0.75rem !important;
		padding: 0.75rem 1.5rem !important;
		font-weight: 700 !important;
		transition: all 0.3s ease !important;
		box-shadow: var(--shadow-md) !important;
	}
	
	button[kind="primary"]:hover {
		transform: translateY(-2px) !important;
		box-shadow: var(--shadow-lg) !important;
	}
	
	/* Page Link Buttons - Enhanced */
	.stPageLink button {
		background: var(--primary-gradient) !important;
		color: white !important;
		border: none !important;
		border-radius: 0.75rem !important;
		padding: 0.875rem 1.75rem !important;
		font-weight: 700 !important;
		font-size: 1.05rem !important;
		transition: all 0.3s ease !important;
		box-shadow: var(--shadow-md) !important;
		width: 100%;
	}
	
	.stPageLink button:hover {
		transform: translateY(-3px) !important;
		box-shadow: var(--shadow-xl) !important;
	}
	
	/* Form Inputs - Enhanced visibility */
	.stTextInput > div > div > input,
	.stTextArea > div > div > textarea,
	.stSelectbox > div > div > select,
	.stNumberInput > div > div > input,
	.stDateInput > div > div > input,
	.stTimeInput > div > div > input {
		border-radius: 0.75rem !important;
		border: 2px solid var(--input-border) !important;
		background: white !important;
		transition: all 0.2s ease !important;
		padding: 0.75rem 1rem !important;
		font-weight: 500 !important;
	}
	
	.stTextInput > div > div > input:focus,
	.stTextArea > div > div > textarea:focus,
	.stSelectbox > div > div > select:focus,
	.stNumberInput > div > div > input:focus,
	.stDateInput > div > div > input:focus,
	.stTimeInput > div > div > input:focus {
		border-color: #667eea !important;
		box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
		background: white !important;
	}
	
	/* Selectbox - Enhanced */
	.stSelectbox > div > div {
		background: white !important;
		border-radius: 0.75rem !important;
	}
	
	.stSelectbox [data-baseweb="select"] {
		border: 2px solid var(--input-border) !important;
		border-radius: 0.75rem !important;
		background: white !important;
	}
	
	.stSelectbox [data-baseweb="select"]:hover {
		border-color: #667eea !important;
	}
	
	/* File Uploader */
	.stFileUploader > div {
		border: 2px dashed var(--input-border) !important;
		border-radius: 0.75rem !important;
		background: white !important;
		padding: 1.5rem !important;
	}
	
	.stFileUploader > div:hover {
		border-color: #667eea !important;
		background: rgba(102, 126, 234, 0.02) !important;
	}
	
	/* Expander - Enhanced */
	.streamlit-expanderHeader {
		background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%) !important;
		border-radius: 0.75rem !important;
		border: 2px solid var(--border-color) !important;
		font-weight: 600 !important;
		transition: all 0.2s ease !important;
		padding: 1rem 1.25rem !important;
	}
	
	.streamlit-expanderHeader:hover {
		background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%) !important;
		border-color: rgba(102, 126, 234, 0.4) !important;
	}
	
	/* Tabs */
	.stTabs [data-baseweb="tab-list"] {
		gap: 1rem;
		background: transparent;
		border-bottom: 2px solid var(--border-color);
	}
	
	.stTabs [data-baseweb="tab"] {
		background: rgba(255,255,255,0.8);
		border-radius: 0.75rem 0.75rem 0 0;
		padding: 0.875rem 1.75rem;
		font-weight: 600;
		border: 2px solid var(--border-color);
		border-bottom: none;
		transition: all 0.2s ease;
	}
	
	.stTabs [data-baseweb="tab"]:hover {
		background: rgba(102, 126, 234, 0.08);
		border-color: rgba(102, 126, 234, 0.3);
	}
	
	.stTabs [aria-selected="true"] {
		background: var(--primary-gradient) !important;
		color: white !important;
		border-color: transparent !important;
	}
	
	/* Metrics */
	[data-testid="stMetricValue"] {
		font-size: 2rem !important;
		font-weight: 900 !important;
		background: var(--primary-gradient);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}
	
	/* Charts */
	.stPlotlyChart, .stVegaLiteChart {
		border-radius: 1rem;
		overflow: hidden;
		box-shadow: var(--shadow-sm);
		background: white;
		padding: 1rem;
		border: 2px solid var(--border-color);
	}
	
	/* Utility Classes */
	.spacer-16 { height: 16px; }
	.spacer-24 { height: 24px; }
	.spacer-32 { height: 32px; }
	.spacer-48 { height: 48px; }
	
	.footer { 
		text-align: center;
		color: var(--text-muted);
		padding: 3rem 0;
		font-weight: 500;
		border-top: 2px solid var(--border-color);
		margin-top: 4rem;
		background: rgba(255,255,255,0.5);
		border-radius: 1rem;
	}
	
	/* Alerts & Messages */
	.stAlert {
		border-radius: 0.75rem !important;
		border-left-width: 4px !important;
		border: 2px solid !important;
	}
	
	/* Success/Error/Warning/Info styling */
	.stSuccess {
		background: linear-gradient(135deg, rgba(72, 187, 120, 0.1) 0%, rgba(56, 161, 105, 0.1) 100%) !important;
		border-color: rgba(72, 187, 120, 0.4) !important;
	}
	
	.stError {
		background: linear-gradient(135deg, rgba(245, 101, 101, 0.1) 0%, rgba(229, 62, 62, 0.1) 100%) !important;
		border-color: rgba(245, 101, 101, 0.4) !important;
	}
	
	.stWarning {
		background: linear-gradient(135deg, rgba(246, 173, 85, 0.1) 0%, rgba(237, 137, 54, 0.1) 100%) !important;
		border-color: rgba(246, 173, 85, 0.4) !important;
	}
	
	.stInfo {
		background: linear-gradient(135deg, rgba(66, 153, 225, 0.1) 0%, rgba(49, 130, 206, 0.1) 100%) !important;
		border-color: rgba(66, 153, 225, 0.4) !important;
	}
	
	/* Animation */
	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(10px); }
		to { opacity: 1; transform: translateY(0); }
	}
	
	.card, .metric-card, .login-card {
		animation: fadeIn 0.5s ease-out;
	}
	
	/* Checkbox and Radio */
	.stCheckbox, .stRadio {
		background: white;
		padding: 0.5rem;
		border-radius: 0.5rem;
		border: 2px solid var(--border-color);
	}
	
	/* Slider */
	.stSlider > div > div > div {
		background: var(--primary-gradient) !important;
	}
	</style>
	"""
	st.markdown(css, unsafe_allow_html=True)


def top_navbar():
	with st.container():
		st.markdown("<div class='navbar'>", unsafe_allow_html=True)
		with st.container():
			col1, col2 = st.columns([1, 3])
			with col1:
				st.markdown("<div class='nav-brand'>🫶 Community Connect</div>", unsafe_allow_html=True)
			with col2:
				links = st.columns([1,1,1,3])
				with links[0]:
					st.page_link("app.py", label="Home")
				with links[1]:
					st.page_link("pages/1_NGO_Dashboard.py", label="NGOs")
				with links[2]:
					st.page_link("pages/2_Volunteer_Dashboard.py", label="Volunteers")
		st.markdown("</div>", unsafe_allow_html=True)
	return None
