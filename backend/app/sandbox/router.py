from fastapi import APIRouter, UploadFile, File

import uuid
import asyncio
import os
sandbox_router = APIRouter(prefix='/sandbox')

@sandbox_router.post('/execute')
async def execute_docker(file: UploadFile = File()):
    contents = await file.read()
    text = contents.decode("utf-8")
    random_id = uuid.uuid4()

    with open(f'sample_{random_id}.py', 'w') as file:
        file.write(f"\n{text}")
    try:
        process = await asyncio.create_subprocess_exec(
            'docker', 'run', '--name', f'output_{random_id}', '--network', 'none',
            '--memory', '128m', '--cpus', '0.5', '--pids-limit', '64',
            '-v', f'{os.getcwd()}/sample_{random_id}.py:/app/sample.py',
            'test'
        )
        await asyncio.wait_for(process.wait(), timeout=10)
        logs = await asyncio.create_subprocess_exec(
            'docker', 'logs', f'output_{random_id}',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await logs.communicate()
        if stderr:
            return stderr
        return stdout
    except asyncio.TimeoutError:
        return "Time Limit exceeded"
    finally:
        await asyncio.create_subprocess_exec('docker', 'rm', '-f', f'output_{random_id}')
        os.remove(f'{os.getcwd()}/sample_{random_id}.py')

