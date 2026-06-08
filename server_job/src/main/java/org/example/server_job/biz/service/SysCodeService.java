package org.example.server_job.biz.service;

import org.example.server_job.biz.dto.SysCodeSaveRequest;

import java.util.Map;

/**
 * 系统字典维护与查询服务。
 */
public interface SysCodeService {

    /**
     * 列出全部字典类型（BM）元信息，优先读 Redis。
     */
    Map<String, Object> listTypes();

    /**
     * 按类型编码查询字典项，支持树形组装。
     *
     * @param bm   类型编码，必填
     * @param tree 是否按 FID 组装树
     */
    Map<String, Object> listByBm(String bm, boolean tree);

    /**
     * 按 BM + DM 翻译字典名称，优先读 Redis。
     */
    Map<String, Object> lookup(String bm, Integer dm);

    Map<String, Object> getDetail(String id);

    Map<String, Object> create(SysCodeSaveRequest request);

    Map<String, Object> update(String id, SysCodeSaveRequest request);

    Map<String, Object> delete(String id);
}
