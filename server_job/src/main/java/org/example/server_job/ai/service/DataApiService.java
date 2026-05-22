package org.example.server_job.ai.service;

import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;

import java.util.List;
import java.util.Map;

public interface DataApiService {
    Map<String, Object> getStudent(String studentId);

    List<BizCompanyInfo> listCompanies();

    /**
     * 企业分页；{@code keyword} 非空时在企业名、统一社会信用代码（id）、行业（area）上做模糊匹配。
     */
    Map<String, Object> listCompaniesPaged(Integer page, Integer pageSize, String keyword);

    BizCompanyInfo getCompany(String creditCode);

    List<BizJobsInfo> listJobs();

    /**
     * 岗位分页；{@code keyword} 非空时在岗位名、企业名、地址、地区上做模糊匹配（与门户列表筛选字段一致）。
     *
     * @param syncedOnly 为 true 时仅返回已同步知识库（synRag = "1"）的岗位
     */
    Map<String, Object> listJobsPaged(Integer page, Integer pageSize, String keyword, Boolean syncedOnly);

    BizJobsInfo getJob(String jobId);

    Map<String, Object> search(String keyword, String scope, Integer limit);
}
