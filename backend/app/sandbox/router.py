from fastapi import APIRouter, UploadFile, File
import subprocess
from asyncio import sleep
import uuid
sandbox_router = APIRouter(prefix='/sandbox')
import os

@sandbox_router.post('/execute')
async def execute_docker(file: UploadFile = File()):
    contents = await file.read()
    text = contents.decode("utf-8")
    random_id = uuid.uuid4()

    with open(f'sample_{random_id}.py', 'w') as file:
        file.write(f"\n{text}")

    subprocess.run([
        'docker', 'run', '--name', 'output', '--network', 'none',
        '-v', f'{os.getcwd()}/sample_{random_id}.py:/app/sample.py',
        'test'
    ])
    logs = subprocess.run(['docker', 'logs', 'output'], capture_output=True, text=True)
    subprocess.run(['docker', 'rm', '-f', 'output'])
    print('here is logs', logs)
    return logs.stdout

