package org.example.server_job.biz.support;

/**
 * 系统字典 Redis 键规范。
 *
 * <p>桶结构：
 * <ul>
 *   <li>{@link #ALL_TYPES} — 全部类型编码（BM）元信息列表</li>
 *   <li>{@code sys_code:bucket:{bm}} — 某类型下全部字典项（扁平列表）</li>
 *   <li>{@code sys_code:lookup:{bm}} — DM → NAME 快速翻译映射</li>
 *   <li>{@code sys_code:lookup_id:{bm}} — ID → NAME 快速翻译映射</li>
 * </ul>
 */
public final class SysCodeRedisKeys {

    private static final String PREFIX = "sys_code:";

    /** 全部字典类型（BM）汇总桶 */
    public static final String ALL_TYPES = PREFIX + "all_types";

    private SysCodeRedisKeys() {
    }

    /** 某 BM 下的字典项列表桶 */
    public static String bucket(String bm) {
        return PREFIX + "bucket:" + normalizeBm(bm);
    }

    /** 某 BM 下 DM → NAME 翻译映射桶 */
    public static String lookup(String bm) {
        return PREFIX + "lookup:" + normalizeBm(bm);
    }

    /** 某 BM 下 ID → NAME 翻译映射桶 */
    public static String lookupById(String bm) {
        return PREFIX + "lookup_id:" + normalizeBm(bm);
    }

    private static String normalizeBm(String bm) {
        if (bm == null || bm.isBlank()) {
            return "_";
        }
        return bm.trim();
    }
}
