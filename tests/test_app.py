"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test"""
    from src.app import activities
    
    # Store original state
    original = {k: {"participants": v["participants"].copy()} for k, v in activities.items()}
    
    yield
    
    # Restore original state
    for k, v in activities.items():
        v["participants"] = original[k]["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_dict(self, client, reset_activities):
        """Test that /activities returns a dictionary of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
    
    def test_get_activities_contains_expected_activities(self, client, reset_activities):
        """Test that /activities returns all expected activities"""
        response = client.get("/activities")
        activities = response.json()
        
        expected_activities = [
            "Basketball", "Tennis Club", "Debate Team", "Robotics Club",
            "Art Studio", "Music Ensemble", "Chess Club", "Programming Class", "Gym Class"
        ]
        
        for activity in expected_activities:
            assert activity in activities
    
    def test_get_activities_activity_structure(self, client, reset_activities):
        """Test that each activity has the required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_details in activities.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert "newstudent@mergington.edu" in response.json()["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Basketball/signup?email={email}")
        
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Basketball"]["participants"]
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup returns 404 for non-existent activity"""
        response = client.post(
            "/activities/NonExistent/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Test signup returns 400 when student is already signed up"""
        response = client.post(
            "/activities/Basketball/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_multiple_students(self, client, reset_activities):
        """Test multiple students can sign up for the same activity"""
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        
        response1 = client.post(f"/activities/Basketball/signup?email={email1}")
        response2 = client.post(f"/activities/Basketball/signup?email={email2}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        response = client.get("/activities")
        activities = response.json()
        assert email1 in activities["Basketball"]["participants"]
        assert email2 in activities["Basketball"]["participants"]


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        response = client.post(
            "/activities/Basketball/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "alex@mergington.edu"
        client.post(f"/activities/Basketball/unregister?email={email}")
        
        response = client.get("/activities")
        activities = response.json()
        assert email not in activities["Basketball"]["participants"]
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregister returns 404 for non-existent activity"""
        response = client.post(
            "/activities/NonExistent/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_student_not_signed_up(self, client, reset_activities):
        """Test unregister returns 400 when student is not signed up"""
        response = client.post(
            "/activities/Basketball/unregister?email=notstudent@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_then_signup_again(self, client, reset_activities):
        """Test that a student can sign up again after unregistering"""
        email = "student@mergington.edu"
        
        # First signup
        response1 = client.post(f"/activities/Tennis Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.post(f"/activities/Tennis Club/unregister?email={email}")
        assert response2.status_code == 200
        
        # Sign up again
        response3 = client.post(f"/activities/Tennis Club/signup?email={email}")
        assert response3.status_code == 200
        
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Tennis Club"]["participants"]


class TestRootEndpoint:
    """Tests for GET / endpoint"""
    
    def test_root_redirects(self, client):
        """Test that root endpoint redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"


class TestIntegration:
    """Integration tests for multiple operations"""
    
    def test_signup_unregister_flow(self, client, reset_activities):
        """Test complete flow of signup and unregister"""
        email = "integration@mergington.edu"
        activity = "Robotics Club"
        
        # Check initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # Unregister
        unregister_response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregister
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count
    
    def test_multiple_activities_operations(self, client, reset_activities):
        """Test operations across multiple activities"""
        email = "multiactivity@mergington.edu"
        
        activities_list = ["Basketball", "Chess Club", "Art Studio"]
        
        # Sign up for multiple activities
        for activity in activities_list:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all signups
        response = client.get("/activities")
        activities_data = response.json()
        for activity in activities_list:
            assert email in activities_data[activity]["participants"]
        
        # Unregister from one activity
        response = client.post(f"/activities/Chess Club/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify partial unregister
        response = client.get("/activities")
        activities_data = response.json()
        assert email not in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Basketball"]["participants"]
        assert email in activities_data["Art Studio"]["participants"]
