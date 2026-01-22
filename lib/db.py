from __future__ import annotations
import os
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
import psycopg2
import psycopg2.pool
import psycopg2.extras
from dotenv import load_dotenv
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
	raise ValueError(
		"DATABASE_URL environment variable is not set. "
		"Please add it to your .env file. "
		"Get the connection string from Supabase: Project Settings -> Database -> Connection string -> URI"
	)


@st.cache_resource
def get_connection_pool():
	"""Create a connection pool for reusing database connections."""
	try:
		return psycopg2.pool.SimpleConnectionPool(
			minconn=1,
			maxconn=10,  # Max 10 concurrent connections
			dsn=DATABASE_URL
		)
	except Exception as e:
		logger.error(f"Failed to create connection pool: {e}")
		raise


@contextmanager
def get_conn():
	"""
	Context manager for database connections.
	Automatically commits on success and rolls back on error.
	"""
	pool = get_connection_pool()
	conn = None
	try:
		conn = pool.getconn()
		yield conn
		conn.commit()
	except psycopg2.OperationalError as e:
		logger.error(f"Database connection error: {e}")
		if conn:
			conn.rollback()
		raise
	except Exception as e:
		logger.error(f"Database error: {e}")
		if conn:
			conn.rollback()
		raise
	finally:
		if conn:
			pool.putconn(conn)


@st.cache_resource
def init_db() -> None:
	"""Initialize database tables with PostgreSQL-compatible schema."""
	with get_conn() as conn:
		cur = conn.cursor()
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS ngos (
				id SERIAL PRIMARY KEY,
				name TEXT NOT NULL,
				email TEXT UNIQUE NOT NULL,
				password_hash TEXT NOT NULL,
				location TEXT,
				description TEXT,
				registration_number TEXT,
				certificate_path TEXT,
				certificate_filename TEXT,
				certificate_content_type TEXT,
				logo_path TEXT,
				phone TEXT
			);

			CREATE TABLE IF NOT EXISTS volunteers (
				id SERIAL PRIMARY KEY,
				name TEXT NOT NULL,
				email TEXT UNIQUE NOT NULL,
				password_hash TEXT NOT NULL,
				location TEXT,
				skills TEXT,
				phone TEXT,
				gender TEXT,
				age INTEGER,
				total_value_generated REAL DEFAULT 0
			);

			CREATE TABLE IF NOT EXISTS tasks (
				id SERIAL PRIMARY KEY,
				ngo_id INTEGER NOT NULL,
				title TEXT NOT NULL,
				description TEXT,
				location TEXT,
				date TEXT,
				start_date TEXT,
				end_date TEXT,
				hours INTEGER,
				status TEXT DEFAULT 'open',
				category TEXT,
				required_skills TEXT,
				max_volunteers INTEGER,
				contact_email TEXT,
				contact_phone TEXT,
				deadline TEXT,
				urgency TEXT,
				age_requirement TEXT,
				physical_requirements TEXT,
				equipment_needed TEXT,
				is_deleted INTEGER DEFAULT 0,
				wage_rate REAL DEFAULT 0,
				address TEXT,
				FOREIGN KEY (ngo_id) REFERENCES ngos(id)
			);

			CREATE TABLE IF NOT EXISTS applications (
				id SERIAL PRIMARY KEY,
				task_id INTEGER NOT NULL,
				volunteer_id INTEGER NOT NULL,
				status TEXT DEFAULT 'pending',
				message TEXT,
				FOREIGN KEY (task_id) REFERENCES tasks(id),
				FOREIGN KEY (volunteer_id) REFERENCES volunteers(id)
			);

			CREATE TABLE IF NOT EXISTS hours_logs (
				id SERIAL PRIMARY KEY,
				application_id INTEGER NOT NULL,
				hours INTEGER NOT NULL,
				note TEXT,
				FOREIGN KEY (application_id) REFERENCES applications(id)
			);

			CREATE TABLE IF NOT EXISTS volunteer_acceptances (
				id SERIAL PRIMARY KEY,
				task_id INTEGER NOT NULL,
				volunteer_id INTEGER NOT NULL,
				availability_date TEXT,
				availability_time TEXT,
				hours_committed INTEGER,
				contact_email TEXT,
				contact_phone TEXT,
				additional_notes TEXT,
				approval_status TEXT DEFAULT 'pending',
				status TEXT DEFAULT 'accepted',
				completion_note TEXT,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				certificate_pushed INTEGER DEFAULT 0,
				monetisation_value REAL DEFAULT 0,
				FOREIGN KEY (task_id) REFERENCES tasks(id),
				FOREIGN KEY (volunteer_id) REFERENCES volunteers(id),
				UNIQUE(task_id, volunteer_id)
			);

			CREATE TABLE IF NOT EXISTS notifications (
				id SERIAL PRIMARY KEY,
				user_type TEXT NOT NULL,
				user_id INTEGER NOT NULL,
				message TEXT NOT NULL,
				notification_type TEXT,
				related_id INTEGER,
				is_read INTEGER DEFAULT 0,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			);
			"""
			)
		
		# Add work time columns to tasks table if they don't exist
		cur.execute("""
			DO $$ 
			BEGIN
				IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
							   WHERE table_name='tasks' AND column_name='work_start_time') THEN
					ALTER TABLE tasks ADD COLUMN work_start_time TEXT;
				END IF;
				IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
							   WHERE table_name='tasks' AND column_name='work_end_time') THEN
					ALTER TABLE tasks ADD COLUMN work_end_time TEXT;
				END IF;
			END $$;
		""")\n	\n	# Create indexes for performance (10-100x faster queries)\n	cur.execute("""
		CREATE INDEX IF NOT EXISTS idx_tasks_ngo_id ON tasks(ngo_id);
		CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
		CREATE INDEX IF NOT EXISTS idx_tasks_deleted ON tasks(is_deleted);
		CREATE INDEX IF NOT EXISTS idx_tasks_ngo_deleted ON tasks(ngo_id, is_deleted);
		CREATE INDEX IF NOT EXISTS idx_acceptances_task ON volunteer_acceptances(task_id);
		CREATE INDEX IF NOT EXISTS idx_acceptances_volunteer ON volunteer_acceptances(volunteer_id);
		CREATE INDEX IF NOT EXISTS idx_acceptances_status ON volunteer_acceptances(approval_status);
		CREATE INDEX IF NOT EXISTS idx_acceptances_task_status ON volunteer_acceptances(task_id, approval_status);
		CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_type, user_id, is_read);
		CREATE INDEX IF NOT EXISTS idx_ngos_email ON ngos(email);
		CREATE INDEX IF NOT EXISTS idx_volunteers_email ON volunteers(email);
	""")




def execute(query: str, params: Tuple[Any, ...] = ()) -> int:
	"""
	Execute a query and return the last inserted row ID.
	
	Args:
		query: SQL query with %s placeholders (PostgreSQL style)
		params: Tuple of parameters to bind to the query
	
	Returns:
		Last inserted row ID (for INSERT queries) or 0
	"""
	# Convert SQLite-style ? placeholders to PostgreSQL-style %s
	query = query.replace("?", "%s")
	
	with get_conn() as conn:
		cur = conn.cursor()
		cur.execute(query, params)
		
		# Try to get the last inserted ID for INSERT queries
		if query.strip().upper().startswith("INSERT"):
			try:
				# PostgreSQL uses RETURNING id or lastval()
				cur.execute("SELECT lastval()")
				result = cur.fetchone()
				return result[0] if result else 0
			except Exception:
				return 0
		return 0


def fetchall(query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
	"""
	Execute a query and return all results as a list of dictionaries.
	
	Args:
		query: SQL query with %s placeholders (PostgreSQL style)
		params: Tuple of parameters to bind to the query
	
	Returns:
		List of dictionaries representing rows
	"""
	# Convert SQLite-style ? placeholders to PostgreSQL-style %s
	query = query.replace("?", "%s")
	
	with get_conn() as conn:
		cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
		cur.execute(query, params)
		rows = [dict(row) for row in cur.fetchall()]
		return rows


def fetchone(query: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
	"""
	Execute a query and return the first result as a dictionary.
	
	Args:
		query: SQL query with %s placeholders (PostgreSQL style)
		params: Tuple of parameters to bind to the query
	
	Returns:
		Dictionary representing the row, or None if no results
	"""
	# Convert SQLite-style ? placeholders to PostgreSQL-style %s
	query = query.replace("?", "%s")
	
	with get_conn() as conn:
		cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
		cur.execute(query, params)
		row = cur.fetchone()
		return dict(row) if row else None
