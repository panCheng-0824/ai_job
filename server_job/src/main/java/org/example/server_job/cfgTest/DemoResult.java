package org.example.server_job.cfgTest;

import java.util.LinkedHashMap;
import java.util.Map;

public final class DemoResult {

    private DemoResult() {
    }

    public static Map<String, Object> ok(Map<String, Object> data) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        result.putAll(data);
        return result;
    }

    public static Map<String, Object> error(String message) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "error");
        result.put("error", message);
        return result;
    }
}
