# Digital Homeez Workflow Management System - Working Documentation

## Table of Contents
1. [Application Structure](#application-structure)
2. [Database Models & Relationships](#database-models--relationships)
3. [User Roles & Permissions](#user-roles--permissions)
4. [Core Workflows](#core-workflows)
5. [Multi-Department Collaboration](#multi-department-collaboration)
6. [Task Lifecycle](#task-lifecycle)
7. [API Routes & Endpoints](#api-routes--endpoints)
8. [Data Flow Diagrams](#data-flow-diagrams)

---

## Application Structure

### Directory Structure
```
workflow/
├── app.py                      # Main Flask application factory
├── config.py                   # Configuration (DB, secrets)
├── models.py                   # SQLAlchemy database models
├── extensions.py               # Flask extensions (db, bcrypt, login_manager)
├── utils.py                    # Utility functions & decorators
├── requirements.txt            # Python dependencies
├── routes/                     # Route blueprints
│   ├── __init__.py
│   ├── auth.py                 # Authentication (login/logout)
│   ├── admin.py                # Admin routes
│   ├── department_head.py      # Department head routes
│   ├── team_member.py          # Team member routes
│   └── tasks.py                # Shared task routes (subtasks, view)
└── templates/                  # Jinja2 HTML templates
    ├── base.html               # Base template
    ├── auth/                   # Login templates
    ├── admin/                  # Admin dashboard & management
    ├── dept_head/              # Department head dashboard & actions
    ├── team_member/            # Team member dashboard
    └── shared/                  # Shared templates (task_detail, task_table)
```

### Application Initialization Flow
```
1. app.py::create_app()
   ├── Initialize Flask app
   ├── Load configuration from Config class
   ├── Initialize extensions (db, bcrypt, login_manager)
   ├── Register blueprints (auth, admin, dept_head, team_member, tasks)
   ├── Create database tables (db.create_all())
   └── Create default admin user if not exists
```

---

## Database Models & Relationships

### Entity Relationship Diagram
```
User (1) ────< (N) Department
  │
  ├───< (N) TaskAssignment ────> (1) Task
  │
  ├───< (N) Task (created_by)
  │
  └───< (N) Subtask (created_by)

Task (1) ────< (N) TaskAssignment ────> (1) User
  │
  ├───< (N) Subtask
  │
  ├───< (N) TaskDepartmentAssignment ────> (1) Department
  │
  └───< (N) DepartmentTaskCompletion ────> (1) Department

Department (1) ────< (N) User
  │
  └───< (N) Task (primary department)
```

### Model Details

#### 1. User
- **Fields**: id, email, username, password_hash, full_name, role, department_id, is_active, created_at
- **Relationships**:
  - `department`: Many-to-One with Department
  - `assigned_tasks`: Many-to-Many with Task (via TaskAssignment)
  - `created_tasks`: One-to-Many with Task

#### 2. Department
- **Fields**: id, name, description, created_at
- **Relationships**:
  - `members`: One-to-Many with User
  - `tasks`: One-to-Many with Task (primary department)
  - `head`: One-to-One with User (department_head role)

#### 3. Task
- **Fields**: id, task_name, description, priority, status, department_id, created_by_id, client_name, deadline, remark, created_at, updated_at
- **Relationships**:
  - `department`: Many-to-One with Department (primary department)
  - `creator`: Many-to-One with User
  - `assignments`: One-to-Many with TaskAssignment
  - `subtasks`: One-to-Many with Subtask
  - `department_assignments`: One-to-Many with TaskDepartmentAssignment
  - `department_completions`: One-to-Many with DepartmentTaskCompletion

#### 4. TaskAssignment
- **Purpose**: Links individual users to tasks
- **Fields**: id, task_id, user_id, assigned_at, assigned_by_id
- **Unique Constraint**: None (users can be assigned multiple times)

#### 5. TaskDepartmentAssignment
- **Purpose**: Links departments to tasks (multi-department support)
- **Fields**: id, task_id, department_id, assigned_at, assigned_by_id
- **Unique Constraint**: (task_id, department_id) - prevents duplicate assignments

#### 6. DepartmentTaskCompletion
- **Purpose**: Tracks completion status per department
- **Fields**: id, task_id, department_id, is_completed, completed_at, completed_by_id
- **Unique Constraint**: (task_id, department_id) - one completion record per department per task

#### 7. Subtask
- **Fields**: id, task_id, subtask_name, description, status, created_by_id, created_at, updated_at
- **Relationships**: Many-to-One with Task

---

## User Roles & Permissions

### Role Hierarchy
```
Admin (Full Access)
  │
  ├── Department Head (Department Management)
  │     │
  │     └── Team Member (Task Execution)
```

### Permission Matrix

| Action | Admin | Department Head | Team Member |
|--------|-------|----------------|-------------|
| Create Departments | ✅ | ❌ | ❌ |
| Edit Departments | ✅ | ❌ | ❌ |
| Delete Departments | ✅ | ❌ | ❌ |
| Add Users | ✅ | ✅ (Team Members only) | ❌ |
| Delete Users | ✅ | ✅ (Team Members only) | ❌ |
| Create Tasks | ✅ | ✅ | ✅ |
| Edit Tasks | ✅ | ❌ | ❌ |
| Delete Tasks | ✅ | ❌ | ❌ |
| Assign Tasks | ✅ | ✅ | ❌ |
| Forward Tasks | ❌ | ✅ | ❌ |
| Reassign Tasks | ✅ | ✅ (to other dept heads) | ❌ |
| Update Task Status | ✅ | ✅ | ✅ |
| Mark Department Complete | ❌ | ✅ (own department) | ❌ |
| View All Tasks | ✅ | ✅ (own + assigned depts) | ❌ (assigned only) |
| View Analytics | ✅ | ❌ | ❌ |

### Access Control Functions

#### `can_access_task(user, task)`
- **Admin**: Always returns True
- **Department Head**: 
  - Returns True if `task.department_id == user.department_id` OR
  - Returns True if task is assigned to user's department via `TaskDepartmentAssignment`
- **Team Member**: Returns True only if user has a `TaskAssignment` record for the task

---

## Core Workflows

### 1. User Authentication Flow
```
User visits / → Redirected to /auth/login
  ↓
User enters credentials
  ↓
auth.py::login() validates credentials
  ↓
If valid: login_user() → Redirect based on role
  ├── Admin → /admin/dashboard
  ├── Department Head → /dept-head/dashboard
  └── Team Member → /team-member/dashboard
```

### 2. Task Creation Flow

#### Admin Creates Task
```
/admin/tasks/create (GET) → Show form
  ↓
User fills form (name, priority, department, assignments)
  ↓
POST /admin/tasks/create
  ├── Create Task record
  ├── Create TaskAssignment records (if users selected)
  ├── Create TaskDepartmentAssignment records (if departments selected)
  └── Create DepartmentTaskCompletion records (initialize as incomplete)
  ↓
Redirect to /admin/dashboard
```

#### Department Head Creates Task
```
/dept-head/tasks/create (GET) → Show form
  ↓
User fills form
  ├── Assign to team members (checkboxes)
  └── Assign to departments (checkboxes) - OPTIONAL
  ↓
POST /dept-head/tasks/create
  ├── Create Task (department_id = current_user.department_id)
  ├── Create TaskAssignment records for selected team members
  ├── Create TaskDepartmentAssignment records for selected departments
  └── Create DepartmentTaskCompletion records
  ↓
Redirect to /dept-head/dashboard
```

#### Team Member Creates Task
```
/team-member/tasks/create (GET) → Show form
  ↓
POST /team-member/tasks/create
  ├── Create Task (department_id = current_user.department_id)
  └── No automatic assignments
  ↓
Redirect to /team-member/dashboard
```

### 3. Task Assignment Flow

#### Admin Assigns Task
```
/admin/tasks/<id>/assign (GET) → Show assignment form
  ↓
User selects users/departments
  ↓
POST /admin/tasks/<id>/assign
  ├── Delete all existing TaskAssignment records
  ├── Create new TaskAssignment records
  └── Create TaskDepartmentAssignment if departments selected
  ↓
Redirect to /admin/dashboard
```

#### Department Head Forwards Task
```
/dept-head/tasks/<id>/forward (GET) → Show team member checkboxes
  ↓
User checks/unchecks team members
  ↓
POST /dept-head/tasks/<id>/forward
  ├── Get current assignments
  ├── Remove assignments for unchecked users
  └── Add assignments for checked users (if not already assigned)
  ↓
Redirect to /dept-head/dashboard
```

#### Department Head Assigns Departments
```
/dept-head/tasks/<id>/assign-departments (GET) → Show department checkboxes
  ↓
User checks/unchecks departments
  ↓
POST /dept-head/tasks/<id>/assign-departments
  ├── Remove TaskDepartmentAssignment for unchecked departments
  ├── Remove DepartmentTaskCompletion for unchecked departments
  ├── Add TaskDepartmentAssignment for checked departments
  ├── Add DepartmentTaskCompletion (initialize as incomplete)
  └── Call _update_task_completion_status()
  ↓
Redirect to /dept-head/dashboard
```

### 4. Task Completion Flow

#### Single Department Task
```
User updates status to COMPLETED
  ↓
Task.status = 'COMPLETED'
  ↓
No department completion logic (no TaskDepartmentAssignment)
  ↓
Task marked as complete
```

#### Multi-Department Task

**Option A: Department Head Marks Department Complete**
```
Department Head clicks "Mark Department as Complete"
  ↓
POST /dept-head/tasks/<id>/mark-department-complete
  ├── Get/Create DepartmentTaskCompletion record
  ├── Toggle is_completed flag
  ├── Set completed_at and completed_by_id
  └── Call _update_task_completion_status()
      ├── Check all departments have is_completed = True
      ├── If yes: task.status = 'COMPLETED'
      └── If no: task.status = 'ASSIGNED' (if was COMPLETED)
  ↓
Redirect to task detail page
```

**Option B: Direct Status Update**
```
User (Team Member or Department Head) sets status to COMPLETED
  ↓
If TaskDepartmentAssignment exists:
  ├── Mark all assigned departments as complete
  ├── Set DepartmentTaskCompletion.is_completed = True for all
  └── Set completed_at and completed_by_id
  ↓
Task.status = 'COMPLETED'
```

---

## Multi-Department Collaboration

### Concept
Tasks can be assigned to multiple departments simultaneously. Each department works independently and marks their completion separately. The overall task is only marked as COMPLETED when ALL assigned departments have completed.

### Data Flow

#### Assignment Phase
```
Task Created
  ↓
Admin/Dept Head selects multiple departments
  ↓
For each selected department:
  ├── Create TaskDepartmentAssignment
  └── Create DepartmentTaskCompletion (is_completed = False)
```

#### Visibility Phase
```
Department Head Dashboard Query:
  ├── Get tasks where department_id = current_user.department_id (primary)
  └── Get tasks where TaskDepartmentAssignment.department_id = current_user.department_id (assigned)
  ↓
Union both queries → Show all relevant tasks
```

#### Completion Phase
```
Department A Head marks complete
  ├── DepartmentTaskCompletion (dept A) → is_completed = True
  └── _update_task_completion_status()
      ├── Check all departments
      ├── Dept A: ✅, Dept B: ❌
      └── Task status remains ASSIGNED

Department B Head marks complete
  ├── DepartmentTaskCompletion (dept B) → is_completed = True
  └── _update_task_completion_status()
      ├── Check all departments
      ├── Dept A: ✅, Dept B: ✅
      └── Task status → COMPLETED
```

### Helper Function: `_update_task_completion_status(task)`
```python
1. Get all TaskDepartmentAssignment for task
2. If no assignments → return (no department logic)
3. For each department:
   - Get DepartmentTaskCompletion record
   - Check if is_completed = True
4. If all completed:
   - task.status = 'COMPLETED'
5. Else if task.status == 'COMPLETED':
   - task.status = 'ASSIGNED' (revert)
```

---

## Task Lifecycle

### State Transitions

```
CREATED (Task created)
  ↓
ASSIGNED (Default status)
  ↓
  ├──→ PENDING (User updates)
  ├──→ Review with ADMIN
  ├──→ Waiting for approval from Client
  └──→ COMPLETED
       ├── Single dept: Direct completion
       └── Multi-dept: All departments must complete
```

### Status Update Rules

1. **Team Members**:
   - Can update status of assigned tasks
   - If task has department assignments and status = COMPLETED:
     - All departments automatically marked as complete
   - Can mark as COMPLETED regardless of department completion

2. **Department Heads**:
   - Can update status of tasks from their department or assigned to their department
   - Can mark department as complete independently
   - Can directly mark task as COMPLETED (overrides department logic)

3. **Admin**:
   - Can update any task status
   - Can reassign tasks to multiple departments

---

## API Routes & Endpoints

### Authentication Routes (`/auth`)
- `GET/POST /auth/login` - User login
- `GET /auth/logout` - User logout

### Admin Routes (`/admin`)
- `GET /admin/dashboard` - Admin dashboard with task filters
- `GET /admin/departments` - List all departments
- `GET/POST /admin/departments/add` - Add new department
- `GET/POST /admin/departments/<id>/edit` - Edit department (update members)
- `POST /admin/departments/<id>/delete` - Delete department
- `GET /admin/users` - List all users
- `GET/POST /admin/users/add` - Add new user
- `POST /admin/users/<id>/delete` - Delete user
- `GET/POST /admin/tasks/create` - Create task
- `GET/POST /admin/tasks/<id>/edit` - Edit task
- `POST /admin/tasks/<id>/delete` - Delete task
- `GET/POST /admin/tasks/<id>/assign` - Assign task to users/departments
- `GET/POST /admin/tasks/<id>/reassign` - Reassign task to multiple departments
- `GET /admin/analytics` - View analytics

### Department Head Routes (`/dept-head`)
- `GET /dept-head/dashboard` - Department head dashboard
- `GET /dept-head/team-members` - List team members
- `GET/POST /dept-head/team-members/add` - Add team member
- `POST /dept-head/team-members/<id>/delete` - Remove team member
- `GET/POST /dept-head/tasks/create` - Create task
- `GET/POST /dept-head/tasks/<id>/forward` - Forward task to team members
- `GET/POST /dept-head/tasks/<id>/reassign` - Reassign to another dept head
- `GET/POST /dept-head/tasks/<id>/assign-departments` - Assign to multiple departments
- `GET/POST /dept-head/tasks/<id>/update-status` - Update task status
- `POST /dept-head/tasks/<id>/mark-department-complete` - Mark department as complete

### Team Member Routes (`/team-member`)
- `GET /team-member/dashboard` - Team member dashboard
- `GET/POST /team-member/tasks/create` - Create task
- `POST /team-member/tasks/<id>/update-status` - Update task status

### Shared Task Routes (`/tasks`)
- `GET /tasks/<id>` - View task details
- `POST /tasks/<id>/subtasks/add` - Add subtask
- `POST /tasks/subtasks/<id>/update-status` - Update subtask status

---

## Data Flow Diagrams

### Task Creation with Multi-Department Assignment
```
User Input
  ├── Task Details (name, priority, description, etc.)
  ├── Primary Department (required)
  └── Department Assignments (optional checkboxes)
      ↓
Backend Processing
  ├── Create Task record
  │   └── department_id = selected primary department
  ├── For each selected department:
  │   ├── Create TaskDepartmentAssignment
  │   └── Create DepartmentTaskCompletion (is_completed=False)
  └── For selected team members:
      └── Create TaskAssignment
      ↓
Database State
  ├── Task (1 record)
  ├── TaskDepartmentAssignment (N records for N departments)
  ├── DepartmentTaskCompletion (N records, all incomplete)
  └── TaskAssignment (M records for M users)
```

### Department Completion Workflow
```
Initial State
  Task: status = ASSIGNED
  Dept A: is_completed = False
  Dept B: is_completed = False
      ↓
Dept A Head marks complete
  ├── DepartmentTaskCompletion (Dept A): is_completed = True
  └── _update_task_completion_status()
      ├── Check Dept A: ✅
      ├── Check Dept B: ❌
      └── Task status: ASSIGNED (unchanged)
      ↓
Dept B Head marks complete
  ├── DepartmentTaskCompletion (Dept B): is_completed = True
  └── _update_task_completion_status()
      ├── Check Dept A: ✅
      ├── Check Dept B: ✅
      └── Task status: COMPLETED ✅
```

### Dashboard Query Flow (Department Head)
```
User: Department Head of Dept X
      ↓
Query 1: Primary Department Tasks
  SELECT * FROM task WHERE department_id = X
      ↓
Query 2: Assigned Department Tasks
  SELECT task_id FROM task_department_assignment WHERE department_id = X
  SELECT * FROM task WHERE id IN (task_ids)
      ↓
Union Results
  ├── Tasks where Dept X is primary
  └── Tasks assigned to Dept X
      ↓
Display in Dashboard
```

---

## Key Features Implementation

### 1. Multi-Department Task Assignment
- **Models**: `TaskDepartmentAssignment`, `DepartmentTaskCompletion`
- **Logic**: Each department tracks completion independently
- **UI**: Checkboxes in create/edit task forms
- **Completion**: Task becomes COMPLETED only when all departments complete

### 2. Department Completion Tracking
- **Model**: `DepartmentTaskCompletion`
- **Fields**: `is_completed`, `completed_at`, `completed_by_id`
- **Update**: Triggered by department head button or direct status update
- **Auto-completion**: `_update_task_completion_status()` checks all departments

### 3. Task Visibility Rules
- **Admin**: Sees all tasks
- **Department Head**: 
  - Primary department tasks (task.department_id = user.department_id)
  - Assigned department tasks (TaskDepartmentAssignment exists)
- **Team Member**: Only tasks with TaskAssignment record

### 4. Status Update Logic
- **Without Department Assignments**: Direct status update
- **With Department Assignments**:
  - Direct COMPLETED → Auto-mark all departments as complete
  - Department completion → Check all, then update overall status

### 5. Department Member Management
- **Admin**: Can edit department and update member list
- **Department Head**: Can add/remove team members from their department
- **Update Logic**: 
  - Unchecked members → department_id set to NULL
  - Checked members → department_id set to department

---

## Error Handling

### Database Connection Issues
- MySQL "server has gone away" errors handled with connection pool settings
- Automatic reconnection via `pool_pre_ping=True`
- Connection recycling every hour

### Permission Errors
- `can_access_task()` checks user permissions before task access
- Role-based decorators (`@admin_required`, `@dept_head_required`)
- Flash messages for unauthorized access attempts

### Validation
- Unique constraints on email, username, department name
- Foreign key constraints ensure data integrity
- Form validation for required fields

---

## Security Features

1. **Password Hashing**: bcrypt with salt
2. **Session Management**: Flask-Login handles user sessions
3. **CSRF Protection**: Flask-WTF (if configured)
4. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
5. **Access Control**: Role-based decorators and permission checks

---

## Future Enhancements (Potential)

1. Email notifications for task assignments
2. Task comments/notes system
3. File attachments for tasks
4. Task templates
5. Recurring tasks
6. Task dependencies
7. Time tracking
8. Advanced reporting and exports

---

## Notes

- Database tables are auto-created on app startup via `db.create_all()`
- Default admin user created if not exists: `admin@digitalhomeez.com` / `admin123`
- MySQL connection pooling configured for production stability
- All timestamps use UTC for consistency

