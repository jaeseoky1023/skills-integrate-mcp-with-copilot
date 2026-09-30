# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create password hashes for each account without entering passwords into shell history:

   ```
   cd src
   python -c 'from getpass import getpass; from app import hash_password; print(hash_password(getpass("Password: ")))'
   ```

3. Configure accounts on the server. `password_hash` is the value printed above:

   ```
   export MERGINGTON_USERS='[{"email":"teacher@mergington.edu","role":"admin","password_hash":"<generated-hash>"},{"email":"student@mergington.edu","role":"student","password_hash":"<generated-hash>"}]'
   uvicorn app:app --reload
   ```

   Keep this configuration out of source control. HTTP Basic credentials are held in browser memory only; use HTTPS outside local development.

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/me`                                                        | Get the authenticated account and role                              |
| POST   | `/activities/{activity_name}/signup`                              | Sign up as the authenticated student; admins may provide a student email |
| DELETE | `/activities/{activity_name}/unregister`                          | Cancel your own signup; admins may provide a student email          |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
