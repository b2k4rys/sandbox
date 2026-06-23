from fastapi import APIRouter, UploadFile, File, Depends, Request, HTTPException
from fastapi.params import Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.sandbox.schemas import CeleryTaskResponse, TaskEnqueueResponse
from app.sandbox.worker import celery
from app.sandbox.service import execute_code
from app.auth.service import get_current_user, get_current_user_optional
from app.auth.models import User
from typing import Annotated
from app.sandbox.models import Job, CeleryStatuses
import uuid
from app.sandbox.rate_limiter import RateLimiter
from database import get_db
import redis
import redis.asyncio as aioredis

from settings import RATE_LIMIT

r = aioredis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
sandbox_router = APIRouter(prefix='/sandbox')

# @sandbox_router.post('/execute', response_model=TaskEnqueueResponse)
@sandbox_router.post('/execute')
async def execute_docker(
        request: Request,
        code: Annotated[str, Body(embed=True)],
        current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
        db: AsyncSession = Depends(get_db)
):
    random_id = uuid.uuid4()
    client_id = request.client.host
    curr = await r.incr(str(client_id))

    if curr == 1:
        await r.expire(client_id, 60)
    if curr > int(RATE_LIMIT):
        raise HTTPException(429)
    user_id = int(current_user.id) if current_user else None
    job = Job(status=CeleryStatuses.PENDING, uuid=str(random_id), user_id=user_id)
    db.add(job)
    await db.commit()
    task = execute_code.delay(str(random_id), code)
    return TaskEnqueueResponse(task_id=task.id)

@sandbox_router.get('/execute/{task_id}', response_model=CeleryTaskResponse)
async def get_task_res(task_id: str, db: AsyncSession = Depends(get_db)):
    task_result = celery.AsyncResult(task_id)
    response_schema = CeleryTaskResponse(task_id=task_result.id, task_status=task_result.status, task_result=task_result.result)
    return response_schema