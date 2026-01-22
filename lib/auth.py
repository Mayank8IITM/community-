from __future__ import annotations
import os
import hashlib
import hmac
from typing import Optional, Literal, Dict, Any
from .db import execute, fetchone

Role = Literal["ngo", "volunteer"]


def _pbkdf2_hash(password: str, salt: bytes | None = None, iterations: int = 200_000) -> str:
	if salt is None:
		salt = os.urandom(16)
	dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
	return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def hash_password(password: str) -> str:
	return _pbkdf2_hash(password)


def verify_password(password: str, stored: str) -> bool:
	try:
		algo, iter_str, salt_hex, hash_hex = stored.split("$")
		iterations = int(iter_str)
		salt = bytes.fromhex(salt_hex)
		dk_check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
		return hmac.compare_digest(dk_check.hex(), hash_hex)
	except Exception:
		return False


def register_user(role: Role, name: str, email: str, password: str, **extra) -> Optional[int]:
	password_hash = hash_password(password)
	if role == "ngo":
		return execute(
			"""INSERT INTO ngos(
				name,
				email,
				password_hash,
				location,
				description,
				registration_number,
				certificate_path,
				certificate_filename,
				certificate_content_type,
				logo_path,
				phone
			) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
			(
				name,
				email.lower().strip(),
				password_hash,
				extra.get("location", ""),
				extra.get("description", ""),
				extra.get("registration_number", ""),
				extra.get("certificate_path"),
				extra.get("certificate_filename"),
				extra.get("certificate_content_type"),
				extra.get("logo_path"),
				extra.get("phone", ""),
			),
		)
	else:
		return execute(
			"""INSERT INTO volunteers(
				name,
				email,
				password_hash,
				location,
				skills,
				phone,
				gender,
				age
			) VALUES(?,?,?,?,?,?,?,?)""",
			(
				name,
				email.lower().strip(),
				password_hash,
				extra.get("location", ""),
				extra.get("skills", ""),
				extra.get("phone", ""),
				extra.get("gender", ""),
				extra.get("age"),
			),
		)


def login_user(role: Role, email: str, password: str) -> Optional[Dict[str, Any]]:
	table = "ngos" if role == "ngo" else "volunteers"
	user = fetchone(f"SELECT * FROM {table} WHERE email=?", (email.lower().strip(),))
	if user and verify_password(password, user["password_hash"]):
		return {"id": user["id"], "name": user["name"], "email": user["email"], "role": role}
	return None
