# Testing Guide

This document describes how to run tests for the Digital Homeez Workflow Management System.

## Installation

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

## Running Tests

Run all tests:
```bash
pytest
```

Run with coverage report:
```bash
pytest --cov=. --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_auth.py
```

Run specific test:
```bash
pytest tests/test_auth.py::TestAuthentication::test_login_success
```

Run with verbose output:
```bash
pytest -v
```

## Test Structure

- `tests/conftest.py` - Shared fixtures and configuration
- `tests/test_auth.py` - Authentication tests
- `tests/test_admin.py` - Admin functionality tests
- `tests/test_department_head.py` - Department head functionality tests
- `tests/test_team_member.py` - Team member functionality tests
- `tests/test_tasks.py` - Task management tests
- `tests/test_permissions.py` - Role-based permission tests
- `tests/test_models.py` - Database model tests

## Test Coverage

The test suite covers:

1. **Authentication**
   - Login/logout functionality
   - Redirect after login
   - Invalid credentials handling

2. **Admin Features**
   - Department management
   - User management
   - Task creation, editing, deletion
   - Analytics access

3. **Department Head Features**
   - Team member management
   - Task creation
   - Task forwarding
   - Dashboard access

4. **Team Member Features**
   - Task viewing (only assigned)
   - Task creation
   - Status updates
   - Subtask management

5. **Permissions**
   - Role-based access control
   - Task visibility restrictions
   - Action restrictions

6. **Models**
   - Database model creation
   - Relationships
   - Data integrity

## Test Configuration

Tests use an in-memory SQLite database (`sqlite:///:memory:`) for fast execution and isolation. Each test runs in a clean database state.

## Writing New Tests

When adding new features, add corresponding tests:

1. Add test fixtures in `conftest.py` if needed
2. Create test file or add to existing test file
3. Follow naming convention: `test_*.py` files with `Test*` classes
4. Use descriptive test names: `test_<feature>_<scenario>`

Example:
```python
def test_create_task_with_all_fields(client, admin_user, department):
    """Test creating task with all fields populated."""
    # Test implementation
```

