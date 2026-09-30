import json
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from src import app as activities_app


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.original_participants = activities_app.activities["Chess Club"]["participants"][:]
        password_hash = activities_app.hash_password("correct horse", "test-salt")
        users = [
            {"email": "student@mergington.edu", "role": "student", "password_hash": password_hash},
            {"email": "teacher@mergington.edu", "role": "admin", "password_hash": password_hash},
        ]
        self.environment = patch.dict(os.environ, {"MERGINGTON_USERS": json.dumps(users)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.restore_participants)

    def restore_participants(self):
        activities_app.activities["Chess Club"]["participants"] = self.original_participants

    def test_password_hash_is_verified(self):
        password_hash = activities_app.hash_password("correct horse", "test-salt")
        self.assertTrue(activities_app.verify_password("correct horse", password_hash))
        self.assertFalse(activities_app.verify_password("wrong password", password_hash))

    def test_authentication_rejects_missing_and_invalid_credentials(self):
        with self.assertRaises(HTTPException) as missing:
            activities_app.get_current_user(None)
        self.assertEqual(missing.exception.status_code, 401)

        with self.assertRaises(HTTPException) as invalid:
            activities_app.get_current_user(
                HTTPBasicCredentials(username="student@mergington.edu", password="wrong")
            )
        self.assertEqual(invalid.exception.status_code, 401)

    def test_mutation_routes_require_authentication(self):
        protected_paths = {
            "/activities/{activity_name}/signup",
            "/activities/{activity_name}/unregister",
        }
        routes = {
            route.path: route
            for route in activities_app.app.routes
            if getattr(route, "path", None) in protected_paths
        }
        self.assertEqual(set(routes), protected_paths)
        for route in routes.values():
            dependencies = [dependency.call for dependency in route.dependant.dependencies]
            self.assertIn(activities_app.get_current_user, dependencies)

    def test_student_can_only_sign_up_as_the_authenticated_account(self):
        student = activities_app.AuthenticatedUser("student@mergington.edu", "student")
        result = activities_app.signup_for_activity("Chess Club", None, student)
        self.assertIn("student@mergington.edu", activities_app.activities["Chess Club"]["participants"])
        self.assertIn("student@mergington.edu", result["message"])

        with self.assertRaises(HTTPException) as forbidden:
            activities_app.signup_for_activity("Chess Club", "other@mergington.edu", student)
        self.assertEqual(forbidden.exception.status_code, 403)

    def test_student_cannot_unregister_another_account(self):
        student = activities_app.AuthenticatedUser("student@mergington.edu", "student")
        with self.assertRaises(HTTPException) as forbidden:
            activities_app.unregister_from_activity(
                "Chess Club", "michael@mergington.edu", student
            )
        self.assertEqual(forbidden.exception.status_code, 403)
        self.assertIn("michael@mergington.edu", activities_app.activities["Chess Club"]["participants"])

    def test_admin_can_manage_a_student_registration(self):
        admin = activities_app.AuthenticatedUser("teacher@mergington.edu", "admin")
        activities_app.signup_for_activity("Chess Club", "student@mergington.edu", admin)
        activities_app.unregister_from_activity("Chess Club", "student@mergington.edu", admin)
        self.assertNotIn("student@mergington.edu", activities_app.activities["Chess Club"]["participants"])

        with self.assertRaises(HTTPException) as unknown_student:
            activities_app.signup_for_activity("Chess Club", "unknown@mergington.edu", admin)
        self.assertEqual(unknown_student.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()