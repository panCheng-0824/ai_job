package org.example.server_job.ai.client;

import okhttp3.MultipartBody;
import okhttp3.Response;

import java.io.IOException;
import java.util.Map;

public interface AiJobGatewayService {

    AiJobHttpResponse get(String apiPath, Map<String, String> queryParams) throws IOException;

    AiJobHttpResponse postJson(String apiPath, String jsonBody) throws IOException;

    AiJobHttpResponse delete(String apiPath) throws IOException;

    AiJobHttpResponse postMultipart(String apiPath, MultipartBody multipartBody) throws IOException;

    Response streamGet(String apiPath, Map<String, String> queryParams) throws IOException;

    /** POST JSON 并保持响应体为流（例如 SSE），调用方负责关闭 {@link Response}。 */
    Response streamPostJson(String apiPath, String jsonBody) throws IOException;
}
