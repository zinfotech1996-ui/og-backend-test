from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
import uuid
import os
from dotenv import load_dotenv

from database import get_db, init_db
from models import User, Project, Task, TimeEntry, UserRole, EntryType
from auth import verify_password, get_password_hash, create_access_token, decode_access_token

load_dotenv()

app = FastAPI(title="Omni Gratum Time Tracking API")

# CORS configuration
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "active"

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: datetime

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: str
    status: Optional[str] = "active"

class TaskResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    project_id: str
    status: str
    created_at: datetime

class TimeEntryCreate(BaseModel):
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None

class TimeEntryResponse(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str]
    task_id: Optional[str]
    start_time: datetime
    end_time: datetime
    duration: int
    entry_type: str
    notes: Optional[str]

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Optional[str] = "employee"

# Auth dependency
def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Initialize database and create demo users
@app.on_event("startup")
async def startup_event():
    init_db()
    db = next(get_db())
    
    # Create demo admin user
    admin_exists = db.query(User).filter(User.email == "admin@omnigratum.com").first()
    if not admin_exists:
        admin_user = User(
            id=str(uuid.uuid4()),
            email="admin@omnigratum.com",
            password=get_password_hash("admin123"),
            name="Admin User",
            role=UserRole.admin
        )
        db.add(admin_user)
    
    # Create demo employee user
    employee_exists = db.query(User).filter(User.email == "employee@omnigratum.com").first()
    if not employee_exists:
        employee_user = User(
            id=str(uuid.uuid4()),
            email="employee@omnigratum.com",
            password=get_password_hash("employee123"),
            name="Employee User",
            role=UserRole.employee
        )
        db.add(employee_user)
    
    db.commit()
    db.close()
    print("✅ Database initialized and demo users created!")
    print("   Admin: admin@omnigratum.com / admin123")
    print("   Employee: employee@omnigratum.com / employee123")

# Health check
@app.get("/")
def read_root():
    return {"message": "Omni Gratum Time Tracking API", "status": "running"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

# Authentication endpoints
@app.post("/api/auth/login", response_model=LoginResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    
    return LoginResponse(
        token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value
        )
    )

@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value
    )

# Projects endpoints
@app.get("/api/projects", response_model=List[ProjectResponse])
def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).all()
    return projects

@app.post("/api/projects", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    new_project = Project(
        id=str(uuid.uuid4()),
        name=project.name,
        description=project.description,
        status=project.status,
        created_by=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, project: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_project.name = project.name
    db_project.description = project.description
    db_project.status = project.status
    
    db.commit()
    db.refresh(db_project)
    return db_project

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted successfully"}

# Tasks endpoints
@app.get("/api/tasks", response_model=List[TaskResponse])
def get_tasks(project_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    tasks = query.all()
    return tasks

@app.post("/api/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    new_task = Task(
        id=str(uuid.uuid4()),
        name=task.name,
        description=task.description,
        project_id=task.project_id,
        status=task.status
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db_task.name = task.name
    db_task.description = task.description
    db_task.project_id = task.project_id
    db_task.status = task.status
    
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}

# Time entries endpoints
@app.get("/api/time-entries", response_model=List[TimeEntryResponse])
def get_time_entries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TimeEntry)
    
    # Non-admin users can only see their own entries
    if current_user.role != UserRole.admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        query = query.filter(TimeEntry.start_time >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00')) + timedelta(days=1)
        query = query.filter(TimeEntry.start_time < end_dt)
    
    entries = query.order_by(TimeEntry.start_time.desc()).all()
    return entries

@app.post("/api/time-entries/manual", response_model=TimeEntryResponse)
def create_manual_time_entry(entry: TimeEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Calculate duration in seconds
    duration = int((entry.end_time - entry.start_time).total_seconds())
    
    if duration <= 0:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    new_entry = TimeEntry(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        project_id=entry.project_id,
        task_id=entry.task_id,
        start_time=entry.start_time,
        end_time=entry.end_time,
        duration=duration,
        entry_type=EntryType.manual,
        notes=entry.notes,
        date=entry.start_time.date()
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

@app.put("/api/time-entries/{entry_id}", response_model=TimeEntryResponse)
def update_time_entry(entry_id: str, entry: TimeEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    # Check permissions
    if db_entry.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this entry")
    
    # Calculate duration
    duration = int((entry.end_time - entry.start_time).total_seconds())
    if duration <= 0:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    db_entry.project_id = entry.project_id
    db_entry.task_id = entry.task_id
    db_entry.start_time = entry.start_time
    db_entry.end_time = entry.end_time
    db_entry.duration = duration
    db_entry.notes = entry.notes
    db_entry.date = entry.start_time.date()
    
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.delete("/api/time-entries/{entry_id}")
def delete_time_entry(entry_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    # Check permissions
    if db_entry.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this entry")
    
    db.delete(db_entry)
    db.commit()
    return {"message": "Time entry deleted successfully"}

# Users endpoints (Admin only)
@app.get("/api/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    users = db.query(User).all()
    return users

@app.post("/api/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        id=str(uuid.uuid4()),
        email=user.email,
        password=get_password_hash(user.password),
        name=user.name,
        role=UserRole(user.role)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Timesheets endpoint
@app.get("/api/timesheets")
def get_timesheets(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TimeEntry)
    
    # Non-admin users can only see their own timesheets
    if current_user.role != UserRole.admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    elif user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        query = query.filter(TimeEntry.start_time >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00')) + timedelta(days=1)
        query = query.filter(TimeEntry.start_time < end_dt)
    
    entries = query.order_by(TimeEntry.start_time).all()
    
    # Group by date
    timesheets = {}
    for entry in entries:
        date_key = entry.start_time.date().isoformat()
        if date_key not in timesheets:
            timesheets[date_key] = {
                "date": date_key,
                "total_duration": 0,
                "entries": []
            }
        
        timesheets[date_key]["total_duration"] += entry.duration
        timesheets[date_key]["entries"].append({
            "id": entry.id,
            "project_id": entry.project_id,
            "task_id": entry.task_id,
            "start_time": entry.start_time.isoformat(),
            "end_time": entry.end_time.isoformat(),
            "duration": entry.duration,
            "notes": entry.notes
        })
    
    return list(timesheets.values())

# Reports endpoint
@app.get("/api/reports")
def get_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TimeEntry)
    
    # Non-admin users can only see their own reports
    if current_user.role != UserRole.admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        query = query.filter(TimeEntry.start_time >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00')) + timedelta(days=1)
        query = query.filter(TimeEntry.start_time < end_dt)
    
    entries = query.all()
    
    total_duration = sum(entry.duration for entry in entries)
    total_entries = len(entries)
    
    # Group by project
    projects_data = {}
    for entry in entries:
        if entry.project_id:
            if entry.project_id not in projects_data:
                project = db.query(Project).filter(Project.id == entry.project_id).first()
                projects_data[entry.project_id] = {
                    "project_id": entry.project_id,
                    "project_name": project.name if project else "Unknown",
                    "duration": 0,
                    "entries_count": 0
                }
            projects_data[entry.project_id]["duration"] += entry.duration
            projects_data[entry.project_id]["entries_count"] += 1
    
    return {
        "total_duration": total_duration,
        "total_entries": total_entries,
        "projects": list(projects_data.values())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
