from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, k8s_routes

app = FastAPI(title="MCP-K8s-FastAPI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(k8s_routes.router, prefix="/k8s")

@app.get("/")
async def root():
    return {"message": "MCP K8s FastAPI running!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=7777,
        reload=True
    )
