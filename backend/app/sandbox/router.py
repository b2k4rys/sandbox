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
    try:

        subprocess.run([
            'docker', 'run', '--name', 'output', '--network', 'none',
            '--memory', '128m', '--cpus', '0.5',
            '-v', f'{os.getcwd()}/sample_{random_id}.py:/app/sample.py',
            'test'
        ], timeout=10)
    except subprocess.TimeoutExpired:
        subprocess.run(['docker', 'rm', '-f', 'output'])
        os.remove(f'{os.getcwd()}/sample_{random_id}.py')
        return "Time Limit exceeded"

    logs = subprocess.run(['docker', 'logs', 'output'], capture_output=True, text=True)
    subprocess.run(['docker', 'rm', '-f', 'output'])
    os.remove(f'{os.getcwd()}/sample_{random_id}.py')
    print('here is logs', logs)
    return logs.stdout

