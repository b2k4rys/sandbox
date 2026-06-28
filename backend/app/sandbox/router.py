import asyncio
from fastapi import APIRouter, Request, HTTPException, WebSocket
from fastapi.params import Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from app.sandbox.schemas import CeleryTaskResponse, TaskEnqueueResponse
from app.sandbox.worker import celery
from app.sandbox.service import execute_code
from app.auth.service import get_current_user, get_current_user_optional
from app.auth.models import User
from typing import Annotated
from app.sandbox.models import Job, CeleryStatuses
import uuid
from database import get_db
import redis.asyncio as aioredis

from settings import RATE_LIMIT, CELERY_RESULT_BACKEND

r = aioredis.from_url(CELERY_RESULT_BACKEND)
sandbox_router = APIRouter(prefix='/sandbox')


# TODO: X-Forwarded-For when behind a proxy
# TODO: token-bucket if boundary burst matters
@sandbox_router.post('/execute', response_model=TaskEnqueueResponse)
# @sandbox_router.post('/execute')
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
# @sandbox_router.get('/execute/{task_id}')
async def get_task_res(task_id: str, db: AsyncSession = Depends(get_db)):
    task_result = celery.AsyncResult(task_id)
    response_schema = CeleryTaskResponse(task_id=task_result.id, task_status=task_result.status, task_result=task_result.result)
    return response_schema


@sandbox_router.websocket("/ws/session")
# @sandbox_router.post('/execute')
async def websocket_session(
        websocket: WebSocket,
        db: AsyncSession = Depends(get_db),
):
    client_id = websocket.client.host
    curr = await r.incr(str(client_id))

    if curr == 1:
        await r.expire(client_id, 60)

    if curr > int(RATE_LIMIT):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    data = await websocket.receive_text()
    await websocket.send_text(f"message text was {data}")
    random_id = uuid.uuid4()
    job = Job(status=CeleryStatuses.PENDING, uuid=str(random_id), user_id=None)
    db.add(job)
    await db.commit()
    task = execute_code.delay(str(random_id), data)
    res = celery.AsyncResult(task.id)

    try:
        while True:
            await websocket.send_text(f"curr is {curr}")
            res = celery.AsyncResult(task.id)
            await websocket.send_text(f"status: {res.status}")
            if res.status in ('SUCCESS', 'FAILURE'):
                response =  CeleryTaskResponse(task_id=task.id, task_status=res.status, task_result=res.result)
                await websocket.send_json(response.model_dump())
                await websocket.close(code=1000)
                return

    except WebSocketDisconnect:
        print("Client disconnected cleanly")
    except Exception as e:
        print(f"Something went wrong: {e}")
        await websocket.close(code=1011)

