import requests

class PrometheusClient:
    def __init__(self, base_url="http://172.17.99.132:30090/query"):
        self.base_url = base_url

    def _query(self, query: str):
        url = f"{self.base_url}/api/v1/query"
        response = requests.get(url, params={"query": query})
        data = response.json()
        if data.get("status") != "success":
            raise Exception(f"Prometheus query failed: {data}")
        return data["data"]["result"]

    def get_container_metrics(self, container_name: str):
        #query_cpu = f'rate(container_cpu_usage_seconds_total{{name="{container_name}"}}[1m])'
        #query_mem = f'container_memory_usage_bytes{{name="{container_name}"}}'
        query_cpu = f'rate(container_cpu_usage_seconds_total{{id=~".*{container_name}.*"}}[1m])'
        query_mem = f'container_memory_usage_bytes{{id=~".*{container_name}.*"}}'

        cpu_result = self._query(query_cpu)
        mem_result = self._query(query_mem)

        cpu = cpu_result[0]["value"][1] if cpu_result else "N/A"
        mem = mem_result[0]["value"][1] if mem_result else "N/A"

        return {
            "container": container_name,
            "cpu_usage": f"{float(cpu)*100:.2f}%" if cpu != "N/A" else "N/A",
            "memory_usage": f"{int(mem)/1e6:.2f} MB" if mem != "N/A" else "N/A"
        }

    def list_containers(self):
        query = 'container_last_seen'
        result = self._query(query)
        containers = [r["metric"].get("name", "unknown") for r in result]
        return {"containers": list(set(containers))}

    
    def query_range(self, query: str, start, end, step: str = "1m"):
        """Range query (historical time series)."""
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start.isoformat() + "Z",
            "end": end.isoformat() + "Z",
            "step": step,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", {}).get("result", [])