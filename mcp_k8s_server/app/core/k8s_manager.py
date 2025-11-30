from kubernetes import client, config, stream, utils
from kubernetes.client.rest import ApiException
import yaml
import requests
from fastapi import FastAPI, Query


PROMETHEUS = "http://172.17.99.132:30090/query"



class KubernetesManager:
    def __init__(self):
        # Try in-cluster config first (K8s pod), fallback to local kubeconfig
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()

        self.core = client.CoreV1Api()
        self.apps = client.AppsV1Api()
        self.metrics = client.CustomObjectsApi()
    
    # -------------------------------------------------------
    # CPU METRICS PODS
    # -------------------------------------------------------   
    def get_pod_cpu(pod):
        query = f'container_cpu_usage_seconds_total{{pod="{pod}"}}'
        r = requests.get(PROMETHEUS, params={"query": query}).json()
        return r["data"]["result"]
    
    def get_pod_memory(pod):
        query = f'container_memory_usage_bytes{{pod="{pod}"}}'
        r = requests.get(PROMETHEUS, params={"query": query}).json()
        return r["data"]["result"]


    # -------------------------------------------------------
    # LIST PODS
    # -------------------------------------------------------
    def list_pods(self, namespace: str | None = Query(default=None)):
        if namespace:
            pods = self.core.list_namespaced_pod(namespace)
        else:
            pods = self.core.list_pod_for_all_namespaces()

        result = []
        for p in pods.items:
          result.append({
             "name": p.metadata.name,
             "namespace": p.metadata.namespace,
             "phase": p.status.phase,
             "node": p.spec.node_name,
             "containers": [c.name for c in p.spec.containers]
        })
        return result
        

    # -------------------------------------------------------
    # GET LOGS
    # -------------------------------------------------------
    def get_pod_logs(self, namespace: str, pod_name: str, container: str = None, tail_lines: int = 200):
        try:
            return self.core.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines
            )
        except ApiException as e:
            raise Exception(f"Failed to read logs: {e}")

    # -------------------------------------------------------
    # EXEC IN POD
    # -------------------------------------------------------
    def exec_in_pod(self, namespace: str, pod_name: str, command: list, container: str = None):
        try:
            return stream.stream(
                self.core.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=command,
                container=container,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False
            )
        except ApiException as e:
            raise Exception(f"Exec failed: {e}")

    # -------------------------------------------------------
    # SCALE DEPLOYMENT
    # -------------------------------------------------------
    def scale_deployment(self, namespace: str, deployment_name: str, replicas: int):
        body = {"spec": {"replicas": replicas}}
        return self.apps.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=namespace,
            body=body
        )

    # -------------------------------------------------------
    # APPLY YAML
    # -------------------------------------------------------
    def apply_yaml(self, namespace: str, yaml_text: str):
        k8s_client = client.ApiClient()
        docs = list(yaml.safe_load_all(yaml_text))
        created = []

        for doc in docs:
            if not doc:
                continue

            utils.create_from_yaml(
                k8s_client,
                yaml_objects=[doc],
                namespace=namespace
            )

            created.append({
                "kind": doc.get("kind"),
                "name": doc.get("metadata", {}).get("name")
            })

        return created

    # -------------------------------------------------------
    # GET DEPLOYMENT STATUS
    # -------------------------------------------------------
    
    
    
    
    def get_deployment(self, namespace: str, name: str):
        return self.apps.read_namespaced_deployment(name, namespace)

    
    def analyze_pod(self, namespace: str, pod: str):
      analysis = {}

    # 1. logs
      analysis["logs"] = self.get_pod_logs(namespace, pod, tail_lines=300)

    # 2. events
      events = self.core.list_namespaced_event(namespace)
      analysis["events"] = [
          {
            "type": e.type,
            "reason": e.reason,
            "message": e.message,
            "count": e.count
          }
          for e in events.items if e.involved_object.name == pod
      ]

    # 3. pod status & restart count
      pod_obj = self.core.read_namespaced_pod(pod, namespace)
      analysis["status"] = pod_obj.status.phase

      if pod_obj.status.container_statuses:
          analysis["restarts"] = sum([
              c.restart_count for c in pod_obj.status.container_statuses
          ])
      else:
          analysis["restarts"] = 0

    # 4. metrics
      try:
            analysis["metrics"] = {
                "cpu": self.get_pod_cpu(pod),
                "memory": self.get_pod_memory(pod)
            }
      except:
          analysis["metrics"] = {"cpu": None, "memory": None}

      return analysis
