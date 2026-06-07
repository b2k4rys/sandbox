from fastapi import APIRouter, UploadFile, File
from .service import execute_code
sandbox_router = APIRouter(prefix='/sandbox')

@sandbox_router.post('/execute')
async def execute_docker(file: UploadFile = File()):
    output = await execute_code(file)
    return output
