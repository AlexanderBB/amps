# Flask MVP Web Application

This is a simple, intuitive MVP web application built with Flask, SQLAlchemy, and Bootstrap 5.

## Tech Stack
- **Backend:** Flask
- **Templating:** Jinja2
- **UI Framework:** Bootstrap 5
- **Icons:** Bootstrap Icons
- **Auth:** Flask-Login
- **Database:** PostgreSQL (SQLAlchemy ORM)
- **Migrations:** Flask-Migrate (Alembic)

## Features
- Authentication (Login/Logout)
- User Roles (Admin, User)
- Record CRUD (Create, Read, Update, Delete)
- Ownership Enforcement (Users see only their own records; Admins see everything)
- Admin Dashboard for User Management (Edit, Deactivate, Reset Password)
- Responsive Sidebar Layout

## Project Structure
```text
flask_mvp/
├── app/
│   ├── __init__.py      # App factory and models
│   ├── routes.py        # Blueprints and route handlers
│   ├── utils.py         # Auth decorators and helpers
│   ├── static/          # Static assets
│   └── templates/       # Jinja2 templates
├── migrations/          # Alembic migrations
├── requirements.txt     # Python dependencies
├── seed.py             # Database seeder
└── wsgi.py             # Application entry point
```

## Setup Instructions

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables:**
   Set the following environment variables:
   - `DATABASE_URL`: PostgreSQL connection string.
   - `SECRET_KEY`: Flask secret key.

3. **Database Initialization:**
   ```bash
   python seed.py
   ```

4. **Run Application:**
   ```bash
   export FLASK_APP=wsgi.py
   flask run
   ```

## Default Credentials (from seed.py)
- **Admin:** `admin@example.com` / `admin123`
- **User:** `user@example.com` / `user123`
