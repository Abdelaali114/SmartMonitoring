from fastapi import FastAPI
from api.prometheus_routes import router as prometheus_router
import uvicorn

app = FastAPI(
    title="MCP Prometheus Monitor",
    version="1.0",
    description="Middleware Control Protocol (MCP) server that provides live container metrics from Prometheus."
)

# Register routes
app.include_router(prometheus_router, prefix="/metrics", tags=["Prometheus"])

@app.get("/")
def root():
    return {"message": "MCP Prometheus Server Running 🚀"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
