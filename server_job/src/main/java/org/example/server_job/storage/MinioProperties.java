package org.example.server_job.storage;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "minio")
public class MinioProperties {

    private boolean enabled = true;

    /** 如 http://127.0.0.1:9000 */
    private String endpoint = "http://127.0.0.1:9000";

    private String accessKey = "minioadmin";

    private String secretKey = "minioadmin";

    private String bucket = "job-portal";

    private String publicBaseUrl = "http://127.0.0.1:9000";

    private long avatarMaxBytes = 2 * 1024 * 1024;
}
