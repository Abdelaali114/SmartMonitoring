package com.example.Openstack_ai_agent.McpClient;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.HashMap;
import java.util.Map;

@Service
public class McpClient1 {

    private WebClient webClient;

    @Value("${mcp.server2.url}")
    private String mcpUrl2;

    public McpClient1(
            @Value("${mcp.server2.url}") String mcpUrl2) {

        this.webClient = WebClient.create(mcpUrl2); // MCP server2 URL
    }

    // -------------------- MCP SERVER 2 (Smart Monitoring) --------------------

    public Mono<String> getContainerMetrics(String name) {
        return webClient.get()
                .uri("/metrics/container/" + name)
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> predictContainerHealth(String name, int hours) {
        // String url =
        // String.format("http://localhost:9000/metrics/predict/%s?hours=%d", name,
        // hours);
        return webClient.get()
                // .uri(url)
                .uri("/metrics/predict/{name}?hours={hours}", name, hours)
                .retrieve()
                .bodyToMono(String.class)
                .onErrorResume(e -> Mono.just("❌ Failed to fetch prediction: " + e.getMessage()));
    }
}
