from fastapi import APIRouter, UploadFile, File
import subprocess
from asyncio import sleep
sandbox_router = APIRouter(prefix='/sandbox')
import os

@sandbox_router.post('/execute')
async def execute_docker(file: UploadFile = File()):
    contents = await file.read()

    text = contents.decode("utf-8")
    with open('sample.py', 'w') as file:
        file.write(f"\n{text}")
    await sleep(1)
    subprocess.run([
        'docker', 'run', '--name', 'output',
        '-v', f'{os.getcwd()}/sample.py:/app/sample.py',
        'test'
    ])
    logs = subprocess.run(['docker', 'logs', 'output'], capture_output=True, text=True)
    subprocess.run(['docker', 'rm', '-f', 'output'])
    print('here is logs', logs)
    return logs.stdout

