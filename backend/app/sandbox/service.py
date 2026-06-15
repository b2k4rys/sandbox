import os
import subprocess
from sqlalchemy import select

from app.sandbox.models import Job, CeleryStatuses
from database import sync_engine
from app.sandbox.schemas import CodeResponse
from app.sandbox.worker import celery
from sqlalchemy.orm import Session

@celery.task(name="execute_code", track_started=True)
def execute_code(random_id):
    stmt = select(Job).where(Job.uuid == random_id)
    try:
        with Session(sync_engine) as session:
            job = session.scalar(stmt)
            job.status = CeleryStatuses.RUNNING
            session.commit()

        subprocess.run([
            'docker', 'run', '--name', f'output_{random_id}', '--network', 'none',
            '--memory', '128m', '--cpus', '0.5',
            '-v', f'{os.getcwd()}/sample_{random_id}.py:/app/sample.py',
            'test'
        ], timeout=10)
        logs = subprocess.run(['docker', 'logs', f'output_{random_id}'], capture_output=True, text=True)
        schema = CodeResponse(stdout=logs.stdout, stderr=logs.stderr)
        with Session(sync_engine) as session:
            job = session.scalar(stmt)
            job.stdout = schema.stdout
            job.status = CeleryStatuses.SUCCESS
            session.commit()
        return schema.model_dump()
    except subprocess.TimeoutExpired:
        return CodeResponse(stderr="time limit exceed").model_dump()
    finally:
        subprocess.run(['docker', 'rm', '-f', f'output_{random_id}'])
        os.remove(f'{os.getcwd()}/sample_{random_id}.py')