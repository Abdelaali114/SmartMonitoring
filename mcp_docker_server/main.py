from fastapi import FastAPI
from api import docker_control

app = FastAPI(title="MCP Docker Manager", version="1.0")

# Register router
app.include_router(docker_control.router, prefix="/docker", tags=["Docker"])

@app.get("/")
async def root():
    return {"message": "MCP Docker Manager is running 🚀"}
