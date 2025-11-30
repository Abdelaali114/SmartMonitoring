package com.example.Openstack_ai_agent.AgentAI;

import com.example.Openstack_ai_agent.McpClient.McpClient;
import com.example.Openstack_ai_agent.McpClient.McpClient1;
import com.example.Openstack_ai_agent.McpClient.McpClientk8s;
import com.example.Openstack_ai_agent.McpClient.McpClientopenstack;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.MessageChatMemoryAdvisor;
import org.springframework.ai.chat.client.advisor.SimpleLoggerAdvisor;
import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.regex.Pattern;
import java.util.regex.Matcher;

import java.util.HashMap;
import java.util.Map;

@Service
public class Aiagent {
    private final ChatClient chatClient;
    private final McpClient mcpClient;
    private final McpClientk8s mcpClientk8s;
    private final McpClientopenstack mcpClientopenstack;
    private final McpClient1 mcpClient1;

    public Aiagent(
            ChatClient.Builder chatClient,
            ChatMemory chatMemory,
            McpClient mcpClient,
            McpClient1 mcpClient1,
            McpClientopenstack mcpClientopenstack,
            McpClientk8s mcpClientk8s) {
        this.mcpClient = mcpClient;
        this.mcpClient1 = mcpClient1;
        this.mcpClientk8s = mcpClientk8s;
        this.mcpClientopenstack = mcpClientopenstack;

        this.chatClient = chatClient
                .defaultSystem(
                        """
                                     You are a multi-agent AI system that can reason and act through multiple MCP APIs.

                                    === Your Capabilities ===
                                    1/ Docker MCP:
                                        - Manage and control containers.
                                        - Available actions: list, start, stop, restart, inspect, logs, execute commands.
                                        - Base URL: ${mcp.server1.url}

                                    2/ Prometheus MCP:
                                        - Monitor and analyze live metrics.
                                        - Available actions: query metrics, detect anomalies, report container health.
                                        - Base URL: ${mcp.server2.url}

                                    === Decision Rules ===
                                    - If the user requests container management or execution → use the Docker MCP.
                                    - If the user requests monitoring, metrics, or alerting → use the Prometheus MCP.
                                    - If the user asks for self-healing → combine both: analyze metrics from Prometheus, then act via Docker MCP.

                                    === Response Style ===
                                    - Always explain briefly what you’re doing before calling an MCP endpoint.
                                    - Format the output neatly with emojis and clear sections (e.g., ✅, ⚠️, 📊, 🔧).
                                    - Keep all reasoning concise, but actionable.

                                    === Example Thought Process ===
                                    User: "Check if any container is over CPU limit"
                                    You:
                                      1. Query Prometheus MCP for CPU metrics.
                                      2. Identify containers exceeding threshold.
                                      3. Optionally suggest a Docker action (restart or scale).

                                    You are designed to reason like a DevOps AI co-pilot with autonomous decision-making.
                                """)
                .defaultAdvisors(MessageChatMemoryAdvisor.builder(chatMemory).build())
                .defaultAdvisors(new SimpleLoggerAdvisor())
                .build();
    }

    // 🐳 Format container list output
    private String formatContainerList(String json) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode containers = mapper.readTree(json);

            if (!containers.isArray() || containers.size() == 0) {
                return "⚠️ No containers found.";
            }

            StringBuilder sb = new StringBuilder();
            sb.append("🐳 Docker Containers\n");
            sb.append("--------------------------\n");

            for (JsonNode c : containers) {
                String name = c.has("name") ? c.get("name").asText() : "unknown";
                String id = c.has("id") ? c.get("id").asText() : "n/a";
                String status = c.has("status") ? c.get("status").asText() : "unknown";

                String icon = status.toLowerCase().contains("running") ? "🟢" : "🔴";

                sb.append(icon)
                        .append(" ").append(name)
                        .append(" (").append(id.substring(0, Math.min(id.length(), 8))).append(")")
                        .append(" — ").append(status)
                        .append("\n");
            }

            return sb.toString();

        } catch (Exception e) {
            return "⚠️ Error formatting container list: " + e.getMessage() + "\nRaw data: " + json;
        }
    }

    // Interpret the user's query
    public Flux<String> onQuery(String query) {
        String lower = query.toLowerCase();

        if (lower.contains("list") && lower.contains("container")) {
            return mcpClient.listContainers()
                    .map(this::formatContainerList)
                    .flux();

        } else if (lower.contains("stop")) {
            String id = extractId(lower);
            return mcpClient.stopContainer(id).flux();

        } else if (lower.contains("start")) {
            String id = extractId(lower);
            return mcpClient.startContainer(id).flux();

        } else if (lower.contains("stats")) {
            String id = extractId(lower);
            return mcpClient.statsContainer(id)
                    .flatMapMany(stats -> chatClient.prompt()
                            .system("Format the following container stats nicely for the user:")
                            .user(stats)
                            .stream()
                            .content());

        } else if (lower.contains("create") || lower.contains("run")) {
            // detect image name and decide what to pull
            return handleCreateCommand(lower);

        } else if (lower.contains("log") || lower.contains("logs")) {
            String id = extractId(lower);
            return mcpClient.getContainerLogs(id, 100)
                    .flatMapMany(logs -> chatClient.prompt()
                            .system("Analyze the following Docker container logs. " +
                                    "Detect possible errors, warnings, or useful insights. " +
                                    "Use emojis, tables, and bullet points" +
                                    "Summarize them clearly for the user." +
                                    "if there is an error or a warning propose the soulution to solve it ")
                            .user(logs)
                            .stream()
                            .content());
        } else if (lower.contains("execute") || lower.contains("run command")) {
            String containerId = extractId(lower);
            String command = extractCommand(lower);

            return mcpClient.execinContainer(containerId, command)
                    .flatMapMany(rawJson -> {
                        try {
                            ObjectMapper mapper = new ObjectMapper();
                            JsonNode node = mapper.readTree(rawJson);
                            String cmd = node.get("command").asText();
                            String output = node.get("output").asText();

                            // Ask the AI model to format & interpret it
                            return chatClient.prompt()
                                    .system("You are a DevOps assistant. Format this command output for clarity. " +
                                            "Use emojis, tables, and bullet points. If the command is 'ls', show directories with 📁; "
                                            +
                                            "if it's 'ps' or 'top', show a clean table; if it's text output, just format it nicely.")
                                    .user("Command: " + cmd + "\nOutput:\n" + output)
                                    .stream()
                                    .content();

                        } catch (Exception e) {
                            return Flux.just("⚠️ Error parsing command output: " + e.getMessage());
                        }
                    });
        } else if (lower.contains("analyze") || lower.contains("intelligent heal") || lower.contains("smart heal")) {
            return mcpClient.selfHealAi()
                    .flatMapMany(data -> chatClient.prompt()
                            .system("""
                                        You are an AI ops engineer.
                                        Use emojis, tables, and bullet points .
                                        You are given Docker container health reports with stats and logs.
                                        Your job is to:
                                        - Identify containers that might be failing or unstable
                                        - Explain the likely reason (e.g., OOM, network error, crash loop)
                                        - Decide what to do: restart, ignore, or scale
                                        - Output the reasoning in a clear format with emojis and bullet points
                                    """)
                            .user(data)
                            .stream()
                            .content());
        } else if (lower.contains("@monitor-boot") && (lower.contains("metrics") || lower.contains("usage"))) {
            String name = extractName(lower);
            return mcpClient1.getContainerMetrics(name)
                    .flatMapMany(metricsJson -> chatClient.prompt()
                            .system("""
                                        You are a monitoring assistant. Analyze the container metrics below and
                                        give a clear health summary with recommendations.
                                        Use emojis and short explanations.
                                    """)
                            .user(metricsJson)
                            .stream()
                            .content());

        } else if (lower.contains("@monitor-boot") && lower.contains("predict")) {
            String name = extractName(lower);
            int hours = extractHours(lower);

            return mcpClient1.predictContainerHealth(name, hours)
                    .flatMapMany(predictionJson -> chatClient.prompt()
                            .system("""
                                    You are a predictive monitoring agent 🧠.
                                    Use emojis, tables, and bullet points .
                                    Your role is to analyze prediction results for container health and
                                    provide a friendly, human-readable summary.

                                    - If the risk level is CRITICAL, emphasize urgency (🚨) and mention that an email alert was sent.
                                    - If it's WARNING, suggest cautious actions (🟠).
                                    - If it's NORMAL, reassure the user (🟢).
                                    - Summarize CPU and memory trends clearly.
                                    - Always use emojis and keep the tone professional but friendly.
                                    - End with a short insight or recommendation.
                                    """)
                            .user(predictionJson)
                            .stream()
                            .content());

        } else if (lower.contains("k8s") &&
                lower.contains("namespace") &&
                lower.contains("pods") &&
                (lower.contains("list") || lower.contains("show"))) {

            String[] np = extractNamespaceAndPod(lower);
            String namespace = np[0];

            return mcpClientk8s.listPodsInNamespace(namespace)
                    .flatMapMany(json -> chatClient.prompt()
                            .system("""
                                        Format this Kubernetes pod list in a clean readable format.
                                        Use emojis and show:
                                        - Pod name
                                        - Namespace
                                        - Status
                                        - Node
                                        - Containers
                                    """)
                            .user(json)
                            .stream()
                            .content());
        } else if (lower.contains("k8s") &&
                lower.contains("log") && // logs, log
                lower.contains("pod") // pod name
        ) {
            String[] np = extractNamespaceAndPod(lower);
            String namespace = np[0];
            String pod = np[1];

            return mcpClientk8s.getPodLogs(namespace, pod)
                    .flatMapMany(logs -> chatClient.prompt()
                            .system("""
                                        You are a Kubernetes log analysis assistant.
                                        Analyze these pod logs:
                                        - Detect errors (CrashLoopBackOff, OOMKilled, ImagePull errors)
                                        - Summarize the root cause
                                        - Suggest 1–3 fixes
                                        - Use emojis and concise explanations
                                    """)
                            .user(logs)
                            .stream()
                            .content());
        }

        else if (lower.contains("@k8s-boot") && (lower.contains("analyze pod") || lower.contains("check pod"))) {

            String[] np = extractNamespaceAndPod(lower);
            String namespace = np[0];
            String pod = np[1];

            return mcpClientk8s.getPodLogs(namespace, pod)
                    .flatMapMany(logs -> chatClient.prompt()
                            .system("""
                                        You are a Kubernetes log analysis assistant.
                                        Analyze these pod logs:
                                        - Identify errors (CrashLoopBackOff, OOMKilled, ImagePull errors)
                                        - Summarize the root cause
                                        - Suggest 1–3 fixes
                                        - Use emojis and concise explanations.
                                        Include the namespace and pod name at the beginning.
                                    """)
                            .user("Namespace: " + namespace + "\nPod: " + pod + "\n\nLogs:\n" + logs)
                            .stream()
                            .content());
        }
        // openstack///////////////////////////////////////////////////////////////
        else if (lower.contains("openstack") && lower.contains("list nodes")) {
            return mcpClientopenstack.listNodes().flux();
        } else if (lower.contains("openstack") && lower.contains("list services")) {
            return mcpClientopenstack.listServices().flux();
        } else if (lower.contains("openstack") && lower.contains("analyze")) {
            String service = extractServiceName(lower);

            return mcpClientopenstack.analyzeService(service)
                    .flatMapMany(json -> chatClient.prompt()
                            .system("""
                                        You are an OpenStack troubleshooting assistant.
                                        Analyze the service health, logs, metrics:
                                        - Detect failures (API down, message queue, DB issues)
                                        - Identify controllers/compute issues
                                        - Suggest fixes (restart service, check RabbitMQ, DB, network)
                                        Use emojis and structured bullet points.
                                    """)
                            .user(json)
                            .stream()
                            .content());
        }

        else {
            // Not a Docker command → use the AI model normally
            return chatClient.prompt()
                    .user(query)
                    .stream()
                    .content();
        }
    }

    private String[] extractNamespaceAndPod(String query) {
        query = query.toLowerCase().trim();

        String namespace = "default"; // fallback if not specified
        String pod = null;

        // Case 1: "namespace xyz" pattern
        Pattern nsPattern = Pattern.compile("namespace\\s+([a-z0-9-]+)");
        Matcher nsMatcher = nsPattern.matcher(query);
        if (nsMatcher.find()) {
            namespace = nsMatcher.group(1);
        }

        // Case 2: "ns xyz" shorthand
        Pattern nsShort = Pattern.compile("\\sns\\s+([a-z0-9-]+)");
        Matcher nsShortMatch = nsShort.matcher(query);
        if (nsShortMatch.find()) {
            namespace = nsShortMatch.group(1);
        }

        // Case 3: "pod xyz"
        Pattern podPattern = Pattern.compile("pod\\s+([a-z0-9-]+)");
        Matcher podMatcher = podPattern.matcher(query);
        if (podMatcher.find()) {
            pod = podMatcher.group(1);
        }

        // Case 4: "namespace/pod" format
        Pattern nsPodPattern = Pattern.compile("([a-z0-9-]+)/([a-z0-9-]+)");
        Matcher nsPodMatcher = nsPodPattern.matcher(query);
        if (nsPodMatcher.find()) {
            namespace = nsPodMatcher.group(1);
            pod = nsPodMatcher.group(2);
        }

        // If pod still null → fallback to last word
        if (pod == null) {
            String[] words = query.split("\\s+");
            pod = words[words.length - 1];
        }

        return new String[] { namespace, pod };
    }

    private int extractHours(String query) {
        Pattern pattern = Pattern.compile("(\\d+)\\s*hour");
        Matcher matcher = pattern.matcher(query);
        if (matcher.find()) {
            return Integer.parseInt(matcher.group(1));
        }
        return 1; // default to 1 hour if not specified
    }

    private String extractContainerName(String query) {
        // Normalize the query
        String lower = query.toLowerCase().trim();

        // This regex covers multiple possible phrasings:
        // - "@monitor-boot predict prometheus next 2 hours"
        // - "@monitor-boot predict nginx for 1 hour"
        // - "predict container prometheus"
        Pattern pattern = Pattern.compile("(?:@monitor-boot\\s+)?predict\\s+(?:container\\s+)?([\\w-]+)");
        Matcher matcher = pattern.matcher(lower);

        if (matcher.find()) {
            return matcher.group(1);
        }

        // Fallback: try generic name extraction
        String[] tokens = lower.split("\\s+");
        for (int i = 0; i < tokens.length; i++) {
            if (tokens[i].equals("predict") && i + 1 < tokens.length) {
                return tokens[i + 1];
            }
        }

        return "unknown";
    }

    private String extractName(String query) {
        if (query == null || query.isEmpty()) {
            return null;
        }
        String lower = query.toLowerCase().trim();
        String[] keywords = { "container", "of", "called", "named", "for", "service", "app" };
        String[] tokens = lower.split("[\\s,.;:!?]+");

        for (int i = 0; i < tokens.length; i++) {
            if (i > 0 && java.util.Arrays.asList(keywords).contains(tokens[i - 1])) {
                return tokens[i];
            }
        }
        if (tokens.length > 0) {
            return tokens[tokens.length - 1];
        }

        return null;
    }

    // Simple ID extractor
    private String extractId(String query) {
        String[] parts = query.split(" ");
        return parts[parts.length - 1];
    }

    // Simple sirvice extractor
    private String extractServiceName(String query) {
        String[] words = query.split("\\s+");
        for (int i = 0; i < words.length; i++) {
            if (words[i].equals("service") && i + 1 < words.length) {
                return words[i + 1];
            }
        }
        return words[words.length - 1];
    }

    // command extractor
    private String extractCommand(String query) {
        // Example queries:
        // "run command ls -la / in container 123abc"
        // "execute 'df -h' inside container abc123"
        // "in container 12ab34cd, run ps aux"

        // Make everything lowercase to simplify
        String lower = query.toLowerCase();

        // Find the start of the command
        String command = "";

        // Case 1: quoted command
        if (query.contains("'")) {
            // Extract whatever is between the first and last single quote
            int first = query.indexOf("'");
            int last = query.lastIndexOf("'");
            if (first != last) {
                command = query.substring(first + 1, last);
            }
        }
        // Case 2: uses the word "command"
        else if (lower.contains("command")) {
            command = query.substring(lower.indexOf("command") + 7).trim();
        }
        // Case 3: uses the word "run"
        else if (lower.contains("run")) {
            command = query.substring(lower.indexOf("run") + 3).trim();
        }

        // Clean it up — remove common container context
        command = command.replaceAll("in container.*", "").trim();
        command = command.replaceAll("inside container.*", "").trim();

        if (command.isEmpty()) {
            command = "ls"; // default command if nothing detected
        }

        return command;
    }

    // Handle create commands like "create a mongodb container"
    private Flux<String> handleCreateCommand(String query) {
        Map<String, String> imageMap = new HashMap<>();
        imageMap.put("mongo", "mongo:latest");
        imageMap.put("redis", "redis:latest");
        imageMap.put("nginx", "nginx:latest");
        imageMap.put("postgres", "postgres:latest");
        imageMap.put("mysql", "mysql:latest");
        imageMap.put("hello", "hello-world");

        Map<String, Integer> defaultPorts = new HashMap<>();
        defaultPorts.put("mongo", 27017);
        defaultPorts.put("redis", 6379);
        defaultPorts.put("nginx", 80);
        defaultPorts.put("postgres", 5432);
        defaultPorts.put("mysql", 3306);
        defaultPorts.put("hello", 8099);

        for (String key : imageMap.keySet()) {
            if (query.contains(key)) {
                String image = imageMap.get(key);
                String name = key + "-container";
                Integer port = defaultPorts.get(key);

                Map<String, Integer> ports = new HashMap<>();
                if (port != null) {
                    ports.put(port + "/tcp", port);
                }

                Mono<String> creationResponse = mcpClient.createContainer(image, name, null, ports);
                return creationResponse
                        .map(res -> "✅ Created container `" + name + "` using image `" + image + "` on port `" + port
                                + "`.\nResponse: " + res)
                        .flux();
            }
        }

        return Flux.just(
                "⚠️ Sorry, I don't recognize which image to create. Please specify one like 'create an nginx container'.");
    }
}
