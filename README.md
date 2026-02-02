# Omni Gratum Time Tracking System - Backend API

FastAPI backend with MySQL database for the Omni Gratum Time Tracking System.

## 🚀 Features

- **Authentication**: JWT-based authentication
- **User Management**: Admin and Employee roles
- **Projects & Tasks**: Manage projects and associated tasks
- **Time Tracking**: Manual and timer-based time entries
- **Reports**: Generate time tracking reports
- **Timesheets**: View and manage timesheets

## 📋 Prerequisites

- Python 3.11+
- MySQL Database (Hostinger or any MySQL server)
- pip (Python package manager)

## 🔧 Installation

1. **Install Dependencies**:
```bash
cd /app/backend
pip install -r requirements.txt
```

2. **Configure Environment Variables**:
Create/edit `.env` file:
```env
# MySQL Database Configuration
DB_USER=your_db_user
DB_PASS=your_db_password
DB_DATABASE=your_db_name
DB_SERVER=your_db_server

# JWT Secret Key
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS Settings (add your Netlify URL)
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.netlify.app
```

3. **Run the Server**:
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

## 👤 Demo Users

Two demo users are automatically created:

**Admin User:**
- Email: `admin@omnigratum.com`
- Password: `admin123`

**Employee User:**
- Email: `employee@omnigratum.com`
- Password: `employee123`

## 📚 API Endpoints

### Authentication
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create project (Admin only)
- `PUT /api/projects/{id}` - Update project (Admin only)
- `DELETE /api/projects/{id}` - Delete project (Admin only)

### Tasks
- `GET /api/tasks?project_id={id}` - List tasks
- `POST /api/tasks` - Create task (Admin only)
- `PUT /api/tasks/{id}` - Update task (Admin only)
- `DELETE /api/tasks/{id}` - Delete task (Admin only)

### Time Entries
- `GET /api/time-entries?start_date={date}&end_date={date}` - List time entries
- `POST /api/time-entries/manual` - Create manual time entry
- `PUT /api/time-entries/{id}` - Update time entry
- `DELETE /api/time-entries/{id}` - Delete time entry

### Users (Admin only)
- `GET /api/users` - List all users
- `POST /api/users` - Create new user

### Reports & Timesheets
- `GET /api/timesheets` - Get timesheets
- `GET /api/reports` - Get reports

## 🔐 Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## 🌐 CORS Configuration

Update `ALLOWED_ORIGINS` in `.env` to include your frontend URLs:
```env
ALLOWED_ORIGINS=http://localhost:3000,https://your-netlify-app.netlify.app
```

## 🗄️ Database Schema

### Users Table
- id (UUID)
- email (unique)
- password (hashed)
- name
- role (admin/employee)
- status
- created_at

### Projects Table
- id (UUID)
- name
- description
- status
- created_by
- created_at

### Tasks Table
- id (UUID)
- name
- description
- project_id (FK)
- status
- created_at

### Time Entries Table
- id (UUID)
- user_id (FK)
- project_id (FK)
- task_id (FK)
- start_time
- end_time
- duration (seconds)
- entry_type (timer/manual)
- notes
- date
- created_at

## 🚢 Deployment

### Deploy to Production

1. Update `.env` with production values
2. Set a strong `JWT_SECRET_KEY`
3. Add production frontend URL to `ALLOWED_ORIGINS`
4. Use a production-grade WSGI server (already using uvicorn)

### Running with Supervisor

The backend is configured to run with supervisor:
```bash
sudo supervisorctl restart backend
sudo supervisorctl status backend
```

## 📝 License

MIT License

## 🤝 Support

For issues and questions, please contact the development team.
