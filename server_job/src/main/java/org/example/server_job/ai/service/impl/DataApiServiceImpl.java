package org.example.server_job.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.service.DataApiService;
import org.example.server_job.biz.dto.JobFacetCountRow;
import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.entity.BizJobsRagSync;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.mapper.BizJobsInfoMapper;
import org.example.server_job.biz.service.BizCompanyInfoService;
import org.example.server_job.biz.service.BizJobsInfoService;
import org.example.server_job.biz.service.BizJobsRagSyncService;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.biz.support.BizCompanyApiTranslator;
import org.example.server_job.biz.support.BizDetailPreviewBuilder;
import org.example.server_job.biz.support.BizDictBm;
import org.example.server_job.biz.support.BizDictLabelSupport;
import org.example.server_job.biz.support.BizJobApiTranslator;
import org.example.server_job.biz.support.BizJobListScopeSupport;
import org.example.server_job.biz.support.StudentPortraitChineseJsonTranslator;
import org.example.server_job.biz.support.SysCodeRedisCache;
import org.example.server_job.biz.vo.BizCompanyApiVO;
import org.example.server_job.biz.vo.BizJobApiVO;
import org.example.server_job.biz.vo.BizStudentPortraitVO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
public class DataApiServiceImpl implements DataApiService {

    private static final Logger log = LogManager.getLogger(DataApiServiceImpl.class);

    private final BizStudentInfoService bizStudentInfoService;
    private final BizCompanyInfoService bizCompanyInfoService;
    private final BizJobsInfoService bizJobsInfoService;
    private final BizJobsInfoMapper bizJobsInfoMapper;
    private final BizJobsRagSyncService bizJobsRagSyncService;
    private final BizDictLabelSupport dictLabelSupport;
    private final BizJobListScopeSupport bizJobListScopeSupport;
    private final SysCodeRedisCache sysCodeRedisCache;
    private final BizDetailPreviewBuilder detailPreviewBuilder;
    private final ObjectMapper objectMapper;

    @Value("${ai-job.rag.source:server_job}")
    private String ragSource;

    public DataApiServiceImpl(
            BizStudentInfoService bizStudentInfoService,
            BizCompanyInfoService bizCompanyInfoService,
            BizJobsInfoService bizJobsInfoService,
            BizJobsInfoMapper bizJobsInfoMapper,
            BizJobsRagSyncService bizJobsRagSyncService,
            BizDictLabelSupport dictLabelSupport,
            BizJobListScopeSupport bizJobListScopeSupport,
            SysCodeRedisCache sysCodeRedisCache,
            BizDetailPreviewBuilder detailPreviewBuilder,
            ObjectMapper objectMapper
    ) {
        this.bizStudentInfoService = bizStudentInfoService;
        this.bizCompanyInfoService = bizCompanyInfoService;
        this.bizJobsInfoService = bizJobsInfoService;
        this.bizJobsInfoMapper = bizJobsInfoMapper;
        this.bizJobsRagSyncService = bizJobsRagSyncService;
        this.dictLabelSupport = dictLabelSupport;
        this.bizJobListScopeSupport = bizJobListScopeSupport;
        this.sysCodeRedisCache = sysCodeRedisCache;
        this.detailPreviewBuilder = detailPreviewBuilder;
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
    public List<BizCompanyApiVO> listCompanies() {
        log.info("查询企业列表开始");
        List<BizCompanyApiVO> companies = bizCompanyInfoService.list().stream()
                .map(c -> BizCompanyApiTranslator.toVo(c, dictLabelSupport))
                .toList();
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
                    .like(BizCompanyInfo::getGsmc, q)
                    .or().like(BizCompanyInfo::getWid, q)
                    .or().like(BizCompanyInfo::getHylx, q)
                    .or().like(BizCompanyInfo::getDwbgdz, q)
                    .or().like(BizCompanyInfo::getDwjj, q));
        }

        Page<BizCompanyInfo> mpPage = new Page<>(safePage, safePageSize);
        Page<BizCompanyInfo> result = bizCompanyInfoService.page(mpPage, wrapper);
        long total = result.getTotal();
        List<BizCompanyInfo> companies = result.getRecords();
        boolean hasMore = (long) safePage * safePageSize < total;

        Map<String, Long> jobCountByZzjgdm = jobCountsForZzjgdm(
                companies.stream()
                        .map(BizCompanyInfo::getZzjgdm)
                        .filter(Objects::nonNull)
                        .map(String::trim)
                        .filter(s -> !s.isEmpty())
                        .toList()
        );

        List<Map<String, Object>> items = new ArrayList<>();
        for (BizCompanyInfo company : companies) {
            BizCompanyApiVO vo = BizCompanyApiTranslator.toVo(company, dictLabelSupport);
            Map<String, Object> item = new HashMap<>();
            item.put("id", vo.getId());
            item.put("companyName", vo.getCompanyName());
            item.put("companySize", vo.getCompanySize());
            item.put("companyType", vo.getCompanyType());
            item.put("area", vo.getArea());
            item.put("address", vo.getAddress());
            item.put("website", vo.getWebsite());
            String zzjgdm = company.getZzjgdm() == null ? "" : company.getZzjgdm().trim();
            item.put("jobCount", zzjgdm.isEmpty() ? 0L : jobCountByZzjgdm.getOrDefault(zzjgdm, 0L));
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

    /** 组织机构代码列表对应的在招岗位数（{@code t_biz_jobs_info.yrdw} = {@code zzjgdm}）。 */
    private Map<String, Long> jobCountsForZzjgdm(List<String> zzjgdmList) {
        Map<String, Long> counts = new HashMap<>();
        if (zzjgdmList == null || zzjgdmList.isEmpty()) {
            return counts;
        }
        QueryWrapper<BizJobsInfo> qw = new QueryWrapper<>();
        qw.select("yrdw", "COUNT(*) AS cnt");
        qw.in("yrdw", zzjgdmList);
        qw.groupBy("yrdw");
        List<Map<String, Object>> rows = bizJobsInfoService.listMaps(qw);
        for (Map<String, Object> row : rows) {
            Object cid = row.get("yrdw");
            if (cid == null) {
                cid = row.get("YRDW");
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
    public BizCompanyApiVO getCompany(String creditCode) {
        log.info("查询企业详情开始, creditCode={}", creditCode);
        BizCompanyInfo company = bizCompanyInfoService.getByIdOrZzjgdm(creditCode);
        if (company == null) {
            log.warn("查询企业详情失败, 原因=企业不存在, creditCode={}", creditCode);
            throw new ResponseStatusException(NOT_FOUND, "企业不存在");
        }
        log.info("查询企业详情成功, creditCode={}, wid={}, zzjgdm={}, companyName={}",
                creditCode, company.getWid(), company.getZzjgdm(), company.getGsmc());
        return BizCompanyApiTranslator.toVo(company, dictLabelSupport);
    }

    @Override
    public Map<String, Object> previewCompanyDetail(String creditCode) {
        log.info("查询企业详情预览开始, creditCode={}", creditCode);
        BizCompanyInfo company = bizCompanyInfoService.getByIdOrZzjgdm(creditCode);
        if (company == null) {
            log.warn("查询企业详情预览失败, 原因=企业不存在, creditCode={}", creditCode);
            throw new ResponseStatusException(NOT_FOUND, "企业不存在");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("展示数据", detailPreviewBuilder.buildCompanyPreview(company));
        List<BizJobsInfo> jobs = listJobEntitiesByCompany(company.getZzjgdm(), 100);
        Set<String> jobIds = jobs.stream()
                .map(BizJobsInfo::getJobid)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<String, BizJobsRagSync> ragMap = bizJobsRagSyncService.mapByJobIds(jobIds);
        result.put("RAG打包预览", detailPreviewBuilder.buildCompanyRagPackPreview(company, jobs, ragMap, ragSource));
        result.put("companyId", company.getWid());
        result.put("zzjgdm", company.getZzjgdm());
        result.put("companyName", company.getGsmc());
        result.put("关联岗位数", jobs.size());
        log.info("查询企业详情预览成功, creditCode={}, companyName={}, jobCount={}",
                creditCode, company.getGsmc(), jobs.size());
        return result;
    }

    private List<BizJobsInfo> listJobEntitiesByCompany(String yrdw, int limit) {
        String code = yrdw == null ? "" : yrdw.trim();
        if (code.isEmpty()) {
            return List.of();
        }
        int safeLimit = Math.max(1, Math.min(limit, 200));
        LambdaQueryWrapper<BizJobsInfo> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(BizJobsInfo::getYrdw, code);
        wrapper.last("LIMIT " + safeLimit);
        return bizJobsInfoService.list(wrapper);
    }

    @Override
    public List<BizJobApiVO> listJobs() {
        log.info("查询岗位列表开始");
        List<BizJobsInfo> jobs = bizJobsInfoService.list();
        List<BizJobApiVO> vos = toJobVoList(jobs);
        log.info("查询岗位列表成功, count={}", vos.size());
        return vos;
    }

    @Override
    public Map<String, Object> listJobsPaged(
            Integer page,
            Integer pageSize,
            String keyword,
            Boolean syncedOnly,
            String companyType,
            String industry
    ) {
        int safePage = Math.max(1, Objects.requireNonNullElse(page, 1));
        int safePageSize = Math.max(1, Math.min(Objects.requireNonNullElse(pageSize, 20), 100));
        String q = keyword == null ? "" : keyword.trim();
        boolean onlySynced = syncedOnly == null || Boolean.TRUE.equals(syncedOnly);
        String companyTypeCode = companyType == null ? "" : companyType.trim();
        String industryCode = industry == null ? "" : industry.trim();

        LambdaQueryWrapper<BizJobsInfo> wrapper = new LambdaQueryWrapper<>();
        if (onlySynced) {
            wrapper.inSql(BizJobsInfo::getJobid,
                    "SELECT jobid FROM t_biz_jobs_rag_sync WHERE syn_rag = 1");
        }
        bizJobListScopeSupport.applyListScope(wrapper, q, companyTypeCode, industryCode);

        Page<BizJobsInfo> mpPage = new Page<>(safePage, safePageSize);
        Page<BizJobsInfo> result = bizJobsInfoService.page(mpPage, wrapper);
        long total = result.getTotal();
        List<BizJobApiVO> items = toJobVoList(result.getRecords());
        boolean hasMore = (long) safePage * safePageSize < total;

        Map<String, Object> map = new HashMap<>();
        map.put("page", safePage);
        map.put("pageSize", safePageSize);
        map.put("total", total);
        map.put("hasMore", hasMore);
        map.put("items", items);
        map.put("keyword", q);
        map.put("syncedOnly", onlySynced);
        map.put("companyType", companyTypeCode);
        map.put("industry", industryCode);
        log.info("分页查询岗位成功, page={}, pageSize={}, keywordBlank={}, syncedOnly={}, companyType={}, industry={}, total={}, itemsCount={}, hasMore={}",
                safePage, safePageSize, q.isEmpty(), onlySynced, companyTypeCode, industryCode, total, items.size(), hasMore);
        return map;
    }

    @Override
    public Map<String, Object> jobFilterFacets(String keyword) {
        String q = keyword == null ? "" : keyword.trim();
        List<Map<String, Object>> companyTypes = buildCompanyTypeFacets(q);
        List<Map<String, Object>> industries = buildIndustryFacets(q);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("keyword", q);
        out.put("companyTypes", companyTypes);
        out.put("industries", industries);
        log.info("岗位筛选维度统计成功, keywordBlank={}, companyTypes={}, industries={}",
                q.isEmpty(), companyTypes.size(), industries.size());
        return out;
    }

    @Override
    public BizJobApiVO getJob(String jobId) {
        log.info("查询岗位详情开始, jobId={}", jobId);
        BizJobsInfo job = bizJobsInfoService.getById(jobId);
        if (job == null) {
            log.warn("查询岗位详情失败, 原因=岗位不存在, jobId={}", jobId);
            throw new ResponseStatusException(NOT_FOUND, "岗位不存在");
        }
        BizJobApiVO vo = toJobVo(job);
        log.info("查询岗位详情成功, jobId={}, jobName={}", jobId, vo.getJobName());
        return vo;
    }

    @Override
    public List<BizJobApiVO> listJobsByCompany(String yrdw, String excludeJobId, Integer limit) {
        String code = yrdw == null ? "" : yrdw.trim();
        if (code.isEmpty()) {
            return List.of();
        }
        int safeLimit = Math.max(1, Math.min(Objects.requireNonNullElse(limit, 12), 50));
        LambdaQueryWrapper<BizJobsInfo> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(BizJobsInfo::getYrdw, code);
        if (excludeJobId != null && !excludeJobId.isBlank()) {
            wrapper.ne(BizJobsInfo::getJobid, excludeJobId.trim());
        }
        wrapper.last("LIMIT " + safeLimit);
        List<BizJobsInfo> jobs = bizJobsInfoService.list(wrapper);
        List<BizJobApiVO> vos = toJobVoList(jobs);
        log.info("按企业查岗位成功, yrdw={}, excludeJobId={}, limit={}, count={}",
                code, excludeJobId, safeLimit, vos.size());
        return vos;
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
            LambdaQueryWrapper<BizJobsInfo> jobW = new LambdaQueryWrapper<>();
            BizJobListScopeSupport.applyKeywordScope(jobW, q);
            jobW.last("limit " + safeLimit);
            for (BizJobApiVO job : toJobVoList(bizJobsInfoService.list(jobW))) {
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
                    .like(BizCompanyInfo::getWid, q)
                    .or().like(BizCompanyInfo::getGsmc, q)
                    .or().like(BizCompanyInfo::getHylx, q)
                    .last("limit " + safeLimit));
            for (BizCompanyInfo company : companyRows) {
                Map<String, Object> item = new HashMap<>();
                item.put("credit_code", company.getWid());
                item.put("company_name", company.getGsmc());
                item.put("industry", dictLabelSupport.industryLabel(company.getHylx()));
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

    private List<BizJobApiVO> toJobVoList(List<BizJobsInfo> jobs) {
        if (jobs == null || jobs.isEmpty()) {
            return List.of();
        }
        Set<String> jobIds = jobs.stream().map(BizJobsInfo::getJobid).filter(Objects::nonNull).collect(Collectors.toSet());
        Map<String, BizJobsRagSync> ragMap = bizJobsRagSyncService.mapByJobIds(jobIds);
        Set<String> zzjgdmSet = jobs.stream()
                .map(BizJobsInfo::getYrdw)
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toSet());
        Map<String, BizCompanyInfo> companyMap = zzjgdmSet.isEmpty()
                ? Map.of()
                : bizCompanyInfoService.mapByZzjgdm(zzjgdmSet);

        List<BizJobApiVO> vos = new ArrayList<>(jobs.size());
        for (BizJobsInfo job : jobs) {
            BizCompanyInfo company = job.getYrdw() == null ? null : companyMap.get(job.getYrdw().trim());
            BizJobsRagSync rag = job.getJobid() == null ? null : ragMap.get(job.getJobid());
            vos.add(BizJobApiTranslator.toVo(job, rag, company, dictLabelSupport));
        }
        return vos;
    }

    private BizJobApiVO toJobVo(BizJobsInfo job) {
        BizCompanyInfo company = bizCompanyInfoService.getByZzjgdm(job.getYrdw());
        BizJobsRagSync rag = bizJobsRagSyncService.findByJobId(job.getJobid());
        return BizJobApiTranslator.toVo(job, rag, company, dictLabelSupport);
    }

    private List<Map<String, Object>> buildCompanyTypeFacets(String keyword) {
        List<Map<String, Object>> dictItems = loadDictItems(BizDictBm.DWXZ);
        Map<String, long[]> totals = initFacetTotals(dictItems);
        String keywordArg = keyword.isEmpty() ? null : keyword;

        for (JobFacetCountRow row : bizJobsInfoMapper.countJobsGroupByCompanyDwxz(keywordArg)) {
            if (row == null || row.getCode() == null || row.getCode().isBlank()) {
                continue;
            }
            String facetCode = resolveDwxzFacetCode(row.getCode().trim(), dictItems);
            if (facetCode == null) {
                continue;
            }
            long[] bucket = totals.computeIfAbsent(facetCode, k -> new long[2]);
            bucket[0] += safeCount(row.getTotal());
            bucket[1] += safeCount(row.getSynced());
        }
        return toFacetList(dictItems, totals);
    }

    private List<Map<String, Object>> buildIndustryFacets(String keyword) {
        List<Map<String, Object>> dictItems = loadDictItems(BizDictBm.HYLB);
        Map<String, long[]> totals = initFacetTotals(dictItems);
        String keywordArg = keyword.isEmpty() ? null : keyword;

        for (JobFacetCountRow row : bizJobsInfoMapper.countJobsGroupByCompanyHylx(keywordArg)) {
            if (row == null || row.getCode() == null || row.getCode().isBlank()) {
                continue;
            }
            String facetCode = resolveIndustryFacetCode(row.getCode().trim(), dictItems);
            if (facetCode == null) {
                continue;
            }
            long[] bucket = totals.computeIfAbsent(facetCode, k -> new long[2]);
            bucket[0] += safeCount(row.getTotal());
            bucket[1] += safeCount(row.getSynced());
        }
        return toFacetList(dictItems, totals);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> loadDictItems(String bm) {
        Optional<Map<String, Object>> bucket = sysCodeRedisCache.readBucket(bm);
        if (bucket.isEmpty()) {
            return List.of();
        }
        Object raw = bucket.get().get("items");
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (Object o : list) {
            if (o instanceof Map<?, ?> map) {
                items.add((Map<String, Object>) map);
            }
        }
        return items;
    }

    private Map<String, long[]> initFacetTotals(List<Map<String, Object>> dictItems) {
        Map<String, long[]> totals = new LinkedHashMap<>();
        for (Map<String, Object> item : dictItems) {
            String code = facetCodeOf(item);
            if (!code.isEmpty()) {
                totals.put(code, new long[2]);
            }
        }
        return totals;
    }

    private List<Map<String, Object>> toFacetList(List<Map<String, Object>> dictItems, Map<String, long[]> totals) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> item : dictItems) {
            String code = facetCodeOf(item);
            if (code.isEmpty()) {
                continue;
            }
            long[] bucket = totals.getOrDefault(code, new long[2]);
            Map<String, Object> facet = new LinkedHashMap<>();
            facet.put("code", code);
            facet.put("label", labelOf(item));
            facet.put("total", bucket[0]);
            facet.put("synced", bucket[1]);
            out.add(facet);
        }
        return out;
    }

    private String resolveDwxzFacetCode(String rawCode, List<Map<String, Object>> dictItems) {
        for (Map<String, Object> item : dictItems) {
            if (matchesDwxzRaw(rawCode, item)) {
                return facetCodeOf(item);
            }
        }
        return null;
    }

    private String resolveIndustryFacetCode(String rawCode, List<Map<String, Object>> dictItems) {
        for (Map<String, Object> item : dictItems) {
            if (matchesIndustryRaw(rawCode, item)) {
                return facetCodeOf(item);
            }
        }
        return null;
    }

    private boolean matchesDwxzRaw(String rawCode, Map<String, Object> item) {
        String dm = textOf(item.get("dm"));
        String id = textOf(item.get("id"));
        if (rawCode.equals(dm) || rawCode.equals(id)) {
            return true;
        }
        try {
            int rawInt = Integer.parseInt(rawCode);
            if (!dm.isEmpty()) {
                try {
                    if (rawInt == Integer.parseInt(dm)) {
                        return true;
                    }
                } catch (NumberFormatException ignored) {
                    // dm 非数字
                }
            }
            if (!id.isEmpty()) {
                try {
                    return rawInt == Integer.parseInt(id);
                } catch (NumberFormatException ignored) {
                    return false;
                }
            }
        } catch (NumberFormatException ignored) {
            return false;
        }
        return false;
    }

    private boolean matchesIndustryRaw(String rawCode, Map<String, Object> item) {
        String dm = textOf(item.get("dm"));
        String id = textOf(item.get("id"));
        String name = textOf(item.get("name"));
        if (rawCode.equals(dm) || rawCode.equals(id) || rawCode.equals(name)) {
            return true;
        }
        if (rawCode.length() == 1 && dm.length() == 1) {
            return Character.toUpperCase(rawCode.charAt(0)) == Character.toUpperCase(dm.charAt(0));
        }
        try {
            int rawInt = Integer.parseInt(rawCode);
            if (!dm.isEmpty()) {
                try {
                    if (rawInt == Integer.parseInt(dm)) {
                        return true;
                    }
                } catch (NumberFormatException ignored) {
                    // continue
                }
            }
            if (!id.isEmpty()) {
                try {
                    return rawInt == Integer.parseInt(id);
                } catch (NumberFormatException ignored) {
                    return false;
                }
            }
        } catch (NumberFormatException ignored) {
            return false;
        }
        return false;
    }

    private static String facetCodeOf(Map<String, Object> item) {
        String dm = textOf(item.get("dm"));
        if (!dm.isEmpty()) {
            return dm;
        }
        return textOf(item.get("id"));
    }

    private static String labelOf(Map<String, Object> item) {
        String name = textOf(item.get("name"));
        return name.isEmpty() ? facetCodeOf(item) : name;
    }

    private static String textOf(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private static long safeCount(Long value) {
        return value == null ? 0L : Math.max(0L, value);
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
