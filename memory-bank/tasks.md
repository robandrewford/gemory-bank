# Project Tasks: [Your Project Name]

## Current Sprint Tasks (Sprint 1: User Authentication)

### Task 1: Implement User Registration Endpoint
- **Description:** Create a Flask API endpoint for new user registration.
- **Acceptance Criteria:**
    - Endpoint: `POST /api/v1/register`
    - Accepts: `username`, `email`, `password`
    - Validates: Unique username/email, strong password.
    - Stores: Hashed password in database.
    - Returns: User ID and success message on success.
- **Status:** In Progress (GitHub Issue #123)

### Task 2: Implement User Login Endpoint
- **Description:** Create a Flask API endpoint for user login and session creation.
- **Acceptance Criteria:**
    - Endpoint: `POST /api/v1/login`
    - Accepts: `username` or `email`, `password`
    - Validates: Credentials, creates session.
    - Returns: Session token/cookie and basic user info.
- **Status:** Todo (GitHub Issue #124)

### Task 3: Database Schema for Users
- **Description:** Define the SQLAlchemy model and initial migration for the `users` table.
- **Acceptance Criteria:**
    - `User` model with `id`, `username`, `email`, `password_hash`, `created_at`.
    - Initial migration script.
- **Status:** Done (GitHub Issue #125)

## Backlog Tasks:

### Task 4: Task Model Definition
- **Description:** Define SQLAlchemy model for tasks (title, description, due_date, status, assignee).
- **Status:** Todo

### Task 5: Basic Task CRUD Endpoints
- **Description:** Implement API endpoints for creating, reading, updating, and deleting tasks.
- **Status:** Todo
