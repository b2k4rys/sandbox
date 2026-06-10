from fastapi import FastAPI
from backend.app.auth.router import router
from backend.app.sandbox.router import sandbox_router
app = FastAPI()

app.include_router(router)
app.include_router(sandbox_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

