from fastapi import APIRouter, UploadFile, File, Depends
from .service import execute_code
from app.auth.service import get_current_user
from app.auth.models import User
from fastapi.params import Depends
from typing import Annotated
from app.auth.service import get_current_user
from app.auth.models import User
sandbox_router = APIRouter(prefix='/sandbox')

@sandbox_router.post('/execute')
async def execute_docker(current_user: Annotated[User, Depends(get_current_user)], file: UploadFile = File()):
    output = await execute_code(file)
    return output
