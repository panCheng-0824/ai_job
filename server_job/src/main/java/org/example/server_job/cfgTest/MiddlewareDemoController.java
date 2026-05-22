package org.example.server_job.cfgTest;

import org.example.server_job.cfgTest.service.MiddlewareDemoService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

@RestController
@RequestMapping("/demo")
public class MiddlewareDemoController {

    private final Map<String, MiddlewareDemoService> demoServiceMap;

    public MiddlewareDemoController(List<MiddlewareDemoService> demoServices) {
        this.demoServiceMap = new LinkedHashMap<>();
        for (MiddlewareDemoService service : demoServices) {
            this.demoServiceMap.put(service.middleware(), service);
        }
    }

    @GetMapping("/all")
    public Map<String, Object> all() {
        Map<String, Object> result = new LinkedHashMap<>();
        for (Map.Entry<String, MiddlewareDemoService> entry : demoServiceMap.entrySet()) {
            result.put(entry.getKey(), execute(entry.getValue()::runDemo));
        }
        return result;
    }

    @GetMapping("/{middleware}")
    public Map<String, Object> runSingle(@PathVariable String middleware) {
        MiddlewareDemoService service = demoServiceMap.get(middleware);
        if (service == null) {
            return DemoResult.error("unsupported middleware: " + middleware);
        }
        return service.runDemo();
    }

    private Map<String, Object> execute(Supplier<Map<String, Object>> supplier) {
        try {
            return supplier.get();
        } catch (Exception e) {
            return DemoResult.error(e.getMessage());
        }
    }
}
