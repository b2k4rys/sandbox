from fastapi import FastAPI
from app.auth.router import router
from app.sandbox.router import sandbox_router
app = FastAPI()

app.include_router(router)
app.include_router(sandbox_router)
from settings import SANDBOX_DIR
import os
os.makedirs(f'{SANDBOX_DIR}', exist_ok=True)

@app.get("/")
async def root():

    return {"message": "Hello World"}

