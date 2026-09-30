"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

security = HTTPBasic(auto_error=False)
PASSWORD_HASH_ITERATIONS = 600_000


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str
    role: str


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$")
        iterations = int(iterations)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
    except (AttributeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()
    return hmac.compare_digest(actual_digest, expected_digest)


def load_users() -> dict:
    configured_users = os.environ.get("MERGINGTON_USERS", "[]")
    try:
        records = json.loads(configured_users)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=503, detail="Authentication is misconfigured") from error

    if not isinstance(records, list):
        raise HTTPException(status_code=503, detail="Authentication is misconfigured")

    users = {}
    for record in records:
        if not isinstance(record, dict):
            raise HTTPException(status_code=503, detail="Authentication is misconfigured")
        email = record.get("email")
        role = record.get("role")
        password_hash = record.get("password_hash")
        if (not isinstance(email, str) or not email.strip() or "@" not in email
            or not isinstance(role, str) or role not in {"student", "admin"}
                or not isinstance(password_hash, str) or "$" not in password_hash
                or email.strip().lower() in users):
            raise HTTPException(status_code=503, detail="Authentication is misconfigured")
        users[email.strip().lower()] = {"role": role, "password_hash": password_hash}
    return users


def get_current_user(
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
) -> AuthenticatedUser:
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Basic"},
    )
    if credentials is None:
        raise unauthorized

    email = credentials.username.strip().lower()
    account = load_users().get(email)
    if account is None or not verify_password(credentials.password, account["password_hash"]):
        raise unauthorized
    return AuthenticatedUser(email=email, role=account["role"])


def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/me")
def get_authenticated_user(user: AuthenticatedUser = Depends(get_current_user)):
    return {"email": user.email, "role": user.role}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: Optional[str] = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    if user.role == "student":
        if email is not None and email.strip().lower() != user.email:
            raise HTTPException(status_code=403, detail="Students can only sign themselves up")
        participant_email = user.email
    else:
        if not email:
            raise HTTPException(status_code=422, detail="Admin must provide a student email")
        target = load_users().get(email.strip().lower())
        if target is None or target["role"] != "student":
            raise HTTPException(status_code=404, detail="Student account not found")
        participant_email = email.strip().lower()

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if participant_email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(participant_email)
    return {"message": f"Signed up {participant_email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: Optional[str] = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    if user.role == "student":
        if email is not None and email.strip().lower() != user.email:
            raise HTTPException(status_code=403, detail="Students can only unregister themselves")
        participant_email = user.email
    else:
        if not email:
            raise HTTPException(status_code=422, detail="Admin must provide a student email")
        participant_email = email.strip().lower()

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if participant_email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(participant_email)
    return {"message": f"Unregistered {participant_email} from {activity_name}"}
