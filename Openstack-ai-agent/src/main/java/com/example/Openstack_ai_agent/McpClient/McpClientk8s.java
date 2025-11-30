package com.example.Openstack_ai_agent.McpClient;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import jakarta.annotation.PostConstruct;
import reactor.core.publisher.Mono;

@Service
public class McpClientk8s {

        private final WebClient webClient;

        public McpClientk8s(@Value("${mcp.server3.url}") String baseUrl) {
                this.webClient = WebClient.builder()
                                .baseUrl(baseUrl)
                                .build();
        }

        public Mono<String> listPods() {
                return webClient.get()
                                .uri("/k8s/pods")
                                .retrieve()
                                .bodyToMono(String.class);
        }

        public Mono<String> listPodsInNamespace(String namespace) {
                return webClient.get()
                                .uri(uriBuilder -> uriBuilder
                                                .path("/k8s/pods")
                                                .queryParam("namespace", namespace)
                                                .build())
                                .retrieve()
                                .bodyToMono(String.class);
        }

        public Mono<String> getPodLogs(String namespace, String pod) {
                return webClient.get()
                                .uri("/k8s/pods/{namespace}/{pod}/logs", namespace, pod)
                                .retrieve()
                                .bodyToMono(String.class);
        }

        public Mono<String> execInPod(String namespace, String pod, String[] command) {
                return webClient.post()
                                .uri("/k8s/pods/{namespace}/{pod}/exec", namespace, pod)
                                .bodyValue(command)
                                .retrieve()
                                .bodyToMono(String.class);
        }

        public Mono<String> scaleDeployment(String namespace, String name, int replicas) {
                return webClient.post()
                                .uri("/api/v1/k8s/deployments/{namespace}/{name}/scale", namespace, name)
                                .bodyValue("{\"replicas\":" + replicas + "}")
                                .retrieve()
                                .bodyToMono(String.class);
        }

        public Mono<String> applyYaml(String namespace, String yamlText) {
                return webClient.post()
                                .uri("/api/v1/k8s/apply")
                                .bodyValue("{\"namespace\":\"" + namespace + "\", \"yaml_text\": \"" +
                                                yamlText.replace("\"", "\\\"") + "\"}")
                                .retrieve()
                                .bodyToMono(String.class);
        }

        public Mono<String> analyzePod(String namespace, String pod) {
                return webClient.get()
                                .uri("/k8s/analyze/{namespace}/{pod}", namespace, pod)
                                .retrieve()
                                .bodyToMono(String.class);
        }
}
