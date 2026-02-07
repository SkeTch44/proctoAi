from locust import HttpUser, task, between
import random
import uuid

class StudentUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Login and get token on start"""
        self.username = f"student_{uuid.uuid4().hex[:8]}"
        self.password = "password123"
        
        # 1. Register
        self.client.post("/api/register", json={
            "username": self.username,
            "password": self.password,
            "role": "student"
        })
        
        # 2. Login
        response = self.client.post("/api/login", json={
            "username": self.username,
            "password": self.password
        })
        
        if response.status_code == 200:
            self.token = response.json().get('token')
            self.headers = {'Authorization': f'Bearer {self.token}'}
        else:
            self.token = None
            self.headers = {}

    @task(1)
    def view_exams(self):
        """View available exams"""
        if self.token:
            self.client.get("/api/exams", headers=self.headers)

    @task(3)
    def submit_random_answer(self):
        """Simulate submitting an answer (if in a session) - Mocked for API load"""
        # In a real test, we'd need to start a session first. 
        # For pure API stress, we can hit the endpoint to check overhead even if it returns 404/400.
        if self.token:
            self.client.post("/api/submit_answer", json={
                "session_id": "fake_session",
                "question_id": "q_1",
                "answer": "A"
            }, headers=self.headers)

    # Note: SocketIO testing requires a specific Locust client or plugin. 
    # This file tests the HTTP API throughput which is crucial for the login/dashboard bottlenecks.
