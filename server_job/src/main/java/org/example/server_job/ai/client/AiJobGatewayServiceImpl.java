package org.example.server_job.ai.client;

import okhttp3.HttpUrl;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.Map;

@Service
public class AiJobGatewayServiceImpl implements AiJobGatewayService {

    private static final MediaType JSON_MEDIA_TYPE = MediaType.get("application/json; charset=utf-8");
    private static final Logger log = LogManager.getLogger(AiJobGatewayServiceImpl.class);
    private final OkHttpClient okHttpClient;
    private final String aiJobBaseUrl;

    public AiJobGatewayServiceImpl(OkHttpClient okHttpClient, @Value("${ai-job.base-url}") String aiJobBaseUrl) {
        this.okHttpClient = okHttpClient;
        this.aiJobBaseUrl = aiJobBaseUrl;
    }

    @Override
    public AiJobHttpResponse get(String apiPath, Map<String, String> queryParams) throws IOException {
        String url = buildUrl(apiPath, queryParams);
        log.info("调用 ai_job GET 开始, path={}, queryParams={}, url={}", apiPath, queryParams, url);
        Request request = new Request.Builder()
                .url(url)
                .get()
                .build();
        return execute(request);
    }

    @Override
    public AiJobHttpResponse postJson(String apiPath, String jsonBody) throws IOException {
        String payload = jsonBody == null ? "{}" : jsonBody;
        String url = buildUrl(apiPath, Map.of());
        log.info("调用 ai_job POST(JSON) 开始, path={}, bodyLength={}, url={}", apiPath, payload.length(), url);
        RequestBody body = RequestBody.create(jsonBody == null ? "{}" : jsonBody, JSON_MEDIA_TYPE);
        Request request = new Request.Builder()
                .url(url)
                .post(body)
                .build();
        return execute(request);
    }

    @Override
    public AiJobHttpResponse delete(String apiPath) throws IOException {
        String url = buildUrl(apiPath, Map.of());
        log.info("调用 ai_job DELETE 开始, path={}, url={}", apiPath, url);
        Request request = new Request.Builder()
                .url(url)
                .delete()
                .build();
        return execute(request);
    }

    @Override
    public AiJobHttpResponse postMultipart(String apiPath, MultipartBody multipartBody) throws IOException {
        String url = buildUrl(apiPath, Map.of());
        log.info("调用 ai_job POST(Multipart) 开始, path={}, partCount={}, url={}",
                apiPath, multipartBody == null ? 0 : multipartBody.size(), url);
        Request request = new Request.Builder()
                .url(url)
                .post(multipartBody)
                .build();
        return execute(request);
    }

    @Override
    public Response streamGet(String apiPath, Map<String, String> queryParams) throws IOException {
        String url = buildUrl(apiPath, queryParams);
        log.info("调用 ai_job STREAM GET 开始, path={}, queryParams={}, url={}", apiPath, queryParams, url);
        long startNanos = System.nanoTime();
        Request request = new Request.Builder()
                .url(url)
                .get()
                .build();
        try {
            Response response = okHttpClient.newCall(request).execute();
            long elapsedMs = (System.nanoTime() - startNanos) / 1_000_000;
            log.info("调用 ai_job STREAM GET 完成, path={}, status={}, elapsedMs={}", apiPath, response.code(), elapsedMs);
            return response;
        } catch (IOException ex) {
            long elapsedMs = (System.nanoTime() - startNanos) / 1_000_000;
            log.error("调用 ai_job STREAM GET 失败, path={}, elapsedMs={}, reason={}", apiPath, elapsedMs, ex.getMessage(), ex);
            throw ex;
        }
    }

    @Override
    public Response streamPostJson(String apiPath, String jsonBody) throws IOException {
        String payload = jsonBody == null ? "{}" : jsonBody;
        String url = buildUrl(apiPath, Map.of());
        log.info("调用 ai_job STREAM POST(JSON) 开始, path={}, bodyLength={}, url={}", apiPath, payload.length(), url);
        long startNanos = System.nanoTime();
        RequestBody body = RequestBody.create(payload, JSON_MEDIA_TYPE);
        Request request = new Request.Builder()
                .url(url)
                .post(body)
                .build();
        try {
            Response response = okHttpClient.newCall(request).execute();
            long elapsedMs = (System.nanoTime() - startNanos) / 1_000_000;
            log.info("调用 ai_job STREAM POST(JSON) 连接建立, path={}, status={}, elapsedMs={}",
                    apiPath, response.code(), elapsedMs);
            return response;
        } catch (IOException ex) {
            long elapsedMs = (System.nanoTime() - startNanos) / 1_000_000;
            log.error("调用 ai_job STREAM POST(JSON) 失败, path={}, elapsedMs={}, reason={}",
                    apiPath, elapsedMs, ex.getMessage(), ex);
            throw ex;
        }
    }

    private AiJobHttpResponse execute(Request request) throws IOException {
        long startNanos = System.nanoTime();
        String method = request.method();
        String url = String.valueOf(request.url());
        try (Response response = okHttpClient.newCall(request).execute()) {
            byte[] body = response.body() == null ? new byte[0] : response.body().bytes();
            long elapsedMs = (System.nanoTime() - startNanos) / 1_000_000;
            log.info("调用 ai_job {} 完成, status={}, elapsedMs={}, bodyBytes={}, url={}",
                    method, response.code(), elapsedMs, body.length, url);
            return new AiJobHttpResponse(response.code(), response.headers().toMultimap(), body);
        } catch (IOException ex) {
            long elapsedMs = (System.nanoTime() - startNanos) / 1_000_000;
            log.error("调用 ai_job {} 失败, elapsedMs={}, reason={}, url={}", method, elapsedMs, ex.getMessage(), url, ex);
            throw ex;
        }
    }

    private String buildUrl(String apiPath, Map<String, String> queryParams) {
        String normalizedBase = aiJobBaseUrl.endsWith("/") ? aiJobBaseUrl.substring(0, aiJobBaseUrl.length() - 1) : aiJobBaseUrl;
        String normalizedPath = apiPath.startsWith("/") ? apiPath : "/" + apiPath;
        HttpUrl.Builder builder = HttpUrl.parse(normalizedBase + "/api" + normalizedPath).newBuilder();
        queryParams.forEach((k, v) -> {
            if (v != null) {
                builder.addQueryParameter(k, v);
            }
        });
        return builder.build().toString();
    }
}
