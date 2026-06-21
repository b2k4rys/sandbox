import os
import subprocess
from sqlalchemy import select
from datetime import datetime
from database import sync_engine
from app.sandbox.schemas import CodeResponse
from app.sandbox.worker import celery
from sqlalchemy.orm import Session
from app.sandbox.models import Job, CeleryStatuses
# import needed for worker
import app.models

@celery.task(name="execute_code", track_started=True, bind=True)
def execute_code(self, random_id, code):
    with open(f'sample_{random_id}.py', 'w') as f:
        f.write(f"{code}")
    stmt = select(Job).where(Job.uuid == random_id)

    with Session(sync_engine) as db_session:
        try:
            job = db_session.scalar(stmt)
            if not job:
                os.remove(f'{os.getcwd()}/sample_{random_id}.py')
                return CodeResponse(stderr="job does not exist").model_dump()
            job.status = CeleryStatuses.STARTED
            job.task_id = self.request.id
            db_session.commit()
            subprocess.run([
                'docker', 'run', '--read-only', '--cap-drop', 'ALL', '--name', f'output_{random_id}', '--network', 'none',
                '--memory', '128m', '--cpus', '0.5', '--pids-limit', '50', '--security-opt', 'no-new-privileges',
                '-v', f'{os.getcwd()}/sample_{random_id}.py:/app/sample.py',
                'test'
            ], timeout=10)
            job.status = CeleryStatuses.RUNNING
            db_session.commit()

            logs = subprocess.run(['docker', 'logs', f'output_{random_id}'], capture_output=True, text=True)
            schema = CodeResponse(stdout=logs.stdout, stderr=logs.stderr)

            job.stdout = schema.stdout
            job.stderr = schema.stderr
            job.status = CeleryStatuses.SUCCESS
            db_session.commit()
            return schema.model_dump()
        except subprocess.TimeoutExpired:
            job.status = CeleryStatuses.FAILED
            db_session.commit()
            return CodeResponse(stderr="time limit exceed").model_dump()
        finally:
            if job is not None:
                subprocess.run(['docker', 'rm', '-f', f'output_{random_id}'])
                os.remove(f'{os.getcwd()}/sample_{random_id}.py')
                job.finished_at = datetime.now()
                print(job)
                db_session.commit()