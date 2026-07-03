package org.example.server_job.storage;

import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.SetBucketPolicyArgs;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(MinioProperties.class)
public class MinioClientConfiguration {

    private static final Logger log = LogManager.getLogger(MinioClientConfiguration.class);

    @Bean
    @ConditionalOnProperty(prefix = "minio", name = "enabled", havingValue = "true", matchIfMissing = true)
    MinioClient minioClient(MinioProperties props) {
        MinioClient client = MinioClient.builder()
                .endpoint(props.getEndpoint().trim())
                .credentials(props.getAccessKey(), props.getSecretKey())
                .build();
        ensureBucket(client, props);
        return client;
    }

    private static void ensureBucket(MinioClient client, MinioProperties props) {
        String bucket = props.getBucket();
        try {
            boolean exists = client.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
            if (!exists) {
                client.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
                log.info("MinIO bucket 已创建: {}", bucket);
            }
            applyPublicReadPolicy(client, bucket);
        } catch (Exception ex) {
            log.warn("MinIO 初始化 bucket 失败（头像上传将不可用）: {}", ex.getMessage());
        }
    }

    /** avatars/* 允许匿名读，便于 img 标签直接引用 */
    private static void applyPublicReadPolicy(MinioClient client, String bucket) {
        String policy = """
                {
                  "Version": "2012-10-17",
                  "Statement": [
                    {
                      "Effect": "Allow",
                      "Principal": {"AWS": ["*"]},
                      "Action": ["s3:GetObject"],
                      "Resource": ["arn:aws:s3:::%s/avatars/*"]
                    }
                  ]
                }
                """.formatted(bucket);
        try {
            client.setBucketPolicy(SetBucketPolicyArgs.builder().bucket(bucket).config(policy).build());
        } catch (Exception ex) {
            log.debug("MinIO bucket policy 设置跳过: {}", ex.getMessage());
        }
    }

    @Bean
    @ConditionalOnProperty(prefix = "minio", name = "enabled", havingValue = "true", matchIfMissing = true)
    MinioObjectStorageService minioObjectStorageService(MinioClient minioClient, MinioProperties props) {
        return new MinioObjectStorageService(minioClient, props);
    }
}
