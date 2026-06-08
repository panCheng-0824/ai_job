package org.example.server_job.biz.support;

/**
 * 字典类型编码（BM）常量，与 {@code sys_code.BM} 一致。
 *
 * <p>业务表字段（如 {@code t_biz_jobs_info.gzszsf}）存的是 {@code DM}，
 * 翻译时需用本类 BM 查 {@code sys_code}，勿与表字段名混淆。
 */
public final class BizDictBm {

    /** 单位性质 → {@code t_biz_compary_info.dwxz} */
    public static final String DWXZ = "job_dwxz";
    /** 公司规模 → {@code t_biz_compary_info.gsgm} */
    public static final String GSGM = "job_gsgm";
    /** 职位类别 → {@code t_biz_jobs_info.zwlb} */
    public static final String ZWLB = "jpb_zwlb";
    /** 职业月薪 → {@code t_biz_jobs_info.yxjb} */
    public static final String YXJB = "job_yxjb";
    /** 性别 → {@code t_biz_jobs_info.xbyq} */
    public static final String XB = "job_xb";
    /** @deprecated 使用 {@link #XB} */
    @Deprecated
    public static final String XBYQ = XB;
    /** 中华人民共和国行政区划代码（省/市/区 DM 均在此 BM 下） */
    public static final String XZQH = "job_xzqh";
    /** 实习期 → {@code t_biz_jobs_info.sxq} */
    public static final String SXQ = "jpb_sxq";
    /** 学历代码 */
    public static final String XL = "job_xl";
    /** 工作类型 */
    public static final String GZLX = "job_gzlx";
    /** 行业类别 → {@code t_biz_compary_info.hylx}（varchar 存 DM） */
    public static final String HYLB = "job_hylb";
    /** 工作职位类别代码 */
    public static final String GZZWLB = "job_gzzwlb";
    /** 能力类型 */
    public static final String NL = "job_nl";
    /** 关键字 */
    public static final String GJZ = "job_gjz";
    /** 关键字分组 */
    public static final String GJZ_FZ = "job_gjz_fz";

    private BizDictBm() {
    }
}
