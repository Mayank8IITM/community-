import streamlit as st
from datetime import date, datetime
from lib.ui import apply_global_styles, top_navbar
from lib.db import init_db, execute, fetchall, fetchone
from lib.auth import register_user, login_user
from lib.monetisation_helper import format_currency

def get_day_of_week(date_obj):
	"""Get day of week name from date object"""
	if date_obj:
		return date_obj.strftime("%A")
	return ""

def is_weekend_day(date_str):
	"""Check if a date string is a weekend (Saturday or Sunday)"""
	if not date_str:
		return False
	try:
		date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
		# weekday(): Monday=0, Sunday=6
		return date_obj.weekday() in [5, 6]  # Saturday=5, Sunday=6
	except:
		return False

def is_weekday_day(date_str):
	"""Check if a date string is a weekday (Monday-Friday)"""
	if not date_str:
		return False
	try:
		date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
		return date_obj.weekday() in [0, 1, 2, 3, 4]  # Monday=0 to Friday=4
	except:
		return False

CATEGORY_CHOICES = [
	"Education",
	"Healthcare",
	"Environment",
	"Community Service",
	"Disaster Relief",
	"Animal Welfare",
	"Elderly Care",
	"Children & Youth",
	"Other",
]


def _min_age_from_requirement(requirement: str | None) -> int:
	if not requirement:
		return 0
	value = requirement.strip().lower()
	if "no restriction" in value:
		return 0
	numeric = "".join(ch for ch in requirement if ch.isdigit())
	try:
		return int(numeric) if numeric else 0
	except ValueError:
		return 0

st.set_page_config(page_title="Volunteer Dashboard · Community Connect", page_icon="🧑‍🤝‍🧑", layout="wide")
apply_global_styles()
init_db()
_ = top_navbar()

if "vol_user" not in st.session_state:
	st.session_state["vol_user"] = None

# Authentication forms
if not st.session_state["vol_user"]:
	st.subheader("Volunteer Authentication")
	
	# Dropdown to select Login or Signup
	auth_mode = st.selectbox("Select Action", ["Login", "Sign Up"], key="vol_auth_mode")
	
	if auth_mode == "Sign Up":
		with st.form("vol_register"):
			st.markdown("### Register as Volunteer")
			name = st.text_input("Full Name")
			email = st.text_input("Email")
			password = st.text_input("Password", type="password")
			location = st.text_input("Location (City)")
			skills = st.text_input("Skills (comma separated)")
			phone = st.text_input("Mobile Number")
			gender = st.selectbox("Gender", ["Female", "Male", "Non-binary", "Prefer not to say", "Other"])
			age = st.number_input("Age (years)", min_value=12, max_value=100, value=18, step=1)
			sub = st.form_submit_button("Create Account", use_container_width=True)
			if sub:
				required_fields = [name, email, password, phone]
				if not all(required_fields):
					st.error("Please fill in all required fields including mobile number.")
				else:
					if "@" not in (email or ""):
						st.error("Please enter a valid email address that includes '@'.")
					else:
						phone_digits = "".join(ch for ch in (phone or "") if ch.isdigit())
						if len(phone_digits) != 10:
							st.error("Mobile number must include exactly 10 digits.")
						else:
							try:
								uid = register_user(
									"volunteer",
									name,
									email,
									password,
									location=location,
									skills=skills,
									phone=phone,
									gender=gender,
									age=int(age),
								)
								st.success("Account created successfully! Please login.")
							except Exception as e:
								st.error(f"Failed: {e}")
	else:
		with st.form("vol_login"):
			st.markdown("### Login as Volunteer")
			email_l = st.text_input("Email", key="v_login_email")
			password_l = st.text_input("Password", type="password", key="v_login_pass")
			login_btn = st.form_submit_button("Login", use_container_width=True)
			if login_btn and email_l and password_l:
				user = login_user("volunteer", email_l, password_l)
				if user:
					st.session_state["vol_user"] = user
					st.rerun()
				else:
					st.error("Invalid credentials")
	st.stop()

current = st.session_state["vol_user"]
volunteer_record = fetchone("SELECT * FROM volunteers WHERE id=?", (current["id"],)) or {}

st.markdown(f"### Welcome, {current['name']}")

# Check for unread notifications
notifications = fetchall(
	"SELECT * FROM notifications WHERE user_type='volunteer' AND user_id=? AND is_read=0 ORDER BY created_at DESC",
	(current["id"],)
)

if notifications:
	st.info(f"🔔 You have {len(notifications)} new notification(s)")
	for notif in notifications:
		notif_type = notif.get('notification_type', 'notification').replace('_', ' ').title()
		with st.expander(f"📬 {notif_type} - {notif.get('created_at', '')[:16]}"):
			st.write(notif.get('message', ''))
			if st.button("Mark as Read", key=f"read_{notif['id']}"):
				execute("UPDATE notifications SET is_read=1 WHERE id=?", (notif["id"],))
				st.rerun()

# Tabs: Browse Tasks, My Accepted Tasks, Profile
browse_tab, accepted_tab, profile_tab = st.tabs(["Browse Tasks", "My Accepted Tasks", "Profile"])

with browse_tab:
	st.subheader("Find Opportunities")
	col_top = st.columns(4)
	with col_top[0]:
		city = st.text_input("Filter by City")
	with col_top[1]:
		category_filter = st.selectbox("Category", ["All"] + CATEGORY_CHOICES)
	with col_top[2]:
		status = st.selectbox("Status", ["open", "closed", "all"], index=0)
	with col_top[3]:
		skills_filter = st.text_input("Skills (comma separated)")
	
	col_bottom = st.columns(4)
	with col_bottom[0]:
		day_type_filter = st.selectbox("Day Type", ["All", "Weekend", "Weekday"], index=0)
	with col_bottom[1]:
		max_hours = st.number_input("Max Hours", min_value=0, max_value=500, value=0, step=1)
	with col_bottom[2]:
		default_age = int(volunteer_record.get("age") or 0)
		age_filter = st.number_input("My Age (years)", min_value=0, max_value=120, value=default_age, step=1)
	
	date_range = None
	if st.checkbox("Filter by Date Range", key="vol_date_range_toggle"):
		date_input = st.date_input("Select Date Range", value=(date.today(), date.today()), key="vol_date_range")
		if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
			start_date, end_date = date_input
			if start_date and end_date:
				date_range = (start_date, end_date)
		elif date_input:
			date_range = (date_input, date_input)
	
	query = "SELECT tasks.*, ngos.name as ngo_name FROM tasks JOIN ngos ON ngos.id = tasks.ngo_id WHERE tasks.is_deleted = 0"
	params = []
	if city:
		query += " AND tasks.location LIKE ?"
		params.append(f"%{city}%")
	if status != "all":
		query += " AND tasks.status = ?"
		params.append(status)
	if category_filter != "All":
		query += " AND tasks.category = ?"
		params.append(category_filter)
	if max_hours > 0:
		query += " AND IFNULL(tasks.hours, 0) <= ?"
		params.append(int(max_hours))
	if date_range:
		start_date, end_date = date_range
		query += " AND date(tasks.date) BETWEEN ? AND ?"
		params.extend([str(start_date), str(end_date)])
	if skills_filter:
		skill_terms = [term.strip() for term in skills_filter.split(",") if term.strip()]
		for term in skill_terms:
			query += " AND IFNULL(tasks.required_skills, '') LIKE ?"
			params.append(f"%{term}%")
	query += " ORDER BY tasks.id DESC"

	tasks = fetchall(query, tuple(params))
	# Apply age filter
	if age_filter > 0:
		tasks = [
			t for t in tasks if _min_age_from_requirement(t.get('age_requirement')) <= age_filter or not t.get('age_requirement')
		]
	# Apply weekend/weekday filter
	if day_type_filter == "Weekend":
		tasks = [
			t for t in tasks 
			if is_weekend_day(t.get('start_date') or t.get('date')) or is_weekend_day(t.get('end_date') or t.get('date'))
		]
	elif day_type_filter == "Weekday":
		tasks = [
			t for t in tasks 
			if is_weekday_day(t.get('start_date') or t.get('date')) or is_weekday_day(t.get('end_date') or t.get('date'))
		]
	if not tasks:
		st.info("No tasks found matching your criteria.")
	else:
		for t in tasks:
			# Check if volunteer already accepted this task
			already_accepted = fetchone(
				"SELECT * FROM volunteer_acceptances WHERE task_id=? AND volunteer_id=?",
				(t["id"], current["id"])
			)
			
			# Get current volunteer count (only approved)
			count_result = fetchone(
				"""
				SELECT COUNT(*) as count
				FROM volunteer_acceptances
				WHERE task_id=? AND approval_status='approved' AND (status IS NULL OR status IN ('accepted','completed'))
				""",
				(t["id"],),
			)
			volunteer_count = count_result["count"] if count_result else 0
			
			max_vols = t.get('max_volunteers') or None
			is_full = max_vols and volunteer_count >= max_vols
			
			with st.expander(f"{t['title']} · {t['ngo_name']} · {t.get('status','open')} · Volunteers: {volunteer_count}/{max_vols if max_vols else '∞'}"):
				st.write(t.get("description", ""))
				# Display date range
				start_d = t.get('start_date') or t.get('date')
				end_d = t.get('end_date') or t.get('date')
				if start_d and end_d:
					try:
						start_obj = datetime.strptime(start_d, "%Y-%m-%d").date()
						end_obj = datetime.strptime(end_d, "%Y-%m-%d").date()
						if start_obj == end_obj:
							st.caption(f"Date: {start_d} ({get_day_of_week(start_obj)}) | City: {t.get('location','-')} | Hours: {t.get('hours','-')}")
						else:
							st.caption(f"Duration: {start_d} ({get_day_of_week(start_obj)}) to {end_d} ({get_day_of_week(end_obj)})")
							st.caption(f"City: {t.get('location','-')} | Hours: {t.get('hours','-')}")
					except:
						st.caption(f"City: {t.get('location','-')} | Date: {start_d} | Hours: {t.get('hours','-')}")
				else:
					st.caption(f"City: {t.get('location','-')} | Date: {start_d or '-'} | Hours: {t.get('hours','-')}")
				
				# AI Estimate Money
				if t.get('wage_rate') and t.get('hours') and start_d and end_d:
					from lib.monetisation_helper import calculate_duration_days
					duration = calculate_duration_days(start_d, end_d)
					est_val = t['wage_rate'] * t['hours'] * duration
					st.info(f"💰 **AI Estimated Value generated from this task :** {format_currency(est_val)}")
				
				if t.get('address'):
					st.caption(f"📍 Address: {t.get('address')}")
				
				# Display additional task information if available
				if t.get('category'):
					st.caption(f"Category: {t.get('category')} | Urgency: {t.get('urgency', 'N/A')}")
				if t.get('required_skills'):
					st.caption(f"Required Skills: {t.get('required_skills')}")
				if t.get('max_volunteers'):
					st.caption(f"Max Volunteers Needed: {t.get('max_volunteers')} | Current: {volunteer_count}")
				if t.get('age_requirement'):
					st.caption(f"Age Requirement: {t.get('age_requirement')}")
				if t.get('contact_email'):
					st.caption(f"Contact Email: {t.get('contact_email')}")
				if t.get('contact_phone'):
					st.caption(f"Contact Phone: {t.get('contact_phone')}")
				if t.get('deadline'):
					st.caption(f"Application Deadline: {t.get('deadline')}")
				if t.get('physical_requirements'):
					st.caption(f"Physical Requirements: {t.get('physical_requirements')}")
				if t.get('equipment_needed'):
					st.caption(f"Equipment Needed: {t.get('equipment_needed')}")
				# Display work hours
				work_start = t.get('work_start_time')
				work_end = t.get('work_end_time')
				if work_start and work_end:
					st.caption(f"⏰ Work Hours: {work_start} - {work_end}")
				
				st.markdown("---")
				
				if t.get('status') == 'closed':
					st.warning("This task is closed.")
				elif already_accepted:
					approval_status = (already_accepted.get("approval_status") or "pending").lower()
					status = (already_accepted.get("status") or "accepted").lower()
					
					if approval_status == "rejected":
						st.error("❌ Your application was rejected by the NGO.")
						st.caption("You can apply again if the task is still open.")
						if st.button("Remove from My List", key=f"remove_rejected_{t['id']}", type="secondary"):
							execute("DELETE FROM volunteer_acceptances WHERE id=?", (already_accepted["id"],))
							st.rerun()
					elif approval_status == "pending":
						st.warning("⏳ Your application is pending NGO approval.")
						col_view1, col_view2 = st.columns([2, 1])
						with col_view1:
							st.info(f"**Availability:** {already_accepted.get('availability_date', 'N/A')} | **Hours Committed:** {already_accepted.get('hours_committed', 'N/A')} hours")
						with col_view2:
							if st.button("Withdraw Application", key=f"withdraw_pending_{t['id']}", type="secondary"):
								execute("DELETE FROM volunteer_acceptances WHERE id=?", (already_accepted["id"],))
								st.success("Application withdrawn.")
								st.rerun()
					else:  # approved
						if status == "completed":
							st.success("✅ This task has been marked as completed by the NGO.")
						elif status == "not_completed":
							st.error("⚠️ This task was marked as not completed by the NGO.")
							if already_accepted.get("completion_note"):
								st.warning(f"Issue reported by NGO: {already_accepted.get('completion_note')}")
						else:
							st.success("✅ You have been approved for this task!")
						col_view1, col_view2 = st.columns([2, 1])
						with col_view1:
							st.info(f"**Availability:** {already_accepted.get('availability_date', 'N/A')} | **Hours Committed:** {already_accepted.get('hours_committed', 'N/A')} hours")
						with col_view2:
							if status == "accepted":
								if st.button("Withdraw", key=f"withdraw_{t['id']}", type="secondary"):
									execute("DELETE FROM volunteer_acceptances WHERE id=?", (already_accepted["id"],))
									# Reopen task if it was closed and now has space
									if t.get('status') == 'closed':
										max_vols = t.get('max_volunteers', 0)
										if max_vols:
											count_after = fetchone(
												"""
												SELECT COUNT(*) as count
												FROM volunteer_acceptances
												WHERE task_id=? AND approval_status='approved' AND (status IS NULL OR status IN ('accepted','completed'))
												""",
												(t["id"],),
											)
											current_count = count_after["count"] if count_after else 0
											if current_count < max_vols:
												execute("UPDATE tasks SET status='open' WHERE id=?", (t["id"],))
									st.success("You have withdrawn from this task.")
									st.rerun()
							else:
								st.caption("Withdrawal disabled after NGO review.")
				elif is_full:
					st.warning("This task has reached maximum volunteers.")
				else:
					with st.form(f"accept_task_{t['id']}"):
						st.markdown("**Apply for this task:**")
						st.caption("Your application will be pending until approved by the NGO.")
						
						# Automatically use task's start date and estimated hours
						availability_date = t.get('start_date') or t.get('date')
						hours_committed = t.get('hours', 2)
						
						contact_email = st.text_input("Your Email *", value=current.get('email', ''), key=f"email_{t['id']}")
						# Auto-fill phone from volunteer details
						volunteer_phone = volunteer_record.get("phone", "")
						contact_phone = st.text_input("Your Phone *", value=volunteer_phone, key=f"phone_{t['id']}")
						additional_notes = st.text_area("Why should we accept you for this task? *", key=f"notes_{t['id']}")
						
						accept_btn = st.form_submit_button("Apply for Task", use_container_width=True)
						
						if accept_btn:
							# Validate compulsory fields
							if not additional_notes or not additional_notes.strip():
								st.error("Please explain why you should be accepted for this task. This field is required.")
							elif not contact_email or not contact_email.strip():
								st.error("Email is required.")
							elif not contact_phone or not contact_phone.strip():
								st.error("Phone number is required.")
							else:
								try:
									execute(
										"""INSERT INTO volunteer_acceptances(task_id, volunteer_id, availability_date, 
										   hours_committed, contact_email, contact_phone, additional_notes, approval_status, status) 
										   VALUES(?,?,?,?,?,?,?, 'pending', 'accepted')""",
										(t["id"], current["id"], str(availability_date), 
										 int(hours_committed), contact_email, contact_phone, additional_notes)
									)
									st.success("Application submitted successfully! Waiting for NGO approval.")
									st.rerun()
								except Exception as e:
									if "UNIQUE constraint" in str(e):
										st.error("You have already applied for this task.")
									else:
										st.error(f"Failed to submit application: {e}")

with accepted_tab:
	st.subheader("My Accepted Tasks")
	accepted_tasks = fetchall(
		"""
		SELECT volunteer_acceptances.*, tasks.title as task_title, tasks.description as task_desc,
		       tasks.location as task_location, tasks.address as task_address, tasks.date as task_date, 
		       tasks.start_date, tasks.end_date, tasks.hours, tasks.category, tasks.urgency,
		       tasks.age_requirement, tasks.physical_requirements, tasks.equipment_needed, tasks.wage_rate,
		       ngos.name as ngo_name, ngos.email as ngo_email
		FROM volunteer_acceptances
		JOIN tasks ON tasks.id = volunteer_acceptances.task_id
		JOIN ngos ON ngos.id = tasks.ngo_id
		WHERE volunteer_acceptances.volunteer_id = ?
		ORDER BY volunteer_acceptances.created_at DESC
		""",
		(current["id"],),
	)
	
	if not accepted_tasks:
		st.info("You haven't accepted any tasks yet. Browse tasks to get started!")
	else:
		for acc in accepted_tasks:
			approval = (acc.get("approval_status") or "pending").title()
			status_label = (acc.get("status") or "accepted").replace("_", " ").title()
			display_status = status_label
			if approval == "Pending":
				display_status = "Pending Approval"
			elif approval == "Rejected":
				display_status = "Rejected"
			
			with st.expander(f"{acc['task_title']} · {acc['ngo_name']} · {display_status}"):
				col1, col2 = st.columns(2)
				with col1:
					st.markdown("**Task Details:**")
					st.write(acc.get('task_desc', ''))
					# Date range and duration
					start_d = acc.get('start_date') or acc.get('task_date')
					end_d = acc.get('end_date') or acc.get('task_date')
					if start_d and end_d:
						st.caption(f"Duration: {start_d} to {end_d} | Hours: {acc.get('hours', '-')}")
					else:
						st.caption(f"Date: {start_d or '-'} | Hours: {acc.get('hours', '-')}")
					
					st.caption(f"Location: {acc.get('task_location', '-')} | City: {acc.get('task_location', '-')}")
					if acc.get('task_address'):
						st.caption(f"Address: {acc.get('task_address')}")
					if acc.get('category'):
						st.caption(f"Category: {acc.get('category')} | Urgency: {acc.get('urgency', 'N/A')}")
					if acc.get('age_requirement'):
						st.caption(f"Age: {acc.get('age_requirement')} | Physical: {acc.get('physical_requirements') or 'None'}")
					if acc.get('equipment_needed'):
						st.caption(f"Supplies: {acc.get('equipment_needed')}")
						
					# AI Estimate Money
					wage_rate = acc.get('wage_rate', 0)
					hours = acc.get('hours', 0)
					if wage_rate and hours and start_d and end_d:
						from lib.monetisation_helper import calculate_duration_days
						duration = calculate_duration_days(start_d, end_d)
						est_val = wage_rate * hours * duration
						st.info(f"💰 **AI Estimated Earnings:** {format_currency(est_val)}")
				with col2:
					st.markdown("**Your Commitment:**")
					st.write(f"**Availability:** {acc.get('availability_date', 'N/A')}")
					st.write(f"**Hours Committed:** {acc.get('hours_committed', 'N/A')} hours")
					st.write(f"**Contact:** {acc.get('contact_email', 'N/A')}")
					if acc.get('contact_phone'):
						st.write(f"**Phone:** {acc.get('contact_phone', 'N/A')}")
					if acc.get('additional_notes'):
						st.write(f"**Notes:** {acc.get('additional_notes')}")
					st.caption(f"NGO Contact: {acc.get('ngo_email', 'N/A')}")
					acc_status = (acc.get("status") or "accepted").lower()
					if acc_status == "not_completed" and acc.get("completion_note"):
						st.warning(f"NGO feedback: {acc.get('completion_note')}")
					if acc_status == "completed":
						st.success(f"Great job! You generated {format_currency(acc.get('monetisation_value', 0) or 0)} worth of community value!")
					if acc_status == "accepted":
						if st.button("Withdraw from Task", key=f"withdraw_acc_{acc['id']}", type="secondary"):
							execute("DELETE FROM volunteer_acceptances WHERE id=?", (acc["id"],))
							# Check if task should be reopened
							task_info = fetchone("SELECT * FROM tasks WHERE id=?", (acc["task_id"],))
							if task_info and task_info.get('status') == 'closed':
								max_vols = task_info.get('max_volunteers', 0)
								if max_vols:
									count_after = fetchone(
										"""
										SELECT COUNT(*) as count
										FROM volunteer_acceptances
										WHERE task_id=? AND (status IS NULL OR status IN ('accepted','completed'))
										""",
										(acc["task_id"],),
									)
									current_count = count_after["count"] if count_after else 0
									if current_count < max_vols:
										execute("UPDATE tasks SET status='open' WHERE id=?", (acc["task_id"],))
							st.success("You have withdrawn from this task.")
							st.rerun()
					else:
						st.caption("Withdrawal disabled after NGO review.")

with profile_tab:
	st.subheader("My Profile & Statistics")
	
	# Profile Information
	volunteer = volunteer_record
	gender_options = ["Female", "Male", "Non-binary", "Prefer not to say", "Other"]
	current_gender = volunteer.get("gender") if volunteer.get("gender") in gender_options else "Prefer not to say"
	with st.form("volunteer_profile"):
		name = st.text_input("Full Name", value=volunteer.get("name", ""))
		email = st.text_input("Email", value=volunteer.get("email", ""), disabled=True)
		location = st.text_input("Location (City)", value=volunteer.get("location", ""))
		skills = st.text_input("Skills (comma separated)", value=volunteer.get("skills", ""))
		phone = st.text_input("Mobile Number", value=volunteer.get("phone", ""))
		gender = st.selectbox("Gender", gender_options, index=gender_options.index(current_gender))
		age_value = st.number_input("Age (years)", min_value=0, max_value=120, value=int(volunteer.get("age") or 0), step=1)
		save = st.form_submit_button("Save Profile", use_container_width=True)
		if save:
			execute(
				"UPDATE volunteers SET name=?, location=?, skills=?, phone=?, gender=?, age=? WHERE id=?",
				(name, location, skills, phone, gender, int(age_value) if age_value else None, current["id"]),
			)
			st.session_state["vol_user"]["name"] = name
			volunteer_record.update(
				{
					"name": name,
					"location": location,
					"skills": skills,
					"phone": phone,
					"gender": gender,
					"age": int(age_value) if age_value else None,
				}
			)
			st.success("Profile updated")
	
	st.markdown("---")
	st.markdown("### 📊 Volunteer Statistics")
	
	# Get statistics
	from datetime import datetime, timedelta
	import pandas as pd
	
	all_acceptances = fetchall(
		"""
		SELECT volunteer_acceptances.*, tasks.title, tasks.category, tasks.location as task_location,
		       tasks.date as task_date, ngos.name as ngo_name
		FROM volunteer_acceptances
		JOIN tasks ON tasks.id = volunteer_acceptances.task_id
		JOIN ngos ON ngos.id = tasks.ngo_id
		WHERE volunteer_acceptances.volunteer_id = ?
		ORDER BY volunteer_acceptances.created_at DESC
		""",
		(current["id"],),
	)
	
	completed_acceptances = [
		acc for acc in all_acceptances if (acc.get("status") or "accepted").lower() == "completed"
	]

	# Update pending logic to check approval_status
	pending_acceptances = [
		acc for acc in all_acceptances 
		if (acc.get("status") or "accepted").lower() == "accepted" 
		and (acc.get("approval_status") or "pending").lower() == "pending"
	]
	not_completed_acceptances = [
		acc for acc in all_acceptances if (acc.get("status") or "").lower() == "not_completed"
	]
	
	if not completed_acceptances:
		st.info("No completed volunteer work recorded yet. Completed tasks will appear here after the NGO marks them as finished.")
		if pending_acceptances or not_completed_acceptances:
			st.markdown("#### Current Engagements")
			cols = st.columns(2)
			with cols[0]:
				st.metric("Awaiting NGO Review", len(pending_acceptances))
			with cols[1]:
				st.metric("Marked Not Completed", len(not_completed_acceptances))
		if not all_acceptances:
			st.caption("Once you complete a task and the NGO approves it, your statistics will appear here.")
	else:
		# Calculate statistics
		total_tasks = len(completed_acceptances)
		total_hours = sum(acc.get('hours_committed', 0) or 0 for acc in completed_acceptances)
		
		# Monthly statistics
		monthly_data = {}
		for acc in completed_acceptances:
			try:
				date_str = acc.get('created_at') or acc.get('availability_date', '')
				if date_str:
					date_obj = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
					month_key = date_obj.strftime('%Y-%m')
					if month_key not in monthly_data:
						monthly_data[month_key] = {'tasks': 0, 'hours': 0}
					monthly_data[month_key]['tasks'] += 1
					monthly_data[month_key]['hours'] += acc.get('hours_committed', 0) or 0
			except:
				pass
		
		# Yearly statistics
		yearly_data = {}
		for acc in completed_acceptances:
			try:
				date_str = acc.get('created_at') or acc.get('availability_date', '')
				if date_str:
					date_obj = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
					year_key = date_obj.strftime('%Y')
					if year_key not in yearly_data:
						yearly_data[year_key] = {'tasks': 0, 'hours': 0}
					yearly_data[year_key]['tasks'] += 1
					yearly_data[year_key]['hours'] += acc.get('hours_committed', 0) or 0
			except:
				pass
		
		# Category breakdown
		category_data = {}
		for acc in completed_acceptances:
			cat = acc.get('category', 'Other')
			if cat not in category_data:
				category_data[cat] = {'tasks': 0, 'hours': 0, 'value': 0}
			category_data[cat]['tasks'] += 1
			category_data[cat]['hours'] += acc.get('hours_committed', 0) or 0
			category_data[cat]['value'] += acc.get('monetisation_value', 0) or 0
		
		# Calculate statistics
		total_tasks = len(completed_acceptances)
		total_hours = sum(acc.get('hours_committed', 0) or 0 for acc in completed_acceptances)
		total_value = sum(acc.get('monetisation_value', 0) or 0 for acc in completed_acceptances)
		
		# Display summary cards
		col1, col2, col3, col4, col5 = st.columns(5)
		with col1:
			st.metric("Total Tasks", total_tasks)
		with col2:
			st.metric("Total Hours", total_hours)
		with col3:
			st.metric("💰 Total Value", format_currency(total_value))
		with col4:
			st.metric("NGOs", len(set(acc.get('ngo_name', '') for acc in completed_acceptances)))
		with col5:
			st.metric("Categories", len(category_data))
		
		if pending_acceptances or not_completed_acceptances:
			st.markdown("#### Additional Status Overview")
			colp, coln = st.columns(2)
			with colp:
				st.metric("Awaiting NGO Review", len(pending_acceptances))
			with coln:
				st.metric("Marked Not Completed", len(not_completed_acceptances))
		
		st.markdown("---")
		
		# Charts
		if monthly_data:
			st.markdown("#### 📅 Monthly Activity")
			months = sorted(monthly_data.keys())
			monthly_df = pd.DataFrame({
				'Month': [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in months],
				'Tasks': [monthly_data[m]['tasks'] for m in months],
				'Hours': [monthly_data[m]['hours'] for m in months]
			})
			col1, col2 = st.columns(2)
			with col1:
				st.bar_chart(monthly_df.set_index('Month')['Tasks'], use_container_width=True)
			with col2:
				st.bar_chart(monthly_df.set_index('Month')['Hours'], use_container_width=True)
		
		if yearly_data:
			st.markdown("#### 📆 Yearly Activity")
			years = sorted(yearly_data.keys())
			yearly_df = pd.DataFrame({
				'Year': years,
				'Tasks': [yearly_data[y]['tasks'] for y in years],
				'Hours': [yearly_data[y]['hours'] for y in years]
			})
			col1, col2 = st.columns(2)
			with col1:
				st.bar_chart(yearly_df.set_index('Year')['Tasks'], use_container_width=True)
			with col2:
				st.bar_chart(yearly_df.set_index('Year')['Hours'], use_container_width=True)
		
		if category_data:
			st.markdown("#### 🏷️ Work by Category")
			category_df = pd.DataFrame({
				'Category': list(category_data.keys()),
				'Tasks': [category_data[c]['tasks'] for c in category_data.keys()],
				'Hours': [category_data[c]['hours'] for c in category_data.keys()],
				'Value (₹)': [category_data[c]['value'] for c in category_data.keys()]
			})
			col1, col2, col3 = st.columns(3)
			with col1:
				st.bar_chart(category_df.set_index('Category')['Tasks'], use_container_width=True)
			with col2:
				st.bar_chart(category_df.set_index('Category')['Hours'], use_container_width=True)
			with col3:
				st.markdown("**💰 Value Generated**")
				st.bar_chart(category_df.set_index('Category')['Value (₹)'], use_container_width=True)
		
		# Recent activity table
		st.markdown("#### 📋 Recent Activity")
		recent_df = pd.DataFrame([{
			'Task': acc.get('title', 'N/A'),
			'NGO': acc.get('ngo_name', 'N/A'),
			'Category': acc.get('category', 'N/A'),
			'Value Generated': format_currency(acc.get('monetisation_value', 0) or 0),
			'Hours': acc.get('hours_committed', 0) or 0,
			'Date': acc.get('availability_date', 'N/A')
		} for acc in completed_acceptances[:10]])
		st.dataframe(recent_df, use_container_width=True, hide_index=True)

st.markdown("<div class='spacer-24'></div>", unsafe_allow_html=True)
if st.button("Logout", type="secondary"):
	st.session_state["vol_user"] = None
	st.rerun()
