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
import logging

logger = logging.getLogger(__name__)
import app.models
from settings import SANDBOX_DIR

@celery.task(name="execute_code", track_started=True, bind=True)
def execute_code(self, random_id, code):
    logger.info('INSIDE EXECUTE CODE')
    filename = f'{SANDBOX_DIR}/sample_{random_id}.py'
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(f'{SANDBOX_DIR}/sample_{random_id}.py', 'w') as f:
        logger.info('INSIDE OPEN FILE')
        f.write(f"{code}")

    stmt = select(Job).where(Job.uuid == random_id)
    logger.info("BEFORE SESSION")
    with Session(sync_engine) as db_session:
        try:
            logger.info("INSIDE FIRST TRY/BLOCK")
            job = db_session.scalar(stmt)
            if not job:
                logger.info('NO JOB, YOU ARE LOX')
                os.remove(f'{SANDBOX_DIR}/sample_{random_id}.py')
                return CodeResponse(stderr="job does not exist").model_dump()

            job.status = CeleryStatuses.STARTED
            job.task_id = self.request.id
            db_session.commit()
            # subprocess.run([
            #     'docker', 'run', '--read-only', '--cap-drop', 'ALL', '--name', f'output_{random_id}', '--network', 'none',
            #     '--memory', '128m', '--cpus', '0.5', '--pids-limit', '50', '--security-opt', 'no-new-privileges',
            #     '-v', f'{SANDBOX_DIR}/sample_{random_id}.py',
            #     'test'
            # ], timeout=10)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(f'{SANDBOX_DIR}/sample_{random_id}.py', 'w') as f:
                logger.info('INSIDE OPEN FILE')
                f.write(f"{code}")

            subprocess.run(['docker', 'cp', f'celery_container:{SANDBOX_DIR}/sample_{random_id}.py',
                            f'./{SANDBOX_DIR}/sample_{random_id}.py'])

            subprocess.run(['docker', 'create', '--name', f'output_{random_id}', 'python:3.12-slim'])

            subprocess.run(['docker', 'cp', f'./{SANDBOX_DIR}/sample_{random_id}.py',
                            f'output_{random_id}:/{SANDBOX_DIR}/sample_{random_id}.py'])

            subprocess.run([
                'docker', 'start', f'output_{random_id}',
            ])
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
            logger.info('INSIDE EXCEP TIMEOUT BLOCK')
            job.status = CeleryStatuses.FAILED
            db_session.commit()
            return CodeResponse(stderr="time limit exceed").model_dump()
        finally:
            logger.info("FINAL BLOCK")
            if job is not None:
                logger.info('IN FINALLY BLOCK, THE FILE WILL BE DELETED')
                subprocess.run(['docker', 'rm', '-f', f'output_{random_id}'])
                os.remove(f'{SANDBOX_DIR}/sample_{random_id}.py')
                job.finished_at = datetime.now()
                db_session.commit()