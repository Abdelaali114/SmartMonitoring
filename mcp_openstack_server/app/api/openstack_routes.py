# api/openstack_routes.py
from fastapi import APIRouter, HTTPException, Body, Query, Request
from typing import Optional, Dict, Any
from app.core.openstack_manager import OpenstackManager

router = APIRouter()
manager = OpenstackManager()  # singleton for the router

@router.post("/ingest")
async def ingest_log(record: Dict[str, Any]):
    """
    Fluent Bit -> HTTP output should post JSON to /api/v1/openstack/ingest
    Example body:
    {
      "timestamp":"2025-11-27T12:00:00Z",
      "node":"compute-1",
      "service":"nova-compute",
      "level":"ERROR",
      "message":"failed to spawn: NoValidHost"
    }
    """
    try:
        return manager.save_log_record(record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
def list_logs(node: Optional[str] = Query(None), service: Optional[str] = Query(None), tail: int = Query(200)):
    try:
        return manager.read_logs(node=node, service=service, tail=tail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events")
def get_events():
    try:
        return manager.list_events()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/{node}/{service}")
def analyze(node: str, service: str):
    try:
        return manager.analyze_service(node, service)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/action/restart")
def restart_service(node: str = Body(..., embed=True), service: str = Body(..., embed=True)):
    try:
        res = manager.restart_service_on_node(node, service)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
