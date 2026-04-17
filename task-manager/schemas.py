from pydantic import BaseModel

class TaskBase(BaseModel):
    title: str
    description: str
    status: str = "pending"

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int

    class Config:
        from_attributes = True