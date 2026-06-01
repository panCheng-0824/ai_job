package org.example.server_job.interview.support;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

/**
 * 服务间鉴权：ai_job 调用 {@code /internal/interview/*} 时携带 X-Service-Token。
 */
@Component
public class InterviewServiceTokenVerifier {

    private final String serviceToken;

    public InterviewServiceTokenVerifier(@Value("${interview.service-token:}") String serviceToken) {
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    /**
     * 校验 Token；未配置 interview.service-token 时跳过（仅建议本地开发）。
     */
    public void verify(String token) {
        if (serviceToken.isEmpty()) {
            return;
        }
        if (token == null || !serviceToken.equals(token.trim())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "无效的服务间 Token");
        }
    }
}
