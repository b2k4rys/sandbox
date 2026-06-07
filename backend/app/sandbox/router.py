from fastapi import APIRouter, UploadFile, File
from .service import execute_code
import uuid
import asyncio
import os
sandbox_router = APIRouter(prefix='/sandbox')

@sandbox_router.post('/execute')
async def execute_docker(file: UploadFile = File()):
    random_id = uuid.uuid4()
    output = await execute_code(random_id, file)
    return output
