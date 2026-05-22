package org.example.server_job.ai.service.impl;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.service.OcrApiService;
import org.example.server_job.ai.service.support.BaseAiApiService;
import org.example.server_job.ai.support.AiResponseMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class OcrApiServiceImpl extends BaseAiApiService implements OcrApiService {

    private static final Logger log = LogManager.getLogger(OcrApiServiceImpl.class);

    private final AiJobGatewayService gatewayService;
    private final AiResponseMapper responseMapper;

    public OcrApiServiceImpl(AiJobGatewayService gatewayService, AiResponseMapper responseMapper) {
        this.gatewayService = gatewayService;
        this.responseMapper = responseMapper;
    }

    @Override
    public ResponseEntity<byte[]> recognizeByPath(String body) {
        log.info("OCR 路径识别请求开始, bodyLength={}", body == null ? 0 : body.length());
        return guard(() -> responseMapper.toResponseEntity(gatewayService.postJson("/ocr/recognize", body)));
    }

    @Override
    public ResponseEntity<byte[]> recognizeByUrl(String body) {
        log.info("OCR 链接识别请求开始, bodyLength={}", body == null ? 0 : body.length());
        return guard(() -> responseMapper.toResponseEntity(gatewayService.postJson("/ocr/recognize-url", body)));
    }

    @Override
    public ResponseEntity<byte[]> recognizeUpload(MultipartFile file, String lang, Boolean useAngleCls) {
        log.info("OCR 上传识别请求开始, filename={}, size={}, lang={}, useAngleCls={}",
                file == null ? "null" : file.getOriginalFilename(),
                file == null ? 0 : file.getSize(),
                lang,
                useAngleCls);
        return guard(() -> {
            String filename = file.getOriginalFilename() == null ? "upload.png" : file.getOriginalFilename();
            MediaType mediaType = MediaType.parse(file.getContentType() == null ? "application/octet-stream" : file.getContentType());
            MultipartBody multipartBody = new MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart(
                            "file",
                            filename,
                            RequestBody.create(file.getBytes(), mediaType)
                    )
                    .addFormDataPart("lang", lang == null ? "ch" : lang)
                    .addFormDataPart("use_angle_cls", String.valueOf(useAngleCls == null || useAngleCls))
                    .build();
            return responseMapper.toResponseEntity(gatewayService.postMultipart("/ocr/recognize-upload", multipartBody));
        });
    }
}
