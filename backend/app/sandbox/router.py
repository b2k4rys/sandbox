from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.sandbox.schemas import CeleryTaskResponse, TaskEnqueueResponse
from app.sandbox.worker import celery
from app.sandbox.service import execute_code
from app.auth.service import get_current_user
from app.auth.models import User
from typing import Annotated
from app.sandbox.models import Job, CeleryStatuses
import uuid
from database import get_db
sandbox_router = APIRouter(prefix='/sandbox')

@sandbox_router.post('/execute', response_model=TaskEnqueueResponse)
async def execute_docker(current_user: Annotated[User, Depends(get_current_user)],file: UploadFile = File(), db: AsyncSession = Depends(get_db)):
    random_id = uuid.uuid4()
    contents = await file.read()
    text = contents.decode("utf-8")
    with open(f'sample_{random_id}.py', 'w') as f:
        f.write(f"\n{text}")
    job = Job(user_id=int(current_user.id), status=CeleryStatuses.PENDING, uuid=str(random_id))
    db.add(job)
    await db.commit()
    task = execute_code.delay(str(random_id))
    return TaskEnqueueResponse(task_id=task.id)

@sandbox_router.get('/execute/{task_id}', response_model=CeleryTaskResponse)
async def get_task_res(task_id: str, db: AsyncSession = Depends(get_db)):
    task_result = celery.AsyncResult(task_id)
    print("TASK RESULT", task_result)
    response_schema = CeleryTaskResponse(task_id=task_result.id, task_status=task_result.status, task_result=task_result.result)
    return response_schema