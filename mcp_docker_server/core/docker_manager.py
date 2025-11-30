import docker

class DockerManager:
    def __init__(self):
        self.client = docker.from_env()

    def list_containers(self, all=False):
        containers = self.client.containers.list(all=all)
        return [
            {
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "image": c.image.tags,
            }
            for c in containers
        ]

    def get_container_stats(self, container_id: str):
        container = self.client.containers.get(container_id)
        stats = container.stats(stream=False)
        return {
            "cpu_total": stats["cpu_stats"]["cpu_usage"]["total_usage"],
            "memory_usage": stats["memory_stats"]["usage"],
            "network_rx": stats["networks"]["eth0"]["rx_bytes"],
            "network_tx": stats["networks"]["eth0"]["tx_bytes"],
        }

    def start_container(self, container_id: str):
        c = self.client.containers.get(container_id)
        c.start()
        return f"Container {c.name} started."

    def stop_container(self, container_id: str):
        c = self.client.containers.get(container_id)
        c.stop()
        return f"Container {c.name} stopped."

    def restart_container(self, container_id: str):
        c = self.client.containers.get(container_id)
        c.restart()
        return f"Container {c.name} restarted."
    
    def create_container(self, image: str, name: str = None, command: str = None, ports: dict = None):
        """
        Create and start a new Docker container.
        """
        try:
            container = self.client.containers.run(
                image=image,
                name=name,
                command=command,
                ports=ports,
                detach=True  # run in background
            )
            return {
                "message": f"Container '{container.name}' created and started successfully.",
                "id": container.short_id,
                "image": image,
                "status": container.status
            }
        except docker.errors.ImageNotFound:
            # Optional: auto-pull if not found
            self.client.images.pull(image)
            container = self.client.containers.run(
                image=image,
                name=name,
                command=command,
                ports=ports,
                detach=True
            )
            return {
                "message": f"Image '{image}' pulled and container '{container.name}' started.",
                "id": container.short_id,
                "status": container.status
            }
        except docker.errors.APIError as e:
            raise Exception(f"Docker API error: {e.explanation}")
    
    
    def get_container_logs(self, container_id: str, tail: int = 100):
        container = self.client.containers.get(container_id)
        logs = container.logs(tail=tail).decode("utf-8")
        return logs
    
    def exec_in_container(self, container_id: str, command: str):
        """
        Execute a shell command inside a running container.
         Returns the command output.
        """
        container = self.client.containers.get(container_id)

        if container.status != "running":
           raise Exception(f"Container {container_id} is not running.")

        exec_result = container.exec_run(command)
        output = exec_result.output.decode("utf-8", errors="ignore")
        return {"command": command, "output": output}


    
