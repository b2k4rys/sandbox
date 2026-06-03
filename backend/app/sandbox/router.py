from fastapi import APIRouter
import subprocess
from asyncio import sleep
sandbox_router = APIRouter(prefix='/sandbox')


@sandbox_router.post('/execute')
async def execute_docker(text=''):
    with open('sample.py', 'a') as file:
        file.write(f"\n{text}")
    await sleep(1)
    build = subprocess.run(['docker', 'build', '-t', 'test'])
    run = subprocess.run(['docker', 'run','--name', 'output', 'test'])
    logs = subprocess.run(['docker', 'logs', 'output'], capture_output=True, text=True)
    delete = subprocess.run(['docker', 'rm', '-f', 'output'])
    print('here is logs', logs)
    return logs.stdout

