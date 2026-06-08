package org.example.server_job.ai.service;

import org.example.server_job.biz.vo.BizCompanyApiVO;
import org.example.server_job.biz.vo.BizJobApiVO;

import java.util.List;
import java.util.Map;

public interface DataApiService {
    Map<String, Object> getStudent(String studentId);

    List<BizCompanyApiVO> listCompanies();

    /**
     * 企业分页；{@code keyword} 非空时在公司名、WID、行业、地址等字段上做模糊匹配。
     */
    Map<String, Object> listCompaniesPaged(Integer page, Integer pageSize, String keyword);

    BizCompanyApiVO getCompany(String creditCode);

    /** 企业详情页底部 JSON 预览（字典翻译后的结构化展示）。 */
    Map<String, Object> previewCompanyDetail(String creditCode);

    List<BizJobApiVO> listJobs();

    /**
     * 岗位分页；{@code keyword} 非空时在职位名、用人单位、工作地点等字段上做模糊匹配。
     *
     * @param syncedOnly  为 true 时仅返回已同步知识库（synRag = "1"）的岗位
     * @param companyType 可选；字典 {@code job_dwxz} 的 DM，按企业单位性质筛选
     * @param industry    可选；字典 {@code job_hylb} 的 DM，按企业行业筛选
     */
    Map<String, Object> listJobsPaged(
            Integer page,
            Integer pageSize,
            String keyword,
            Boolean syncedOnly,
            String companyType,
            String industry
    );

    /**
     * 岗位列表筛选维度：公司类型（单位性质）与行业，含各选项岗位总数与已同步数。
     */
    Map<String, Object> jobFilterFacets(String keyword);

    BizJobApiVO getJob(String jobId);

    /**
     * 按用人单位组织机构代码（{@code yrdw} / {@code zzjgdm}）查关联岗位，供详情页「同企业岗位」区块。
     *
     * @param excludeJobId 可选；岗位详情页排除当前岗位
     */
    List<BizJobApiVO> listJobsByCompany(String yrdw, String excludeJobId, Integer limit);

    Map<String, Object> search(String keyword, String scope, Integer limit);
}
