package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.AuthApiService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class AuthController {

    private final AuthApiService authApiService;

    public AuthController(AuthApiService authApiService) {
        this.authApiService = authApiService;
    }

    @PostMapping("/login")
    public Map<String, Object> login(@RequestBody String body) {
        return authApiService.login(body);
    }
}
