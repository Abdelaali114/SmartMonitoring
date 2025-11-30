package com.example.Openstack_ai_agent.config;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class LLMConfig {

    @Bean
    public ChatClient chatClient (ChatClient.Builder builder) {
        return builder.build();
    }
}

