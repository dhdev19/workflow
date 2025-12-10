# Digital Homeez Workflow Management System

A Flask-based workflow assignment tool for managing tasks, departments, and team members.

## Features

- **Role-based Access Control**: Admin, Department Head, and Team Member roles
- **Department Management**: Create and manage departments
- **User Management**: Add/remove users with different roles
- **Task Management**: Create, assign, and track tasks with priorities and statuses
- **Subtask Support**: Add subtasks to main tasks
- **Task Assignment**: Assign tasks to individuals, departments, or multiple users
- **Task Filtering**: Filter tasks by name, status, department, and client
- **Analytics Dashboard**: View task statistics and department performance

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory:
```
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///workflow.db
```

4. Run the application:
```bash
python app.py
```

5. Access the application at `http://localhost:5000`

## Default Credentials

- **Email**: admin@digitalhomeez.com
- **Password**: admin123

## User Roles

### Admin
- Full system access
- Manage departments, users, and tasks
- View all tasks across all departments
- Assign tasks to any user or department
- Delete tasks and users
- View analytics

### Department Head
- Manage team members in their department
- Create and assign tasks
- Forward tasks to team members
- Reassign tasks to other department heads
- View all tasks in their department
- Cannot delete tasks

### Team Member
- View only tasks assigned to them
- Create tasks and subtasks
- Update task status
- Add subtasks to tasks
- Cannot delete tasks

## Task Priorities

- **URGENT**: High priority tasks requiring immediate attention
- **IMPORTANT**: Important tasks with priority handling
- **DAILY TASK**: Regular daily tasks

## Task Statuses

- **ASSIGNED**: Task has been assigned
- **PENDING**: Task is pending
- **COMPLETED**: Task is completed
- **Review with ADMIN**: Task requires admin review
- **Waiting for approval from Client**: Task is waiting for client approval

## Project Structure

```
workflow/
├── app.py                 # Main application file
├── config.py             # Configuration settings
├── models.py             # Database models
├── utils.py              # Utility functions and decorators
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── routes/               # Route blueprints
│   ├── auth.py          # Authentication routes
│   ├── admin.py         # Admin routes
│   ├── department_head.py  # Department head routes
│   ├── team_member.py   # Team member routes
│   └── tasks.py         # Task-related routes
└── templates/           # Jinja2 templates
    ├── base.html        # Base template
    ├── auth/            # Authentication templates
    ├── admin/           # Admin templates
    ├── dept_head/       # Department head templates
    ├── team_member/     # Team member templates
    └── shared/          # Shared templates
```

## License

This project is proprietary software for Digital Homeez.

