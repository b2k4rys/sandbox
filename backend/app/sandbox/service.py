import os
import subprocess
from backend.app.sandbox.schemas import CodeResponse
from backend.app.sandbox.worker import celery

@celery.task(name="execute_code")
def execute_code(random_id):
    try:
        process = subprocess.run([
            'docker', 'run', '--name', f'output_{random_id}', '--network', 'none',
            '--memory', '128m', '--cpus', '0.5',
            '-v', f'{os.getcwd()}/sample_{random_id}.py:/app/sample.py',
            'test'
        ], timeout=10)
        logs = subprocess.run(['docker', 'logs', f'output_{random_id}'], capture_output=True, text=True)
        schema = CodeResponse(stdout=logs.stdout, stderr=logs.stderr)
        return schema.model_dump()
    except subprocess.TimeoutExpired:
        return CodeResponse(stderr="time limit exceed").model_dump()
    finally:
        subprocess.run(['docker', 'rm', '-f', f'output_{random_id}'])
        os.remove(f'{os.getcwd()}/sample_{random_id}.py')