# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import openstack_routes

app = FastAPI(title="MCP-OpenStack-FastAPI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(openstack_routes.router, prefix="/api/v1/openstack")

@app.get("/")
async def root():
    return {"message": "MCP OpenStack FastAPI running!"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=7779,
        reload=True
    )