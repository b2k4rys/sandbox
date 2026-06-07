from fastapi import APIRouter, UploadFile, File, Depends
from .service import execute_code
from app.auth.service import get_current_user
from app.auth.models import User
sandbox_router = APIRouter(prefix='/sandbox')

@sandbox_router.post('/execute')
async def execute_docker(file: UploadFile = File(), user: User = Depends(get_current_user)):
    output = await execute_code(file)
    return output
