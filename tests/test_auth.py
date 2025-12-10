import pytest
from models import User

class TestAuthentication:
    """Test authentication functionality."""
    
    def test_login_page_loads(self, client):
        """Test login page is accessible."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Login' in response.data
    
    def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/auth/login', data={
            'email': 'wrong@test.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
    
    def test_logout(self, client, admin_user):
        """Test logout functionality."""
        # Login first
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        # Logout
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'logged out' in response.data.lower()
    
    def test_redirect_after_login(self, client, admin_user):
        """Test redirect after successful login."""
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=False)
        # Should redirect to admin dashboard
        assert response.status_code in [302, 200]

