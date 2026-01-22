import re
import uuid
from pathlib import Path
from datetime import datetime

import streamlit as st
from lib.ui import apply_global_styles, top_navbar
from lib.db import init_db, execute, fetchall, fetchone
from lib.auth import register_user, login_user
from lib.gemini_helper import get_wage_rate
from lib.monetisation_helper import (
    calculate_duration_days, 
    calculate_volunteer_value, 
    calculate_task_value,
    format_currency,
    update_volunteer_total_value
)
from lib.file_validation import validate_file_size, format_file_size
from dotenv import load_dotenv

from lib.query_helpers import (
    get_tasks_with_counts, 
    get_task_volunteers, 
    get_all_ngo_volunteers, 
    get_analytics_data, 
    get_ngo_profile,
    clear_ngo_cache,
    clear_task_cache
)
from lib.rate_limiter import check_action_rate_limit

# Load environment variables
load_dotenv()

def get_day_of_week(val):
	"""Get day of week name from date object or string"""
	if not val:
		return ""
	if hasattr(val, 'strftime'):
		return val.strftime("%A")
	try:
		return datetime.strptime(str(val), "%Y-%m-%d").strftime("%A")
	except:
		return ""

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
CERT_DIR = UPLOADS_DIR / "ngo_certificates"
LOGO_DIR = UPLOADS_DIR / "ngo_logos"


def _ensure_dir(path: Path) -> None:
	path.mkdir(parents=True, exist_ok=True)


def _sanitize_identifier(value: str) -> str:
	return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "file"


def save_uploaded_file(uploaded_file, target_dir: Path, name_prefix: str) -> str:
	_ensure_dir(target_dir)
	suffix = Path(uploaded_file.name).suffix or ""
	filename = f"{name_prefix}_{uuid.uuid4().hex}{suffix}"
	destination = target_dir / filename
	with destination.open("wb") as f:
		f.write(uploaded_file.getbuffer())
	return str(destination)


def file_exists(path_str: str | None) -> bool:
	return bool(path_str) and Path(path_str).exists()


def read_binary(path_str: str) -> bytes:
	with Path(path_str).open("rb") as f:
		return f.read()


def _safe_date_value(raw_value):
	if not raw_value:
		return datetime.today().date()
	try:
		return datetime.strptime(str(raw_value), "%Y-%m-%d").date()
	except Exception:
		return datetime.today().date()

st.set_page_config(page_title="NGO Dashboard · Community Connect", page_icon="🏢", layout="wide")
apply_global_styles()
init_db()
_ = top_navbar()

if "ngo_user" not in st.session_state:
	st.session_state["ngo_user"] = None
if "editing_task_id" not in st.session_state:
	st.session_state["editing_task_id"] = None
if "remove_volunteer_context" not in st.session_state:
	st.session_state["remove_volunteer_context"] = None

# Authentication forms
if not st.session_state["ngo_user"]:
	st.subheader("NGO Authentication")
	
	# Dropdown to select Login or Signup
	auth_mode = st.selectbox("Select Action", ["Login", "Sign Up"], key="ngo_auth_mode")
	
	if auth_mode == "Sign Up":
		with st.form("ngo_register"):
			st.markdown("### Register as NGO")
			name = st.text_input("Organization Name")
			email = st.text_input("Email")
			password = st.text_input("Password", type="password")
			phone = st.text_input("Contact Phone")
			location = st.text_input("Location (City)")
			description = st.text_area("About NGO")
			registration_number = st.text_input("Registration Number")
			certificate_file = st.file_uploader(
				"Upload Registration Certificate (Max 10KB)",
				type=["pdf", "png", "jpg", "jpeg"],
				help="Accepted formats: PDF, PNG, JPG. Maximum file size: 10KB",
			)
			if certificate_file:
				st.caption(f"File size: {format_file_size(certificate_file.size)}")
			sub = st.form_submit_button("Create Account", use_container_width=True)
			if sub:
				if not all([name, email, password, registration_number, phone]):
					st.error("Please complete all required fields including registration number.")
					st.stop()
				if "@" not in (email or ""):
					st.error("Please enter a valid email address that includes '@'.")
					st.stop()
				phone_digits = "".join(ch for ch in (phone or "") if ch.isdigit())
				if len(phone_digits) != 10:
					st.error("Contact phone must include exactly 10 digits.")
					st.stop()
				if certificate_file is None:
					st.error("Please upload your NGO registration certificate.")
					st.stop()
				# Validate file size
				is_valid, error_msg = validate_file_size(certificate_file)
				if not is_valid:
					st.error(error_msg)
					st.stop()
				try:
					email_clean = email.lower().strip()
					identifier = _sanitize_identifier(email_clean or name)
					certificate_path = save_uploaded_file(certificate_file, CERT_DIR, f"{identifier}_certificate")
					uid = register_user(
						"ngo",
						name,
						email,
						password,
						location=location,
						description=description,
						registration_number=registration_number,
						phone=phone,
						certificate_path=certificate_path,
						certificate_filename=certificate_file.name,
						certificate_content_type=getattr(certificate_file, "type", None),
					)
					if uid:
						st.success("Account created successfully! Please login.")
					else:
						st.error("Failed to create account. Please try again.")
				except Exception as e:
					st.error(f"Failed: {e}")
					if 'certificate_path' in locals() and file_exists(certificate_path):
						try:
							Path(certificate_path).unlink(missing_ok=True)
						except Exception:
							pass
	else:
		with st.form("ngo_login"):
			st.markdown("### Login as NGO")
			email_l = st.text_input("Email", key="login_email")
			password_l = st.text_input("Password", type="password", key="login_pass")
			login_btn = st.form_submit_button("Login", use_container_width=True)
			if login_btn and email_l and password_l:
				user = login_user("ngo", email_l, password_l)
				if user:
					st.session_state["ngo_user"] = user
					st.rerun()
				else:
					st.error("Invalid credentials")
	st.stop()

current = st.session_state["ngo_user"]

# Fetch NGO data for use throughout the dashboard - Optimized with caching
ngo_data = get_ngo_profile(current["id"])

st.markdown(f"### Welcome, {current['name']}")

# Tabs: Profile, Tasks, Volunteers, Analytics
profile_tab, tasks_tab, volunteers_tab, analytics_tab = st.tabs(["Profile", "Tasks", "Volunteers", "Analytics"])

with profile_tab:
	ngo = get_ngo_profile(current["id"])
	with st.form("ngo_profile"):
		name = st.text_input("Organization Name", value=ngo.get("name", ""))
		email = st.text_input("Email", value=ngo.get("email", ""), disabled=True)
		location = st.text_input("Location", value=ngo.get("location", ""))
		description = st.text_area("About", value=ngo.get("description", ""))
		phone = st.text_input("Contact Phone", value=ngo.get("phone", ""))
		registration_number = st.text_input("Registration Number", value=ngo.get("registration_number", ""))
		st.markdown("**Registration Certificate**")
		current_certificate = ngo.get("certificate_filename") or (Path(ngo.get("certificate_path")).name if file_exists(ngo.get("certificate_path")) else None)
		if current_certificate:
			st.caption(f"Current certificate: {current_certificate}")
		certificate_update = st.file_uploader(
			"Upload Updated Certificate (optional, Max 10KB)",
			type=["pdf", "png", "jpg", "jpeg"],
			key="profile_certificate",
		)
		if certificate_update:
			st.caption(f"File size: {format_file_size(certificate_update.size)}")
		st.markdown("**NGO Logo**")
		if file_exists(ngo.get("logo_path")):
			st.image(ngo.get("logo_path"), caption="Current Logo", width=200)
		logo_update = st.file_uploader(
			"Upload/Update Logo (optional, Max 10KB)",
			type=["png", "jpg", "jpeg", "webp"],
			key="profile_logo",
			help="Recommended: square image, PNG or JPG format. Maximum file size: 10KB",
		)
		if logo_update:
			st.caption(f"File size: {format_file_size(logo_update.size)}")
		save = st.form_submit_button("Save Profile", use_container_width=True)
		if save:
			try:
				# Validate file sizes before saving
				if certificate_update is not None:
					is_valid, error_msg = validate_file_size(certificate_update)
					if not is_valid:
						st.error(f"Certificate: {error_msg}")
						st.stop()
				if logo_update is not None:
					is_valid, error_msg = validate_file_size(logo_update)
					if not is_valid:
						st.error(f"Logo: {error_msg}")
						st.stop()
				
				identifier = _sanitize_identifier(email or name)
				certificate_path = ngo.get("certificate_path")
				certificate_filename = ngo.get("certificate_filename")
				certificate_content_type = ngo.get("certificate_content_type")
				if certificate_update is not None:
					certificate_path = save_uploaded_file(certificate_update, CERT_DIR, f"{identifier}_certificate")
					certificate_filename = certificate_update.name
					certificate_content_type = getattr(certificate_update, "type", None)
				logo_path = ngo.get("logo_path")
				if logo_update is not None:
					logo_path = save_uploaded_file(logo_update, LOGO_DIR, f"{identifier}_logo")

				execute(
					"""UPDATE ngos
					SET name=?,
						location=?,
						description=?,
						phone=?,
						registration_number=?,
						certificate_path=?,
						certificate_filename=?,
						certificate_content_type=?,
						logo_path=?
					WHERE id=?""",
					(
						name,
						location,
						description,
						phone,
						registration_number,
						certificate_path,
						certificate_filename,
						certificate_content_type,
						logo_path,
						current["id"],
					),
				)
				clear_ngo_cache(current["id"])
				st.success("Profile updated")
				st.rerun()
			except Exception as e:
				st.error(f"Failed to update profile: {e}")
	if file_exists(ngo.get("certificate_path")):
		try:
			st.download_button(
				"Download Current Certificate",
				data=read_binary(ngo.get("certificate_path")),
				file_name=ngo.get("certificate_filename") or Path(ngo.get("certificate_path")).name,
				mime=ngo.get("certificate_content_type") or "application/octet-stream",
				key="download_certificate",
			)
		except Exception:
			st.warning("Unable to load certificate file. Please upload a new one if needed.")

with tasks_tab:
	category_options = ["Education", "Healthcare", "Environment", "Community Service", "Disaster Relief", "Animal Welfare", "Elderly Care", "Children & Youth", "Other"]
	urgency_options = ["Low", "Medium", "High", "Critical"]
	age_requirement_options = ["No restriction", "18+", "21+", "16+ with supervision"]
	left, right = st.columns([1,1])
	with left:
		st.subheader("Post a Task")
		# Using session_state for a formless experience
		# Initialize form counter for auto-clear functionality
		if "task_form_counter" not in st.session_state:
			st.session_state.task_form_counter = 0
		
		if "create_task_data" not in st.session_state:
			st.session_state.create_task_data = {
				"title": "", "desc": "", "loc": "", "start_date": None, "end_date": None,
				"hours": 2, "category": "", "skills": "", "max_vols": 1,
				"email": ngo_data.get('email', ''), "phone": ngo_data.get('phone', ''),
				"deadline": None, "urgency": "", "age": "No restriction",
				"physical": "", "equipment": "", "wage": 300.0,
				"work_start_time": None, "work_end_time": None
			}
		
		# Use form counter in widget keys to force reset
		fc = st.session_state.task_form_counter
		
		d = st.session_state.create_task_data
		
		title = st.text_input("Title *", value=d["title"], key=f"ct_title_{fc}")
		desc = st.text_area("Description *", value=d["desc"], key=f"ct_desc_{fc}")
		loc = st.text_input("Location (City) *", value=d["loc"], key=f"ct_loc_{fc}")
		address = st.text_input("Work Address *", value=d.get("address", ""), key=f"ct_address_{fc}", help="Provide the full address where the work will take place")
		
		st.markdown("**Task Duration**")
		col_date1, col_date2 = st.columns(2)
		with col_date1:
			start_date = st.date_input("Start Date *", value=d["start_date"], key=f"ct_start_{fc}")
		with col_date2:
			end_date = st.date_input("End Date *", value=d["end_date"], key=f"ct_end_{fc}")
		
		hours = st.number_input("Estimated Hours/day *", 1, 24, value=d["hours"], key=f"ct_hours_{fc}")
		
		st.markdown("**Work Hours**")
		col_time1, col_time2 = st.columns(2)
		with col_time1:
			work_start_time = st.time_input("Start Time *", value=d["work_start_time"], key=f"ct_work_start_{fc}")
		with col_time2:
			work_end_time = st.time_input("End Time *", value=d["work_end_time"], key=f"ct_work_end_{fc}")
		
		st.markdown("---")
		st.markdown("**Additional Information**")
		
		category = st.selectbox("Category *", [""] + category_options, index=0 if not d["category"] else (category_options.index(d["category"]) + 1 if d["category"] in category_options else 0), key=f"ct_cat_{fc}")
		required_skills = st.text_input("Required Skills (comma separated)", value=d["skills"], key=f"ct_skills_{fc}")
		max_volunteers = st.number_input("Maximum Volunteers Needed", 1, 1000, value=d["max_vols"], key=f"ct_max_{fc}")
		contact_email = st.text_input("Contact Email *", value=d["email"], key=f"ct_email_{fc}")
		contact_phone = st.text_input("Contact Phone *", value=d["phone"], key=f"ct_phone_{fc}")
		deadline = st.date_input("Application Deadline (Optional)", value=d["deadline"], key=f"ct_deadline_{fc}")
		urgency = st.selectbox("Urgency Level *", [""] + urgency_options, index=0 if not d["urgency"] else (urgency_options.index(d["urgency"]) + 1 if d["urgency"] in urgency_options else 0), key=f"ct_urgency_{fc}")
		age_requirement = st.selectbox("Age Requirement", age_requirement_options, index=age_requirement_options.index(d["age"]) if d["age"] in age_requirement_options else 0, key=f"ct_age_{fc}")
		physical_requirements = st.text_area("Physical Requirements (if any)", value=d["physical"], key=f"ct_physical_{fc}")
		equipment_needed = st.text_input("Equipment/Supplies Needed", value=d["equipment"], key=f"ct_equipment_{fc}")
		
		st.markdown("---")
		st.markdown("**💰 Volunteer Work Monetisation**")
		st.caption("Estimate the economic value of volunteer contributions using AI.")
		
		col_wage1, col_wage2 = st.columns([3, 1])
		with col_wage1:
			# Use the session state for wage
			if "temp_wage_rate" not in st.session_state:
				st.session_state.temp_wage_rate = 0
				
			wage_rate_val = st.number_input(
				"Hourly Wage Rate (₹/hour) *", 
				min_value=0.0, 
				max_value=10000.0, 
				value=float(st.session_state.temp_wage_rate), 
				step=50.0,
				key="wage_rate_input_live"
			)
		with col_wage2:
			st.write("") # Spacer
			st.write("") # Spacer
			if st.button("🤖 AI Estimate", help="Estimate based on Title, Description and Location"):
				if title and desc and loc:
					with st.spinner("🤖 Consulting AI..."):
						from lib.gemini_helper import get_wage_rate
						estimated = get_wage_rate(title, desc, loc)
						if estimated:
							st.session_state.temp_wage_rate = estimated
							st.success(f"Estimated: ₹{estimated}")
							st.rerun()
						else:
							st.error("Failed to estimate.")
				else:
					st.warning("Fill Title/Desc/Loc first.")
		
		if st.button("Create Task", use_container_width=True, type="primary"):
			if not check_action_rate_limit(current["id"], "create_task"):
				st.stop()
			required = [title, desc, loc, address, contact_email, contact_phone, category, urgency]
			if not all(required):
				st.error("Missing required fields (*) including Work Address")
			elif not start_date or not end_date:
				st.error("Select dates")
			elif end_date < start_date:
				st.error("Invalid date range")
			elif not work_start_time or not work_end_time:
				st.error("Please select work start and end times")
			elif work_end_time <= work_start_time:
				st.error("End time must be after start time")
			else:
				try:
					deadline_str = str(deadline) if deadline else None
					wage_rate = wage_rate_val
					execute(
						"""INSERT INTO tasks(ngo_id, title, description, location, address, start_date, end_date, hours, status, 
						   category, required_skills, max_volunteers, contact_email, contact_phone, 
						   deadline, urgency, age_requirement, physical_requirements, equipment_needed, wage_rate,
						   work_start_time, work_end_time) 
						   VALUES(?,?,?,?,?,?,?,?, 'open',?,?,?,?,?,?,?,?,?,?,?,?,?)""",
						(current["id"], title, desc, loc, address, str(start_date), str(end_date), int(hours), 
						 category, required_skills, max_volunteers, contact_email, contact_phone,
						 deadline_str, urgency, age_requirement, physical_requirements, equipment_needed, wage_rate,
						 str(work_start_time), str(work_end_time)),
					)
					clear_ngo_cache(current["id"])
					st.success("Task created!")
					# Reset form - increment counter to force new form
					st.session_state.task_form_counter += 1
					
					if "temp_wage_rate" in st.session_state:
						del st.session_state.temp_wage_rate
					
					# Reset create_task_data to defaults
					st.session_state.create_task_data = {
						"title": "", "desc": "", "loc": "", "start_date": None, "end_date": None,
						"hours": 2, "category": "", "skills": "", "max_vols": 1,
						"email": ngo_data.get('email', ''), "phone": ngo_data.get('phone', ''),
						"deadline": None, "urgency": "", "age": "No restriction",
						"physical": "", "equipment": "", "wage": 300.0,
						"work_start_time": None, "work_end_time": None
					}
					st.rerun()
				except Exception as e:
					st.error(f"Error: {e}")
	with right:
		st.subheader("Your Tasks")
		# Using optimized query with cached counts
		tasks = get_tasks_with_counts(current["id"])
		if not tasks:
			st.info("No tasks created yet. Create your first task using the form on the left.")
		else:
			for t in tasks:
				# Use pre-fetched volunteer count from optimized query
				volunteer_count = t.get("volunteer_count", 0)
				max_vols = t.get('max_volunteers', 0)
				
				# Auto-close task if max volunteers reached
				if max_vols and max_vols > 0 and volunteer_count >= max_vols and t.get('status') == 'open':
					execute("UPDATE tasks SET status='closed' WHERE id=?", (t["id"],))
					t['status'] = 'closed'
				
				status_display = t.get('status','open')
				if max_vols and volunteer_count >= max_vols and status_display == 'open':
					status_display = 'full'
				
				with st.expander(f"{t['title']} · {status_display} · Volunteers: {volunteer_count}/{max_vols if max_vols else '∞'}"):
					col1, col2, col3, col4 = st.columns([2,1,1,1])
					with col1:
						st.write(t.get("description", ""))
						# Display date range
						start_d = t.get('start_date') or t.get('date')
						end_d = t.get('end_date') or t.get('date')
						if start_d and end_d:
							day1 = get_day_of_week(start_d)
							day2 = get_day_of_week(end_d)
							if start_d == end_d:
								st.caption(f"Date: {start_d} ({day1}) | Location: {t.get('location','-')} | Hours: {t.get('hours','-')}")
							else:
								st.caption(f"Duration: {start_d} ({day1}) to {end_d} ({day2})")
								st.caption(f"Location: {t.get('location','-')} | Hours: {t.get('hours','-')}")
						else:
							st.caption(f"Location: {t.get('location','-')} | Date: {start_d or '-'} | Hours: {t.get('hours','-')}")
						if t.get('category'):
							st.caption(f"Category: {t.get('category')} | Urgency: {t.get('urgency', 'N/A')}")
						if t.get('required_skills'):
							st.caption(f"Required Skills: {t.get('required_skills')}")
						if t.get('age_requirement'):
							st.caption(f"Age: {t.get('age_requirement')} | Physical: {t.get('physical_requirements') or 'None'}")
						if t.get('equipment_needed'):
							st.caption(f"Supplies: {t.get('equipment_needed')}")
						# Display work hours
						work_start = t.get('work_start_time')
						work_end = t.get('work_end_time')
						if work_start and work_end:
							st.caption(f"⏰ Work Hours: {work_start} - {work_end}")
						if t.get('contact_email') or t.get('contact_phone'):
							st.caption(f"Contact: {t.get('contact_email', '-')} | {t.get('contact_phone', '-')}")
						
						# Display AI Estimate Money
						wage_rate = t.get('wage_rate', 0)
						hours = t.get('hours', 0)
						start_d = t.get('start_date')
						end_d = t.get('end_date')
						if wage_rate and hours and start_d and end_d:
							from lib.monetisation_helper import calculate_duration_days, calculate_task_value
							duration = calculate_duration_days(start_d, end_d)
							est_value = wage_rate * hours * duration
							st.info(f"💰 **AI Estimated Value per Volunteer:** {format_currency(est_value)}")
						if max_vols:
							st.caption(f"Max Volunteers: {max_vols} | Current: {volunteer_count}")
							if volunteer_count >= max_vols:
								st.success(f"✅ Task is full! ({volunteer_count}/{max_vols} volunteers)")
							elif volunteer_count > 0:
								st.info(f"📊 {volunteer_count}/{max_vols} volunteers accepted")
					with col2:
						if st.button("Mark Closed", key=f"close_{t['id']}"):
							execute("UPDATE tasks SET status='closed' WHERE id=?", (t["id"],))
							clear_task_cache(t["id"])
							st.rerun()
					with col3:
						if st.button("Edit", key=f"edit_{t['id']}"):
							st.session_state["editing_task_id"] = t["id"]
							st.rerun()
					with col4:
						if st.button("Delete", key=f"del_{t['id']}"):
							st.session_state["confirm_delete_task_id"] = t["id"]
							st.rerun()
					
					# Delete confirmation "popup" (inline form)
					if st.session_state.get("confirm_delete_task_id") == t["id"]:
						with st.form(f"delete_confirm_{t['id']}"):
							st.error(f"⚠️ Are you sure you want to delete '{t['title']}'?")
							del_reason = st.text_area("Reason for deleting this task *", placeholder="Explain to volunteers why this task is being cancelled...")
							del_col1, del_col2 = st.columns(2)
							with del_col1:
								if st.form_submit_button("Confirm Delete", use_container_width=True):
									if not del_reason.strip():
										st.error("Please provide a reason for deletion.")
									else:
										# Get all volunteers who accepted this task
										affected_volunteers = fetchall(
											"SELECT volunteer_id FROM volunteer_acceptances WHERE task_id=?",
											(t["id"],)
										)
										
										# Create notifications with reason
										for vol in affected_volunteers:
											execute(
												"""INSERT INTO notifications(user_type, user_id, message, notification_type, related_id)
												   VALUES('volunteer', ?, ?, 'task_deleted', ?)""",
												(vol["volunteer_id"],
												 f"Task '{t.get('title', 'N/A')}' has been deleted. Reason: {del_reason.strip()}",
												 t["id"])
											)
										
										# Soft delete task
										execute("UPDATE tasks SET is_deleted=1 WHERE id=?", (t["id"],))
										# We don't delete acceptances so they stay in analytics
										
										clear_task_cache(t["id"])
										del st.session_state["confirm_delete_task_id"]
										st.success(f"Task deleted. {len(affected_volunteers)} volunteer(s) notified.")
										st.rerun()
							with del_col2:
								if st.form_submit_button("Cancel", use_container_width=True):
									del st.session_state["confirm_delete_task_id"]
									st.rerun()
					
					# Show approved and pending volunteers for this task - Optimized with caching
					vols_data = get_task_volunteers(t["id"])
					approved_vols = vols_data['approved']
					pending_vols = vols_data['pending']
					
					if pending_vols:
						st.markdown("---")
						st.markdown("**⏳ Pending Approvals:**")
						for vol in pending_vols:
							with st.container():
								vol_col1, vol_col2 = st.columns([3, 2])
								with vol_col1:
									st.write(f"**{vol['vol_name']}** ({vol.get('vol_email', 'N/A')})")
									st.caption(
										f"📍 {vol.get('vol_location', 'N/A')} | 📅 Available: {vol.get('availability_date', 'N/A')} at {vol.get('availability_time', 'N/A')} | ⏱️ Committed: {vol.get('hours_committed', 0)} hours"
									)
									if vol.get('contact_phone'):
										st.caption(f"📞 Phone: {vol.get('contact_phone')}")
									if vol.get('additional_notes'):
										st.caption(f"📝 Notes: {vol.get('additional_notes')}")
								with vol_col2:
									if st.button("✅ Approve", key=f"approve_{vol['id']}", type="primary", use_container_width=True):
										if st.session_state["ngo_user"] and check_action_rate_limit(st.session_state["ngo_user"]["id"], "approve_volunteer"):
											execute(
												"UPDATE volunteer_acceptances SET approval_status='approved' WHERE id=?",
												(vol["id"],),
											)
											clear_task_cache(t["id"])
											st.success("Volunteer approved!")
											st.rerun()
									if st.button("❌ Reject", key=f"reject_{vol['id']}", type="secondary", use_container_width=True):
										execute(
											"UPDATE volunteer_acceptances SET approval_status='rejected' WHERE id=?",
											(vol["id"],),
										)
										clear_task_cache(t["id"])
										st.warning("Application rejected")
										st.rerun()
								st.markdown("---")
					
					if approved_vols:
						st.markdown("---")
						st.markdown("**Approved Volunteers:**")
						for vol in approved_vols:
							with st.container():
								vol_col1, vol_col2 = st.columns([3, 2])
								current_status = (vol.get("status") or "accepted").lower()
								with vol_col1:
									st.write(f"**{vol['vol_name']}** ({vol.get('vol_email', 'N/A')})")
									st.caption(
										f"📍 {vol.get('vol_location', 'N/A')} | 📅 Available: {vol.get('availability_date', 'N/A')} at {vol.get('availability_time', 'N/A')} | ⏱️ Committed: {vol.get('hours_committed', 0)} hours"
									)
									if vol.get('contact_phone'):
										st.caption(f"📞 Phone: {vol.get('contact_phone')}")
									if vol.get('additional_notes'):
										st.caption(f"📝 Notes: {vol.get('additional_notes')}")
									if current_status == "completed":
										st.success("Status: Work completed")
									elif current_status == "not_completed":
										st.error("Status: Work not completed")
										if vol.get("completion_note"):
											st.caption(f"⚠️ Issue: {vol.get('completion_note')}")
									else:
										st.info("Status: Accepted")
								with vol_col2:
									if st.button("Work Completed", key=f"complete_{vol['id']}", use_container_width=True):
										# Calculate monetisation value
										task_data = fetchone("SELECT start_date, end_date, hours, wage_rate FROM tasks WHERE id=?", (t["id"],))
										if task_data:
											start_date = task_data.get('start_date')
											end_date = task_data.get('end_date')
											hours_per_day = task_data.get('hours', 0)
											wage_rate = task_data.get('wage_rate', 0)
											
											if start_date and end_date and wage_rate:
												# Calculate duration and value
												duration_days = calculate_duration_days(start_date, end_date)
												monetisation_value = calculate_volunteer_value(wage_rate, hours_per_day, duration_days)
												
												# Update volunteer acceptance with value
												execute(
													"""UPDATE volunteer_acceptances 
													   SET status='completed', completion_note=NULL, monetisation_value=? 
													   WHERE id=?""",
													(monetisation_value, vol["id"]),
												)
												
												# Update volunteer's total value generated
												update_volunteer_total_value(vol["volunteer_id"])
												
												clear_task_cache(t["id"])
												st.success(f"Marked as completed! Value generated: {format_currency(monetisation_value)}")
											else:
												# No wage rate set, just mark as completed
												execute(
													"UPDATE volunteer_acceptances SET status='completed', completion_note=NULL WHERE id=?",
													(vol["id"],),
												)
												clear_task_cache(t["id"])
												st.success("Marked as completed")
										else:
											execute(
												"UPDATE volunteer_acceptances SET status='completed', completion_note=NULL WHERE id=?",
												(vol["id"],),
											)
											clear_task_cache(t["id"])
											st.success("Marked as completed")
										st.rerun()
									
									# Check if certificate already pushed
									cert_pushed = vol.get("certificate_pushed", 0)
									if cert_pushed:
										st.caption("Certificate Sent")
									else:
										if st.button("Certificate Sent", key=f"cert_{vol['id']}", use_container_width=True):
											# Mark certificate as pushed
											execute(
												"UPDATE volunteer_acceptances SET certificate_pushed=1 WHERE id=?",
												(vol["id"],)
											)
											# Create notification
											execute(
												"""INSERT INTO notifications(user_type, user_id, message, notification_type, related_id)
												   VALUES('volunteer', ?, ?, 'certificate_pushed', ?)""",
												(vol["volunteer_id"], 
												 f"Certificate has been sent to your Email/Phone Number : {t.get('title', 'N/A')}", 
												 vol["id"])
											)
											clear_task_cache(t["id"])
											st.success("Certificate notification sent!")
											st.rerun()
									
									if st.button("Remove", key=f"remove_{vol['id']}", use_container_width=True):
										st.session_state["remove_volunteer_context"] = {
											"acceptance_id": vol["id"],
											"task_id": t["id"],
											"vol_name": vol.get("vol_name", "this volunteer"),
											"task_title": t.get("title", "this task"),
										}
										st.rerun()
									with st.form(f"not_completed_form_{vol['id']}"):
										issue = st.text_area(
											"Describe the issue",
											value=vol.get("completion_note", ""),
											key=f"issue_{vol['id']}",
											label_visibility="collapsed",
											placeholder="Describe why the work was not completed",
										)
										if st.form_submit_button("Work Not Done", use_container_width=True):
											if issue.strip():
												# Mark as not completed - NO value calculation
												execute(
													"UPDATE volunteer_acceptances SET status='not_completed', completion_note=?, monetisation_value=0 WHERE id=?",
													(issue.strip(), vol["id"]),
												)
												# Update volunteer total (will exclude this task)
												update_volunteer_total_value(vol["volunteer_id"])
												clear_task_cache(t["id"])
												st.warning("Marked as not completed")
												st.rerun()
											else:
												st.warning("Please provide a brief description of the issue.")
								st.markdown("---")

			edit_task_id = st.session_state.get("editing_task_id")
			if edit_task_id:
				task_to_edit = fetchone("SELECT * FROM tasks WHERE id=? AND ngo_id=?", (edit_task_id, current["id"]))
				if not task_to_edit:
					st.session_state["editing_task_id"] = None
				else:
					st.markdown("---")
					st.markdown("### Edit Task")
					with st.form(f"edit_task_form_{edit_task_id}"):
						edit_title = st.text_input("Title *", value=task_to_edit.get("title", ""), key=f"edit_title_{edit_task_id}")
						edit_desc = st.text_area("Description *", value=task_to_edit.get("description", ""), key=f"edit_desc_{edit_task_id}")
						edit_loc = st.text_input("Location (City) *", value=task_to_edit.get("location", ""), key=f"edit_loc_{edit_task_id}")
						edit_address = st.text_input("Work Address *", value=task_to_edit.get("address", ""), key=f"edit_address_{edit_task_id}")
						
						# Date range fields
						st.markdown("**Task Duration**")
						col_edit_date1, col_edit_date2 = st.columns(2)
						with col_edit_date1:
							edit_start_date = st.date_input(
								"Start Date *", 
								value=_safe_date_value(task_to_edit.get("start_date") or task_to_edit.get("date")), 
								key=f"edit_start_date_{edit_task_id}"
							)
							if edit_start_date:
								st.caption(f"Day: {get_day_of_week(edit_start_date)}")
						with col_edit_date2:
							edit_end_date = st.date_input(
								"End Date *", 
								value=_safe_date_value(task_to_edit.get("end_date") or task_to_edit.get("date")), 
								key=f"edit_end_date_{edit_task_id}"
							)
							if edit_end_date:
								st.caption(f"Day: {get_day_of_week(edit_end_date)}")
						
						edit_hours = st.number_input("Estimated Hours/day *", 1, 200, int(task_to_edit.get("hours") or 1), key=f"edit_hours_{edit_task_id}")

						st.markdown("---")
						st.markdown("**Additional Information**")

						current_category = task_to_edit.get("category") or category_options[0]
						category_index = category_options.index(current_category) if current_category in category_options else 0
						edit_category = st.selectbox(
							"Category",
							category_options,
							index=category_index,
							key=f"edit_category_{edit_task_id}",
						)
						edit_required_skills = st.text_input(
							"Required Skills (comma separated)",
							value=task_to_edit.get("required_skills", ""),
							key=f"edit_skills_{edit_task_id}",
						)
						edit_max_volunteers = st.number_input(
							"Maximum Volunteers Needed",
							1,
							100,
							int(task_to_edit.get("max_volunteers") or 1),
							key=f"edit_max_vols_{edit_task_id}",
						)
						edit_contact_email = st.text_input(
							"Contact Email *",
							value=task_to_edit.get("contact_email", ""),
							key=f"edit_contact_email_{edit_task_id}",
						)
						edit_contact_phone = st.text_input(
							"Contact Phone *",
							value=task_to_edit.get("contact_phone", ""),
							key=f"edit_contact_phone_{edit_task_id}",
						)
						deadline_enabled = st.checkbox(
							"Set Application Deadline",
							value=bool(task_to_edit.get("deadline")),
							key=f"edit_deadline_enabled_{edit_task_id}",
						)
						edit_deadline_value = None
						if deadline_enabled:
							edit_deadline_value = st.date_input(
								"Application Deadline",
								value=_safe_date_value(task_to_edit.get("deadline")),
								key=f"edit_deadline_{edit_task_id}",
							)
						current_urgency = task_to_edit.get("urgency") or urgency_options[0]
						urgency_index = urgency_options.index(current_urgency) if current_urgency in urgency_options else 0
						edit_urgency = st.selectbox(
							"Urgency Level",
							urgency_options,
							index=urgency_index,
							key=f"edit_urgency_{edit_task_id}",
						)
						current_age_req = task_to_edit.get("age_requirement") or age_requirement_options[0]
						age_index = age_requirement_options.index(current_age_req) if current_age_req in age_requirement_options else 0
						edit_age_requirement = st.selectbox(
							"Age Requirement",
							age_requirement_options,
							index=age_index,
							key=f"edit_age_req_{edit_task_id}",
						)
						edit_physical = st.text_area(
							"Physical Requirements (if any)",
							value=task_to_edit.get("physical_requirements", ""),
							key=f"edit_physical_{edit_task_id}",
						)
						edit_equipment = st.text_input(
							"Equipment/Supplies Needed",
							value=task_to_edit.get("equipment_needed", ""),
							key=f"edit_equipment_{edit_task_id}",
						)

						# Monetisation Index - Wage Rate
						st.markdown("---")
						st.markdown("**💰 Volunteer Work Monetisation**")
						edit_wage_rate = st.number_input(
							"Hourly Wage Rate (₹/hour) *", 
							min_value=0.0, 
							max_value=10000.0, 
							value=float(task_to_edit.get("wage_rate") or 300.0), 
							step=50.0,
							key=f"edit_wage_{edit_task_id}",
							help="Market hourly wage rate for this task"
						)

						update_btn = st.form_submit_button("Update Task", use_container_width=True)
						if update_btn:
							if not check_action_rate_limit(current["id"], "edit_task"):
								st.stop()
							required_fields = [edit_title, edit_desc, edit_loc, edit_address, edit_contact_email, edit_contact_phone]
							if not all(required_fields):
								st.error("Please complete all required fields including Work Address and contact details.")
							elif not edit_start_date or not edit_end_date:
								st.error("Please select both start and end dates.")
							elif edit_end_date < edit_start_date:
								st.error("End date cannot be before start date.")
							else:
								try:
									# Change detection
									critical_fields = {
										"start_date": str(edit_start_date),
										"end_date": str(edit_end_date),
										"hours": int(edit_hours),
										"location": edit_loc,
										"address": edit_address,
										"contact_email": edit_contact_email,
										"contact_phone": edit_contact_phone,
										"urgency": edit_urgency,
										"physical_requirements": edit_physical,
										"age_requirement": edit_age_requirement,
										"equipment_needed": edit_equipment
									}
									
									changes = []
									for field, new_val in critical_fields.items():
										old_val = task_to_edit.get(field)
										# Handle type conversion for comparison
										if field == "hours":
											old_val = int(old_val) if old_val is not None else 0
										elif field in ["start_date", "end_date"]:
											old_val = str(old_val) if old_val else ""
										
										if str(old_val) != str(new_val):
											# Special formatting for field names
											field_name = field.replace('_', ' ').capitalize()
											changes.append(field_name)
									
									# Update database
									execute(
										"""UPDATE tasks
										SET title=?,
											description=?,
											location=?,
											address=?,
											start_date=?,
											end_date=?,
											hours=?,
											category=?,
											required_skills=?,
											max_volunteers=?,
											contact_email=?,
											contact_phone=?,
											deadline=?,
											urgency=?,
											age_requirement=?,
											physical_requirements=?,
											equipment_needed=?,
											wage_rate=?
										WHERE id=?""",
										(
											edit_title,
											edit_desc,
											edit_loc,
											edit_address,
											str(edit_start_date),
											str(edit_end_date),
											int(edit_hours),
											edit_category,
											edit_required_skills,
											int(edit_max_volunteers),
											edit_contact_email,
											edit_contact_phone,
											str(edit_deadline_value) if edit_deadline_value else None,
											edit_urgency,
											edit_age_requirement,
											edit_physical,
											edit_equipment,
											edit_wage_rate,
											edit_task_id,
										),
									)
									
									# Notify volunteers if changes detected
									if changes:
										affected_volunteers = fetchall(
											"SELECT volunteer_id FROM volunteer_acceptances WHERE task_id=? AND approval_status='approved'",
											(edit_task_id,)
										)
										change_list = ", ".join(changes)
										for vol in affected_volunteers:
											execute(
												"""INSERT INTO notifications(user_type, user_id, message, notification_type, related_id)
												   VALUES('volunteer', ?, ?, 'task_updated', ?)""",
												(vol["volunteer_id"],
												 f"Update for '{edit_title}': {change_list} have been changed. Please check the latest details.",
												 edit_task_id)
											)
									
									clear_task_cache(edit_task_id)
									st.success("Task updated successfully.")
									st.session_state["editing_task_id"] = None
									st.rerun()
								except Exception as e:
									st.error(f"Failed to update task: {e}")
					if st.button("Cancel Editing", key="cancel_edit_task"):
						st.session_state["editing_task_id"] = None
						st.rerun()

		remove_context = st.session_state.get("remove_volunteer_context")
		if remove_context:
			st.markdown("---")
			vol_name = remove_context.get("vol_name", "this volunteer")
			task_title = remove_context.get("task_title", "this task")
			st.warning("Are you sure you want to remove the volunteer from task?")
			st.caption(f"{vol_name} → {task_title}")
			confirm_col, cancel_col = st.columns(2)
			if confirm_col.button("Yes", key="confirm_remove_yes"):
				execute("DELETE FROM volunteer_acceptances WHERE id=?", (remove_context["acceptance_id"],))
				task_info = fetchone("SELECT id, status, max_volunteers FROM tasks WHERE id=?", (remove_context["task_id"],))
				if task_info and (task_info.get("status") == 'closed'):
					max_vols = task_info.get("max_volunteers") or 0
					if max_vols:
						count_after = fetchone(
							"""
							SELECT COUNT(*) as count
							FROM volunteer_acceptances
							WHERE task_id=? AND approval_status='approved' AND (status IS NULL OR status IN ('accepted','completed'))
							""",
							(remove_context["task_id"],),
						)
						current_count = count_after["count"] if count_after else 0
						if current_count < max_vols:
							execute("UPDATE tasks SET status='open' WHERE id=?", (remove_context["task_id"],))
				clear_task_cache(remove_context["task_id"])
				st.session_state["remove_volunteer_context"] = None
				st.rerun()
			if cancel_col.button("No", key="confirm_remove_cancel"):
				st.session_state["remove_volunteer_context"] = None
				st.rerun()

with volunteers_tab:
	st.subheader("All Accepted Volunteers")
	
	# Optimized query with caching
	all_volunteers = get_all_ngo_volunteers(current["id"])
	
	if not all_volunteers:
		st.info("No volunteers have accepted any tasks yet.")
	else:
		# Filter options
		col1, col2 = st.columns(2)
		with col1:
			filter_task = st.selectbox("Filter by Task", ["All"] + list(set(v.get('task_title', '') for v in all_volunteers)))
		with col2:
			filter_category = st.selectbox("Filter by Category", ["All"] + list(set(v.get('category', '') for v in all_volunteers if v.get('category'))))
		
		filtered_vols = all_volunteers
		if filter_task != "All":
			filtered_vols = [v for v in filtered_vols if v.get('task_title') == filter_task]
		if filter_category != "All":
			filtered_vols = [v for v in filtered_vols if v.get('category') == filter_category]
		
		st.metric("Total Volunteers", len(filtered_vols))
		
		for vol in filtered_vols:
			with st.expander(f"{vol['vol_name']} → {vol['task_title']} · {vol.get('category', 'N/A')}"):
				col1, col2 = st.columns(2)
				with col1:
					st.markdown("**Volunteer Information:**")
					st.write(f"**Name:** {vol['vol_name']}")
					st.write(f"**Email:** {vol.get('vol_email', 'N/A')}")
					st.write(f"**Location:** {vol.get('vol_location', 'N/A')}")
					if vol.get('vol_skills'):
						st.write(f"**Skills:** {vol.get('vol_skills')}")
				with col2:
					st.markdown("**Commitment Details:**")
					st.write(f"**Task:** {vol['task_title']}")
					st.write(f"**Category:** {vol.get('category', 'N/A')}")
					st.write(f"**Available Date:** {vol.get('availability_date', 'N/A')}")
					st.write(f"**Available Time:** {vol.get('availability_time', 'N/A')}")
					st.write(f"**Hours Committed:** {vol.get('hours_committed', 0)} hours")
					status_text = (vol.get('status') or 'accepted').replace('_', ' ').title()
					st.write(f"**Status:** {status_text}")
					if vol.get('status') == 'not_completed' and vol.get('completion_note'):
						st.warning(f"Issue reported: {vol.get('completion_note')}")
					if vol.get('contact_phone'):
						st.write(f"**Phone:** {vol.get('contact_phone')}")
					if vol.get('additional_notes'):
						st.write(f"**Notes:** {vol.get('additional_notes')}")

with analytics_tab:
	st.subheader("📊 NGO Analytics & Statistics")
	
	# Optimized query with caching for analytics
	analytics = get_analytics_data(current["id"])
	all_tasks = analytics['tasks']
	all_acceptances = analytics['acceptances']
	
	if not all_tasks:
		st.info("No tasks created yet. Create tasks to see analytics!")
	else:
		import pandas as pd
		from datetime import datetime
		
		# Use pre-calculated statistics
		total_tasks = analytics['total_tasks']
		open_tasks = analytics['open_tasks']
		closed_tasks = analytics['closed_tasks']
		total_volunteers = analytics['total_volunteers']
		total_hours_committed = analytics['total_hours']
		total_value_generated = analytics['total_value']
		
		# Display metrics with modern cards
		st.markdown("<div class='spacer-24'></div>", unsafe_allow_html=True)
		col1, col2, col3, col4, col5 = st.columns(5)
		
		with col1:
			st.markdown(f"""
			<div class='metric-card'>
				<div style='font-size: 2rem; margin-bottom: 0.5rem;'>📋</div>
				<div class='metric-value'>{total_tasks}</div>
				<div class='metric-label'>Total Tasks</div>
			</div>
			""", unsafe_allow_html=True)
		
		with col2:
			st.markdown(f"""
			<div class='metric-card'>
				<div style='font-size: 2rem; margin-bottom: 0.5rem;'>✅</div>
				<div class='metric-value'>{open_tasks}</div>
				<div class='metric-label'>Open Tasks</div>
			</div>
			""", unsafe_allow_html=True)
		
		with col3:
			st.markdown(f"""
			<div class='metric-card'>
				<div style='font-size: 2rem; margin-bottom: 0.5rem;'>👥</div>
				<div class='metric-value'>{total_volunteers}</div>
				<div class='metric-label'>Total Volunteers</div>
			</div>
			""", unsafe_allow_html=True)
		
		with col4:
			st.markdown(f"""
			<div class='metric-card'>
				<div style='font-size: 2rem; margin-bottom: 0.5rem;'>⏱️</div>
				<div class='metric-value'>{total_hours_committed}</div>
				<div class='metric-label'>Hours Committed</div>
			</div>
			""", unsafe_allow_html=True)
		
		with col5:
			st.markdown(f"""
			<div class='metric-card'>
				<div style='font-size: 2rem; margin-bottom: 0.5rem;'>💰</div>
				<div class='metric-value'>{format_currency(total_value_generated)}</div>
				<div class='metric-label'>Value Generated</div>
			</div>
			""", unsafe_allow_html=True)
		
		st.markdown("---")
		
		# Use local variables for breakdown calculations (already loaded from analytics)
		category_data = {}
		for task in all_tasks:
			cat = task.get('category', 'Other')
			if cat not in category_data:
				category_data[cat] = {'tasks': 0, 'volunteers': 0, 'hours': 0, 'value': 0}
			category_data[cat]['tasks'] += 1
		
		for acc in all_acceptances:
			cat = acc.get('category', 'Other')
			if cat in category_data:
				category_data[cat]['volunteers'] += 1
				category_data[cat]['hours'] += acc.get('hours_committed', 0) or 0
				# Only add value for completed tasks
				if acc.get('status') == 'completed' and acc.get('approval_status') == 'approved':
					category_data[cat]['value'] += acc.get('monetisation_value', 0) or 0
		
		if category_data:
			st.markdown("<div class='spacer-32'></div>", unsafe_allow_html=True)
			st.markdown("""
			<div style='text-align: center; margin-bottom: 2rem;'>
				<h3 style='font-size: 1.75rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
					📈 Tasks by Category
				</h3>
			</div>
			""", unsafe_allow_html=True)
			
			category_df = pd.DataFrame({
				'Category': list(category_data.keys()),
				'Tasks': [category_data[c]['tasks'] for c in category_data.keys()],
				'Volunteers': [category_data[c]['volunteers'] for c in category_data.keys()],
				'Hours': [category_data[c]['hours'] for c in category_data.keys()],
				'Value (₹)': [category_data[c]['value'] for c in category_data.keys()]
			})
			
			col1, col2, col3, col4 = st.columns(4)
			with col1:
				st.markdown("**📋 Tasks**")
				st.bar_chart(category_df.set_index('Category')['Tasks'], use_container_width=True, color="#667eea")
			with col2:
				st.markdown("**👥 Volunteers**")
				st.bar_chart(category_df.set_index('Category')['Volunteers'], use_container_width=True, color="#764ba2")
			with col3:
				st.markdown("**⏱️ Hours**")
				st.bar_chart(category_df.set_index('Category')['Hours'], use_container_width=True, color="#f093fb")
			with col4:
				st.markdown("**💰 Value Generated**")
				st.bar_chart(category_df.set_index('Category')['Value (₹)'], use_container_width=True, color="#f5576c")
		
		# Task status breakdown
		st.markdown("<div class='spacer-32'></div>", unsafe_allow_html=True)
		st.markdown("""
		<div style='text-align: center; margin-bottom: 2rem;'>
			<h3 style='font-size: 1.75rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
				📊 Task Status Overview
			</h3>
		</div>
		""", unsafe_allow_html=True)
		status_df = pd.DataFrame({
			'Status': ['Open', 'Closed'],
			'Count': [open_tasks, closed_tasks]
		})
		st.bar_chart(status_df.set_index('Status')['Count'], use_container_width=True, color="#667eea")
		
		# Volunteer engagement by task
		if all_acceptances:
			st.markdown("<div class='spacer-32'></div>", unsafe_allow_html=True)
			st.markdown("""
			<div style='text-align: center; margin-bottom: 2rem;'>
				<h3 style='font-size: 1.75rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
					👥 Volunteer Engagement
				</h3>
			</div>
			""", unsafe_allow_html=True)
			task_engagement = {}
			for acc in all_acceptances:
				task_title = acc.get('title', 'Unknown')
				if task_title not in task_engagement:
					task_engagement[task_title] = 0
				task_engagement[task_title] += 1
			
			engagement_df = pd.DataFrame({
				'Task': list(task_engagement.keys()),
				'Volunteers': list(task_engagement.values())
			}).sort_values('Volunteers', ascending=False).head(10)
			
			st.bar_chart(engagement_df.set_index('Task')['Volunteers'], use_container_width=True, color="#764ba2")

st.markdown("<div class='spacer-24'></div>", unsafe_allow_html=True)
if st.button("Logout", type="secondary"):
	st.session_state["ngo_user"] = None
	st.session_state["editing_task_id"] = None
	st.rerun()
