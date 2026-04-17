from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import json

import models
import schemas
from database import engine, get_db, Base
from redis_client import redis_client

app = FastAPI()


# Create DB tables on startup
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "Task Manager API is running"}


# Create Task
@app.post("/tasks", response_model=schemas.TaskResponse)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # clear cache
    redis_client.delete("tasks")

    return db_task


# Get All Tasks (with Redis cache)
@app.get("/tasks", response_model=list[schemas.TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    try:
        cached_tasks = redis_client.get("tasks")
    except:
        cached_tasks = None

    if cached_tasks:
        return [schemas.TaskResponse(**task) for task in json.loads(cached_tasks)]

    tasks = db.query(models.Task).all()

    result = [schemas.TaskResponse.model_validate(task).model_dump() for task in tasks]

    redis_client.setex("tasks", 60, json.dumps(result))  # cache for 60 sec

    return result


# Get Single Task
@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


# Update Task
@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(task_id: int, updated_task: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in updated_task.model_dump().items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)

    # clear cache
    redis_client.delete("tasks")

    return task


# Delete Task
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    # clear cache
    redis_client.delete("tasks")

    return {"message": "Task deleted"}