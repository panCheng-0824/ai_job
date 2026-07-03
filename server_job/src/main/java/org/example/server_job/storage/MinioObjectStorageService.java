package org.example.server_job.storage;

import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ResponseStatusException;

import java.io.InputStream;
import java.util.Locale;
import java.util.UUID;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE;

/**
 * MinIO 对象存储：学生头像等静态资源。
 */
public class MinioObjectStorageService {

    private final MinioClient client;
    private final MinioProperties props;

    public MinioObjectStorageService(MinioClient client, MinioProperties props) {
        this.client = client;
        this.props = props;
    }

    public String uploadAvatar(String studentId, InputStream stream, long size, String contentType, String originalFilename) {
        if (!StringUtils.hasText(studentId)) {
            throw new ResponseStatusException(BAD_REQUEST, "student_id 不能为空");
        }
        if (size <= 0 || size > props.getAvatarMaxBytes()) {
            throw new ResponseStatusException(BAD_REQUEST, "头像大小需在 1B ~ 2MB 之间");
        }
        String ext = resolveImageExt(contentType, originalFilename);
        String objectKey = "avatars/" + studentId.trim() + "/" + System.currentTimeMillis() + "-"
                + UUID.randomUUID().toString().substring(0, 8) + ext;
        try {
            client.putObject(PutObjectArgs.builder()
                    .bucket(props.getBucket())
                    .object(objectKey)
                    .stream(stream, size, -1)
                    .contentType(contentType != null ? contentType : "application/octet-stream")
                    .build());
        } catch (Exception ex) {
            throw new ResponseStatusException(SERVICE_UNAVAILABLE, "头像上传失败: " + ex.getMessage());
        }
        return buildPublicUrl(objectKey);
    }

    public String buildPublicUrl(String objectKey) {
        String base = props.getPublicBaseUrl().trim();
        if (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        return base + "/" + props.getBucket() + "/" + objectKey;
    }

    private static String resolveImageExt(String contentType, String filename) {
        if (StringUtils.hasText(contentType)) {
            String ct = contentType.toLowerCase(Locale.ROOT);
            if (ct.contains("png")) return ".png";
            if (ct.contains("webp")) return ".webp";
            if (ct.contains("gif")) return ".gif";
            if (ct.contains("jpeg") || ct.contains("jpg")) return ".jpg";
        }
        if (StringUtils.hasText(filename) && filename.contains(".")) {
            String ext = filename.substring(filename.lastIndexOf('.')).toLowerCase(Locale.ROOT);
            if (ext.matches("\\.(png|jpe?g|webp|gif)")) {
                return ext.startsWith(".") ? ext : "." + ext;
            }
        }
        return ".jpg";
    }
}
