package org.example.server_job.biz.dto;

/**
 * 字典项新增/修改请求体。
 *
 * @param id   主键，修改时必填
 * @param fid  父级 id（省市区等级联）
 * @param name 字典文本
 * @param dm   字典编码
 * @param mc   类型名称
 * @param bm   类型编码
 * @param lbmc 类别名称（可选）
 */
public record SysCodeSaveRequest(
        String id,
        String fid,
        String name,
        Integer dm,
        String mc,
        String bm,
        String lbmc
) {
}
