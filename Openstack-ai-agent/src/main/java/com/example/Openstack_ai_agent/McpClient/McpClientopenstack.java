package com.example.Openstack_ai_agent.McpClient;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@Service
public class McpClientopenstack {

    private final WebClient webClient;

    public McpClientopenstack(@Value("${mcp.server4.url}") String baseUrl) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .build();
    }

    // -----------------------------
    // 1. LIST OPENSTACK SERVICES HEALTH
    // -----------------------------
    public Mono<String> listServices() {
        return webClient.get()
                .uri("/api/v1/openstack/services")
                .retrieve()
                .bodyToMono(String.class);
    }

    // -----------------------------
    // 2. LIST COMPUTE / CONTROLLER NODES
    // -----------------------------
    public Mono<String> listNodes() {
        return webClient.get()
                .uri("/api/v1/openstack/nodes")
                .retrieve()
                .bodyToMono(String.class);
    }

    // -----------------------------
    // 3. GET SERVICE LOGS (via Fluent Bit/Loki)
    // -----------------------------
    public Mono<String> getServiceLogs(String service) {
        return webClient.get()
                .uri("/api/v1/openstack/logs/{service}", service)
                .retrieve()
                .bodyToMono(String.class);
    }

    // -----------------------------
    // 4. GET NODE METRICS (Prometheus)
    // -----------------------------
    public Mono<String> getNodeMetrics(String nodeName) {
        return webClient.get()
                .uri("/api/v1/openstack/metrics/{node}", nodeName)
                .retrieve()
                .bodyToMono(String.class);
    }

    // -----------------------------
    // 5. ANALYZE AN OPENSTACK SERVICE
    // -----------------------------
    public Mono<String> analyzeService(String service) {
        return webClient.get()
                .uri("/api/v1/openstack/analyze/{service}", service)
                .retrieve()
                .bodyToMono(String.class);
    }

}
