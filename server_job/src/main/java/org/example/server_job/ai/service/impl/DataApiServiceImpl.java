package org.example.server_job.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.service.DataApiService;
import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizCompanyInfoService;
import org.example.server_job.biz.service.BizJobsInfoService;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.biz.support.StudentPortraitChineseJsonTranslator;
import org.example.server_job.biz.vo.BizStudentPortraitVO;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
public class DataApiServiceImpl implements DataApiService {

    private static final Logger log = LogManager.getLogger(DataApiServiceImpl.class);

    private final BizStudentInfoService bizStudentInfoService;
    private final BizCompanyInfoService bizCompanyInfoService;
    private final BizJobsInfoService bizJobsInfoService;
    private final ObjectMapper objectMapper;

    public DataApiServiceImpl(
            BizStudentInfoService bizStudentInfoService,
            BizCompanyInfoService bizCompanyInfoService,
            BizJobsInfoService bizJobsInfoService,
            ObjectMapper objectMapper
    ) {
        this.bizStudentInfoService = bizStudentInfoService;
        this.bizCompanyInfoService = bizCompanyInfoService;
        this.bizJobsInfoService = bizJobsInfoService;
        this.objectMapper = objectMapper;
    }

    @Override
    public Map<String, Object> getStudent(String studentId) {
        log.info("查询学生画像开始, studentId={}", studentId);
        Integer xh = parseXh(studentId);
        BizStudentPortraitVO portrait = bizStudentInfoService.getStudentPortraitByXh(xh);
        if (portrait.getStudentInfo() == null) {
            log.warn("查询学生画像失败, 原因=学生不存在, studentId={}, normalizedXh={}", studentId, xh);
            throw new ResponseStatusException(NOT_FOUND, "学生不存在");
        }
        log.info("查询学生画像成功, studentId={}, normalizedXh={}, name={}",
                studentId, xh, portrait.getStudentInfo().getXm());
        var tree = StudentPortraitChineseJsonTranslator.toFullPortraitChineseTree(objectMapper, portrait);
        return objectMapper.convertValue(tree, new TypeReference<>() {
        });
    }

    @Override
    public List<BizCompanyInfo> listCompanies() {
        log.info("查询企业列表开始");
        List<BizCompanyInfo> companies = bizCompanyInfoService.list();
        log.info("查询企业列表成功, count={}", companies.size());
        return companies;
    }

    @Override
    public Map<String, Object> listCompaniesPaged(Integer page, Integer pageSize, String keyword) {
        int safePage = Math.max(1, Objects.requireNonNullElse(page, 1));
        int safePageSize = Math.max(1, Math.min(Objects.requireNonNullElse(pageSize, 20), 100));
        String q = keyword == null ? "" : keyword.trim();

        LambdaQueryWrapper<BizCompanyInfo> wrapper = new LambdaQueryWrapper<>();
        if (!q.isEmpty()) {
            wrapper.and(w -> w
                    .like(BizCompanyInfo::getCompanyName, q)
                    .or().like(BizCompanyInfo::getId, q)
                    .or().like(BizCompanyInfo::getArea, q)
                    .or().like(BizCompanyInfo::getAddress, q)
                    .or().like(BizCompanyInfo::getCompanyType, q));
        }

        Page<BizCompanyInfo> mpPage = new Page<>(safePage, safePageSize);
        Page<BizCompanyInfo> result = bizCompanyInfoService.page(mpPage, wrapper);
        long total = result.getTotal();
        List<BizCompanyInfo> companies = result.getRecords();
        boolean hasMore = (long) safePage * safePageSize < total;

        Map<String, Long> jobCountByCompanyId = jobCountsForCompanyIds(
                companies.stream().map(BizCompanyInfo::getId).filter(Objects::nonNull).toList()
        );

        List<Map<String, Object>> items = new ArrayList<>();
        for (BizCompanyInfo company : companies) {
            Map<String, Object> item = new HashMap<>();
            item.put("id", company.getId());
            item.put("companyName", company.getCompanyName());
            item.put("companySize", company.getCompanySize());
            item.put("companyType", company.getCompanyType());
            item.put("area", company.getArea());
            item.put("address", company.getAddress());
            item.put("website", company.getWebsite());
            item.put("jobCount", jobCountByCompanyId.getOrDefault(company.getId(), 0L));
            items.add(item);
        }

        Map<String, Object> map = new HashMap<>();
        map.put("page", safePage);
        map.put("pageSize", safePageSize);
        map.put("total", total);
        map.put("hasMore", hasMore);
        map.put("items", items);
        map.put("keyword", q);
        log.info("分页查询企业成功, page={}, pageSize={}, keywordBlank={}, total={}, itemsCount={}, hasMore={}",
                safePage, safePageSize, q.isEmpty(), total, items.size(), hasMore);
        return map;
    }

    /** 当前页企业 id 列表对应的在招岗位数（按 companyId 聚合）。 */
    private Map<String, Long> jobCountsForCompanyIds(List<String> companyIds) {
        Map<String, Long> counts = new HashMap<>();
        if (companyIds == null || companyIds.isEmpty()) {
            return counts;
        }
        QueryWrapper<BizJobsInfo> qw = new QueryWrapper<>();
        qw.select("companyId", "COUNT(*) AS cnt");
        qw.in("companyId", companyIds);
        qw.groupBy("companyId");
        List<Map<String, Object>> rows = bizJobsInfoService.listMaps(qw);
        for (Map<String, Object> row : rows) {
            Object cid = row.get("companyId");
            if (cid == null) {
                cid = row.get("companyid");
            }
            if (cid == null) {
                continue;
            }
            Object cnt = row.get("cnt");
            if (cnt == null) {
                cnt = row.get("CNT");
            }
            long n = 0L;
            if (cnt instanceof Number) {
                n = ((Number) cnt).longValue();
            } else if (cnt != null) {
                try {
                    n = Long.parseLong(String.valueOf(cnt));
                } catch (NumberFormatException ignored) {
                    n = 0L;
                }
            }
            counts.put(String.valueOf(cid), n);
        }
        return counts;
    }

    @Override
    public BizCompanyInfo getCompany(String creditCode) {
        log.info("查询企业详情开始, creditCode={}", creditCode);
        BizCompanyInfo company = bizCompanyInfoService.getById(creditCode);
        if (company == null) {
            log.warn("查询企业详情失败, 原因=企业不存在, creditCode={}", creditCode);
            throw new ResponseStatusException(NOT_FOUND, "企业不存在");
        }
        log.info("查询企业详情成功, creditCode={}, companyName={}", creditCode, company.getCompanyName());
        return company;
    }

    @Override
    public List<BizJobsInfo> listJobs() {
        log.info("查询岗位列表开始");
        List<BizJobsInfo> jobs = bizJobsInfoService.list();
        log.info("查询岗位列表成功, count={}", jobs.size());
        return jobs;
    }

    @Override
    public Map<String, Object> listJobsPaged(Integer page, Integer pageSize, String keyword, Boolean syncedOnly) {
        int safePage = Math.max(1, Objects.requireNonNullElse(page, 1));
        int safePageSize = Math.max(1, Math.min(Objects.requireNonNullElse(pageSize, 20), 100));
        String q = keyword == null ? "" : keyword.trim();
        boolean onlySynced = syncedOnly == null || Boolean.TRUE.equals(syncedOnly);

        LambdaQueryWrapper<BizJobsInfo> wrapper = new LambdaQueryWrapper<>();
        if (onlySynced) {
            wrapper.eq(BizJobsInfo::getSynRag, "1");
        }
        if (!q.isEmpty()) {
            wrapper.and(w -> w
                    .like(BizJobsInfo::getJobName, q)
                    .or().like(BizJobsInfo::getCompanyName, q)
                    .or().like(BizJobsInfo::getAddress, q)
                    .or().like(BizJobsInfo::getArea, q));
        }

        Page<BizJobsInfo> mpPage = new Page<>(safePage, safePageSize);
        Page<BizJobsInfo> result = bizJobsInfoService.page(mpPage, wrapper);
        long total = result.getTotal();
        List<BizJobsInfo> items = result.getRecords();
        boolean hasMore = (long) safePage * safePageSize < total;

        Map<String, Object> map = new HashMap<>();
        map.put("page", safePage);
        map.put("pageSize", safePageSize);
        map.put("total", total);
        map.put("hasMore", hasMore);
        map.put("items", items);
        map.put("keyword", q);
        map.put("syncedOnly", onlySynced);
        log.info("分页查询岗位成功, page={}, pageSize={}, keywordBlank={}, syncedOnly={}, total={}, itemsCount={}, hasMore={}",
                safePage, safePageSize, q.isEmpty(), onlySynced, total, items.size(), hasMore);
        return map;
    }

    @Override
    public BizJobsInfo getJob(String jobId) {
        log.info("查询岗位详情开始, jobId={}", jobId);
        BizJobsInfo job = bizJobsInfoService.getById(jobId);
        if (job == null) {
            log.warn("查询岗位详情失败, 原因=岗位不存在, jobId={}", jobId);
            throw new ResponseStatusException(NOT_FOUND, "岗位不存在");
        }
        log.info("查询岗位详情成功, jobId={}, jobName={}, companyName={}",
                jobId, job.getJobName(), job.getCompanyName());
        return job;
    }

    @Override
    public Map<String, Object> search(String keyword, String scope, Integer limit) {
        String q = keyword == null ? "" : keyword.trim();
        if (q.isEmpty()) {
            log.warn("搜索参数校验失败, 原因=keyword 为空");
            throw new ResponseStatusException(BAD_REQUEST, "keyword 不能为空");
        }
        int safeLimit = Math.max(1, Math.min(Objects.requireNonNullElse(limit, 20), 100));
        String normalizedScope = (scope == null ? "all" : scope.trim().toLowerCase(Locale.ROOT));
        log.info("搜索请求开始, keyword={}, scope={}, normalizedScope={}, limit={}, safeLimit={}",
                keyword, scope, normalizedScope, limit, safeLimit);
        if (!List.of("all", "student", "job", "company").contains(normalizedScope)) {
            log.warn("搜索参数校验失败, 原因=scope 非法, scope={}, normalizedScope={}", scope, normalizedScope);
            throw new ResponseStatusException(BAD_REQUEST, "scope 仅支持: all, company, job, student");
        }

        Map<String, Object> result = new HashMap<>();
        result.put("keyword", q);
        result.put("scope", normalizedScope);

        List<Map<String, Object>> students = new ArrayList<>();
        List<Map<String, Object>> jobs = new ArrayList<>();
        List<Map<String, Object>> companies = new ArrayList<>();

        if ("all".equals(normalizedScope) || "student".equals(normalizedScope)) {
            List<BizStudentInfo> studentRows = bizStudentInfoService.list(new LambdaQueryWrapper<BizStudentInfo>()
                    .like(BizStudentInfo::getXm, q)
                    .or().like(BizStudentInfo::getZymc, q)
                    .or().like(BizStudentInfo::getXh, q)
                    .last("limit " + safeLimit));
            for (BizStudentInfo student : studentRows) {
                Map<String, Object> item = new HashMap<>();
                item.put("student_id", student.getXh());
                item.put("name", student.getXm());
                item.put("major", student.getZymc());
                students.add(item);
            }
        }

        if ("all".equals(normalizedScope) || "job".equals(normalizedScope)) {
            List<BizJobsInfo> jobRows = bizJobsInfoService.list(new LambdaQueryWrapper<BizJobsInfo>()
                    .like(BizJobsInfo::getJobName, q)
                    .or().like(BizJobsInfo::getCompanyName, q)
                    .or().like(BizJobsInfo::getArea, q)
                    .last("limit " + safeLimit));
            for (BizJobsInfo job : jobRows) {
                Map<String, Object> item = new HashMap<>();
                item.put("job_id", job.getId());
                item.put("job_title", job.getJobName());
                item.put("city", job.getAddress());
                item.put("district", job.getArea());
                item.put("company_name", job.getCompanyName());
                item.put("credit_code", job.getCompanyId());
                jobs.add(item);
            }
        }

        if ("all".equals(normalizedScope) || "company".equals(normalizedScope)) {
            List<BizCompanyInfo> companyRows = bizCompanyInfoService.list(new LambdaQueryWrapper<BizCompanyInfo>()
                    .like(BizCompanyInfo::getId, q)
                    .or().like(BizCompanyInfo::getCompanyName, q)
                    .or().like(BizCompanyInfo::getArea, q)
                    .last("limit " + safeLimit));
            for (BizCompanyInfo company : companyRows) {
                Map<String, Object> item = new HashMap<>();
                item.put("credit_code", company.getId());
                item.put("company_name", company.getCompanyName());
                item.put("industry", company.getArea());
                companies.add(item);
            }
        }

        result.put("students", students);
        result.put("jobs", jobs);
        result.put("companies", companies);
        result.put("total", students.size() + jobs.size() + companies.size());
        log.info("搜索请求成功, normalizedScope={}, students={}, jobs={}, companies={}, total={}",
                normalizedScope, students.size(), jobs.size(), companies.size(), result.get("total"));
        return result;
    }

    private Integer parseXh(String studentId) {
        String cleaned = studentId == null ? "" : studentId.trim();
        if (cleaned.isEmpty()) {
            throw new ResponseStatusException(BAD_REQUEST, "student_id 不能为空");
        }
        try {
            return Integer.valueOf(cleaned);
        } catch (NumberFormatException ex) {
            throw new ResponseStatusException(BAD_REQUEST, "student_id 必须为数字学号");
        }
    }
}
