from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from ..database import get_db
from ..models.project import Project
from ..schemas import ProjectCreate, ProjectResponse

router = APIRouter()

@router.post("/projects/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    # Verify if the path is a valid directory
    target_path = Path(project.path)
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")
    
    # Check if a git repo exists (optional, but good for maestro)
    if not (target_path / ".git").exists():
        raise HTTPException(status_code=400, detail="Path is not a valid Git repository")

    db_project = db.query(Project).filter(Project.path == project.path).first()
    if db_project:
        raise HTTPException(status_code=400, detail="Project already registered")
        
    new_project = Project(name=project.name, path=project.path)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@router.get("/projects/", response_model=list[ProjectResponse])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    projects = db.query(Project).offset(skip).limit(limit).all()
    return projects
