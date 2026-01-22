"""
File validation utilities for the Community Connect application.
"""
from typing import Optional

# Maximum file size in bytes (10KB = 10,240 bytes)
MAX_FILE_SIZE_BYTES = 10 * 1024


def validate_file_size(uploaded_file, max_size_bytes: int = MAX_FILE_SIZE_BYTES) -> tuple[bool, Optional[str]]:
	"""
	Validate that an uploaded file does not exceed the maximum size.
	
	Args:
		uploaded_file: Streamlit UploadedFile object
		max_size_bytes: Maximum allowed file size in bytes (default: 10KB)
	
	Returns:
		Tuple of (is_valid, error_message)
		- is_valid: True if file size is acceptable, False otherwise
		- error_message: None if valid, error string if invalid
	"""
	if uploaded_file is None:
		return True, None
	
	file_size = uploaded_file.size
	
	if file_size > max_size_bytes:
		max_size_kb = max_size_bytes / 1024
		actual_size_kb = file_size / 1024
		error_msg = f"File size ({actual_size_kb:.1f}KB) exceeds maximum allowed size ({max_size_kb:.1f}KB). Please upload a smaller file."
		return False, error_msg
	
	return True, None


def format_file_size(size_bytes: int) -> str:
	"""
	Format file size in human-readable format.
	
	Args:
		size_bytes: File size in bytes
	
	Returns:
		Formatted string (e.g., "5.2KB", "1.3MB")
	"""
	if size_bytes < 1024:
		return f"{size_bytes}B"
	elif size_bytes < 1024 * 1024:
		return f"{size_bytes / 1024:.1f}KB"
	else:
		return f"{size_bytes / (1024 * 1024):.1f}MB"
