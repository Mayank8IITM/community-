"""
Rate limiting to prevent abuse and protect the application from spam/crashes.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional


def check_rate_limit(
	user_id: int,
	action: str,
	max_requests: int = 10,
	window_minutes: int = 1,
	show_error: bool = True
) -> bool:
	"""
	Check if user has exceeded rate limit for a specific action.
	
	Args:
		user_id: ID of the user (NGO or volunteer)
		action: Action being performed (e.g., 'create_task', 'apply_task')
		max_requests: Maximum number of requests allowed in the time window
		window_minutes: Time window in minutes
		show_error: Whether to show error message to user
	
	Returns:
		True if request is allowed, False if rate limit exceeded
	
	Example:
		if check_rate_limit(ngo_id, 'create_task', max_requests=5, window_minutes=1):
			# Create task...
		else:
			# Rate limit exceeded, error already shown
	"""
	key = f"rate_limit_{user_id}_{action}"
	
	# Initialize rate limit tracking for this user/action
	if key not in st.session_state:
		st.session_state[key] = []
	
	# Remove old requests outside the time window
	cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
	st.session_state[key] = [
		timestamp for timestamp in st.session_state[key]
		if timestamp > cutoff_time
	]
	
	# Check if limit exceeded
	if len(st.session_state[key]) >= max_requests:
		if show_error:
			st.error(
				f"⚠️ Too many requests. Please wait {window_minutes} minute(s) before trying again. "
				f"({len(st.session_state[key])}/{max_requests} requests used)"
			)
		return False
	
	# Add current request timestamp
	st.session_state[key].append(datetime.now())
	return True


def get_rate_limit_status(user_id: int, action: str, window_minutes: int = 1) -> dict:
	"""
	Get current rate limit status for a user/action.
	
	Returns:
		dict with 'count', 'window_minutes', and 'reset_time'
	"""
	key = f"rate_limit_{user_id}_{action}"
	
	if key not in st.session_state:
		return {
			'count': 0,
			'window_minutes': window_minutes,
			'reset_time': None
		}
	
	cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
	recent_requests = [
		timestamp for timestamp in st.session_state[key]
		if timestamp > cutoff_time
	]
	
	reset_time = None
	if recent_requests:
		oldest_request = min(recent_requests)
		reset_time = oldest_request + timedelta(minutes=window_minutes)
	
	return {
		'count': len(recent_requests),
		'window_minutes': window_minutes,
		'reset_time': reset_time
	}


def reset_rate_limit(user_id: int, action: Optional[str] = None):
	"""
	Reset rate limit for a user. If action is None, resets all actions.
	Use with caution - mainly for testing or admin purposes.
	"""
	if action:
		key = f"rate_limit_{user_id}_{action}"
		if key in st.session_state:
			del st.session_state[key]
	else:
		# Reset all rate limits for this user
		keys_to_delete = [
			key for key in st.session_state.keys()
			if key.startswith(f"rate_limit_{user_id}_")
		]
		for key in keys_to_delete:
			del st.session_state[key]


# Predefined rate limits for common actions
RATE_LIMITS = {
	'create_task': {'max_requests': 10, 'window_minutes': 5},  # 10 tasks per 5 minutes
	'edit_task': {'max_requests': 20, 'window_minutes': 5},    # 20 edits per 5 minutes
	'delete_task': {'max_requests': 10, 'window_minutes': 5},  # 10 deletions per 5 minutes
	'apply_task': {'max_requests': 20, 'window_minutes': 5},   # 20 applications per 5 minutes
	'update_profile': {'max_requests': 5, 'window_minutes': 10}, # 5 profile updates per 10 minutes
	'send_notification': {'max_requests': 50, 'window_minutes': 5}, # 50 notifications per 5 minutes
	'approve_volunteer': {'max_requests': 100, 'window_minutes': 5}, # 100 approvals per 5 minutes
}


def check_action_rate_limit(user_id: int, action: str, show_error: bool = True) -> bool:
	"""
	Convenience function using predefined rate limits.
	
	Args:
		user_id: ID of the user
		action: Action name from RATE_LIMITS dict
		show_error: Whether to show error message
	
	Returns:
		True if allowed, False if rate limited
	"""
	if action not in RATE_LIMITS:
		# No rate limit defined for this action, allow it
		return True
	
	limits = RATE_LIMITS[action]
	return check_rate_limit(
		user_id=user_id,
		action=action,
		max_requests=limits['max_requests'],
		window_minutes=limits['window_minutes'],
		show_error=show_error
	)
