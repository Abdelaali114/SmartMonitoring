from fastapi import APIRouter, HTTPException
from core.docker_manager import DockerManager
from fastapi import Query
from fastapi import Body

router = APIRouter()
docker_manager = DockerManager()

@router.get("/list")
def list_containers(all: bool = Query(default=False, description="Include stopped containers")):
    try:
        return docker_manager.list_containers(all)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{container_id}/stats")
def get_stats(container_id: str):
    try:
        stats = docker_manager.get_container_stats(container_id)
        return {
            "status": "success",
            "container_id": container_id,
            "formatted": (
                f"📊 Container Stats\n"
                f"----------------------\n"
                f"🧠 CPU total: {stats['cpu_total']} ns\n"
                f"💾 Memory used: {stats['memory_usage']} bytes\n"
                f"📡 Network RX: {stats['network_rx']} bytes\n"
                f"📡 Network TX: {stats['network_tx']} bytes\n"
            ),
            "raw": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{container_id}/start")
def start_container(container_id: str):
    try:
        return {"message": docker_manager.start_container(container_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{container_id}/stop")
def stop_container(container_id: str):
    try:
        return {"message": docker_manager.stop_container(container_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{container_id}/restart")
def restart_container(container_id: str):
    try:
        return {"message": docker_manager.restart_container(container_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/create")
def create_container(
    image: str = Body(..., embed=True),
    name: str = Body(None, embed=True),
    command: str = Body(None, embed=True),
    ports: dict = Body(None, embed=True)
):
    """
    Create a new Docker container.
    Example JSON body:
    {
        "image": "nginx:latest",
        "name": "my-nginx",
        "ports": {"80/tcp": 8080}
    }
    """
    try:
        return docker_manager.create_container(image=image, name=name, command=command, ports=ports)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/{container_id}/logs")
def get_logs(container_id: str, tail: int = 100):
    """
    Get logs for a specific container.
    Example: GET /docker/<container_id>/logs?tail=200
    """
    try:
        return {"logs": docker_manager.get_container_logs(container_id, tail)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/{container_id}/exec")
def exec_command(container_id: str, command: str = Body(..., embed=True)):
    """
    Execute a shell command inside a running container.
    Example:
    {
        "command": "ls -la"
    }
    """
    try:
        result = docker_manager.exec_in_container(container_id, command)
        return {
            "command": result["command"],
            "output": result["output"].strip().replace("\n", "\n📄 ")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/self-heal/ai")
def self_heal_with_analysis():
    """
    Intelligent self-healing using container stats and logs.
    The AI layer will decide whether to restart or not.
    """
    try:
        containers = docker_manager.list_containers(all=True)
        report = []

        for c in containers:
            name = c.get("name")
            cid = c.get("id")

            # 1️⃣ Collect stats and logs
            try:
                stats = docker_manager.get_container_stats(cid)
                logs = docker_manager.get_container_logs(cid)

                cpu = stats.get("cpu_total", 0)
                mem = stats.get("memory_usage", 0)
                status = c.get("status", "")

                report.append({
                    "id": cid,
                    "name": name,
                    "status": status,
                    "cpu": cpu,
                    "memory": mem,
                    "logs": logs[-500:]  # limit for safety
                })
            except Exception as e:
                report.append({"name": name, "error": str(e)})

        return {"analysis_data": report}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    