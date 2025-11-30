from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List
from app.core.k8s_manager import KubernetesManager


router = APIRouter()
manager = KubernetesManager()
# GET /nodes
@router.get("/nodes")
def list_nodes():
    try:
        return manager.list_nodes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET /pods
@router.get("/pods")
def list_pods(namespace: Optional[str] = None):
    try:
        return manager.list_pods(namespace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET /pods/{namespace}/{pod}/logs
@router.get("/pods/{namespace}/{pod}/logs")
def pod_logs(
    namespace: str,
    pod: str,
    container: Optional[str] = None,
    tail: int = Query(200)
):
    try:
        return manager.get_pod_logs(namespace, pod, container, tail_lines=tail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST /pods/{namespace}/{pod}/exec
@router.post("/pods/{namespace}/{pod}/exec")
def pod_exec(
    namespace: str,
    pod: str,
    command: List[str] = Body(...)
):
    """Executes a command inside a pod container (non-streaming)"""
    try:
        cli = manager.exec_in_pod(namespace, pod, command)
        output = ""

        # Read output until stream closes
        while cli.is_open():
            cli.update(timeout=1)

            if cli.peek_stdout():
                output += cli.read_stdout()

            if cli.peek_stderr():
                output += cli.read_stderr()

            if not cli.is_open():
                break

        return {"output": output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST /deployments/{namespace}/{name}/scale
@router.post("/deployments/{namespace}/{name}/scale")
def scale_deployment(
    namespace: str,
    name: str,
    replicas: int = Body(..., embed=True)
):
    try:
        res = manager.scale_deployment(namespace, name, replicas)
        return {"message": "scaled", "replicas": replicas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST /apply — apply YAML
@router.post("/apply")
def apply_yaml(
    namespace: str = Body("default"),
    yaml_text: str = Body(..., embed=True)
):
    try:
        created = manager.apply_yaml(namespace, yaml_text)
        return {"applied": created}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{namespace}/{pod}")
def analyze(namespace: str, pod: str):
    try:
        return manager.analyze_pod(namespace, pod)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

