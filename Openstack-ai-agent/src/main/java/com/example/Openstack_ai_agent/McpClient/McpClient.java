package com.example.Openstack_ai_agent.McpClient;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.HashMap;
import java.util.Map;

@Service
public class McpClient {

    private WebClient webClient;

    @Value("${mcp.server1.url}")
    private String mcpUrl1;

    public McpClient(@Value("${mcp.server1.url}") String mcpUrl1) {
        this.webClient = WebClient.create(mcpUrl1); // MCP server URL
    }

    public Mono<String> listContainers() {
        return webClient.get()
                .uri("/docker/list")
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> getContainerLogs(String containerId, int tail) {
        return webClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/docker/" + containerId + "/logs")
                        .queryParam("tail", tail)
                        .build())
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> stopContainer(String containerId) {
        return webClient.post()
                .uri("/docker/" + containerId + "/stop")
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> startContainer(String containerId) {
        return webClient.post()
                .uri("/docker/" + containerId + "/start")
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> statsContainer(String containerId) {
        return webClient.get()
                .uri("/docker/" + containerId + "/stats")
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> createContainer(String image, String name, String command, Map<String, Integer> ports) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("image", image);
        if (name != null)
            requestBody.put("name", name);
        if (command != null)
            requestBody.put("command", command);
        if (ports != null)
            requestBody.put("ports", ports);

        return webClient.post()
                .uri("/docker/create")
                .body(BodyInserters.fromValue(requestBody))
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> execinContainer(String containerId, String command) {
        return webClient.post()
                .uri("/docker/" + containerId + "/exec")
                .bodyValue(Map.of("command", command))
                .retrieve()
                .bodyToMono(String.class);
    }

    public Mono<String> selfHealAi() {
        return webClient.post()
                .uri("/docker/self-heal/ai")
                .retrieve()
                .bodyToMono(String.class);
    }

}
