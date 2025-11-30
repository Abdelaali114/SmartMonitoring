package com.example.Openstack_ai_agent.Controller;

import com.example.Openstack_ai_agent.AgentAI.Aiagent;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

@RestController
@CrossOrigin("*")
public class AgentController {
    private Aiagent agent ;
    private ChatClient chatClient ;


    public AgentController(Aiagent agent , ChatClient chatClient  ){
        this.agent = agent;
        this.chatClient = chatClient;
    }


    @GetMapping(value = "/AskAgent" , produces = MediaType.TEXT_PLAIN_VALUE)
    public Flux<String> chat(String query){
        return agent.onQuery(query);
    }

}
