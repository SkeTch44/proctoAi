
import unittest
import json
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from backend.app import app, db_manager
from backend.config import TestingConfig

class TestAdminApproval(unittest.TestCase):
    def setUp(self):
        app.config.from_object(TestingConfig)
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db_manager.init_database()
        
        # Create a "Super Admin" manually (Approved)
        self.super_id = db_manager.create_user('super', 'hash', role='admin')
        db_manager.approve_user(self.super_id)
        
        # Login Super Admin
        with patch('backend.db.database.check_password_hash', return_value=True):
             # We assume authentication succeeds for mocked hash
             # But authenticate_user checks real hash. 
             # Let's create user with real hash for test simplicity
             pass

    def test_approval_flow(self):
        from werkzeug.security import generate_password_hash
        import uuid
        
        print("\nTesting Admin Approval Flow...")
        
        # Use unique name to avoid collisions
        unique_suffix = uuid.uuid4().hex[:4]
        super_name = f'super_{unique_suffix}'
        junior_name = f'junior_{unique_suffix}'
        
        # 0. Setup Real Super Admin
        super_hash = generate_password_hash('superpass')
        super_id = db_manager.create_user(super_name, super_hash, role='admin')
        self.assertIsNotNone(super_id, "Failed to create super admin")
        
        approved = db_manager.approve_user(super_id)
        self.assertTrue(approved, "Failed to approve super admin")
        
        # Super Login
        resp_super = self.client.post('/api/login', json={'username': super_name, 'password': 'superpass'})
        self.assertEqual(resp_super.status_code, 200, f"Super admin login failed: {resp_super.json}")
        super_token = resp_super.json['token']
        super_headers = {'Authorization': f'Bearer {super_token}'}
        
        # 1. Register New Admin (Should be pending)
        print("Registering new admin...")
        resp_reg = self.client.post('/api/register', json={
            'username': junior_name,
            'password': 'password123',
            'role': 'admin'
        })
        self.assertEqual(resp_reg.status_code, 200)
        self.assertIn('pending Admin approval', resp_reg.json['message'])
        jr_id = resp_reg.json['user']['id']
        
        # 2. Junior Login (Should Fail)
        print("Attempting login as unapproved admin...")
        resp_login_fail = self.client.post('/api/login', json={
            'username': junior_name,
            'password': 'password123'
        })
        self.assertEqual(resp_login_fail.status_code, 403)
        self.assertIn('pending', resp_login_fail.json['message'])
        
        # 3. Approve Junior (By Super)
        print("Approving admin...")
        resp_approve = self.client.post('/api/admin/approve_user', 
                                      headers=super_headers,
                                      json={'user_id': jr_id})
        self.assertEqual(resp_approve.status_code, 200)
        
        # 4. Junior Login (Should Succeed)
        print("Attempting login as approved admin...")
        resp_login_success = self.client.post('/api/login', json={
            'username': junior_name,
            'password': 'password123'
        })
        self.assertEqual(resp_login_success.status_code, 200)
        print("✅ SUCCESS: Junior admin logged in after approval.")

if __name__ == '__main__':
    unittest.main()
