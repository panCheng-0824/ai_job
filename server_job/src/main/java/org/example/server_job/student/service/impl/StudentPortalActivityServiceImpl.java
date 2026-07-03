package org.example.server_job.student.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizCompanyInfoService;
import org.example.server_job.biz.service.BizJobsInfoService;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.biz.support.BizDictBm;
import org.example.server_job.biz.support.BizDictLabelSupport;
import org.example.server_job.interview.entity.StudentInterviewRecordEntity;
import org.example.server_job.interview.mapper.StudentInterviewRecordMapper;
import org.example.server_job.student.entity.StudentCompanyReview;
import org.example.server_job.student.entity.StudentCompanyReviewTag;
import org.example.server_job.student.entity.StudentFavoriteJob;
import org.example.server_job.student.entity.StudentFollowCompany;
import org.example.server_job.student.entity.StudentJobApplication;
import org.example.server_job.student.entity.StudentJobInterviewBooking;
import org.example.server_job.student.entity.StudentJobReview;
import org.example.server_job.student.entity.StudentJobReviewTag;
import org.example.server_job.student.mapper.StudentCompanyReviewMapper;
import org.example.server_job.student.mapper.StudentCompanyReviewTagMapper;
import org.example.server_job.student.mapper.StudentFavoriteJobMapper;
import org.example.server_job.student.mapper.StudentFollowCompanyMapper;
import org.example.server_job.student.mapper.StudentJobApplicationMapper;
import org.example.server_job.student.mapper.StudentJobInterviewBookingMapper;
import org.example.server_job.student.mapper.StudentJobReviewMapper;
import org.example.server_job.student.mapper.StudentJobReviewTagMapper;
import org.example.server_job.student.service.StudentPortalActivityService;
import org.example.server_job.student.support.ReviewTagsCatalog;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
public class StudentPortalActivityServiceImpl implements StudentPortalActivityService {

    private static final Logger log = LogManager.getLogger(StudentPortalActivityServiceImpl.class);
    private static final int MAX_COMMENT = 2000;
    private static final DateTimeFormatter ISO_TS = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private final ReviewTagsCatalog reviewTagsCatalog;
    private final BizStudentInfoService bizStudentInfoService;
    private final BizJobsInfoService bizJobsInfoService;
    private final BizCompanyInfoService bizCompanyInfoService;
    private final BizDictLabelSupport dictLabelSupport;
    private final StudentFavoriteJobMapper favoriteMapper;
    private final StudentFollowCompanyMapper followMapper;
    private final StudentJobReviewMapper jobReviewMapper;
    private final StudentJobReviewTagMapper jobReviewTagMapper;
    private final StudentCompanyReviewMapper companyReviewMapper;
    private final StudentCompanyReviewTagMapper companyReviewTagMapper;
    private final StudentJobApplicationMapper applicationMapper;
    private final StudentJobInterviewBookingMapper interviewBookingMapper;
    private final StudentInterviewRecordMapper interviewRecordMapper;

    public StudentPortalActivityServiceImpl(
            ReviewTagsCatalog reviewTagsCatalog,
            BizStudentInfoService bizStudentInfoService,
            BizJobsInfoService bizJobsInfoService,
            BizCompanyInfoService bizCompanyInfoService,
            BizDictLabelSupport dictLabelSupport,
            StudentFavoriteJobMapper favoriteMapper,
            StudentFollowCompanyMapper followMapper,
            StudentJobReviewMapper jobReviewMapper,
            StudentJobReviewTagMapper jobReviewTagMapper,
            StudentCompanyReviewMapper companyReviewMapper,
            StudentCompanyReviewTagMapper companyReviewTagMapper,
            StudentJobApplicationMapper applicationMapper,
            StudentJobInterviewBookingMapper interviewBookingMapper,
            StudentInterviewRecordMapper interviewRecordMapper
    ) {
        this.reviewTagsCatalog = reviewTagsCatalog;
        this.bizStudentInfoService = bizStudentInfoService;
        this.bizJobsInfoService = bizJobsInfoService;
        this.bizCompanyInfoService = bizCompanyInfoService;
        this.dictLabelSupport = dictLabelSupport;
        this.favoriteMapper = favoriteMapper;
        this.followMapper = followMapper;
        this.jobReviewMapper = jobReviewMapper;
        this.jobReviewTagMapper = jobReviewTagMapper;
        this.companyReviewMapper = companyReviewMapper;
        this.companyReviewTagMapper = companyReviewTagMapper;
        this.applicationMapper = applicationMapper;
        this.interviewBookingMapper = interviewBookingMapper;
        this.interviewRecordMapper = interviewRecordMapper;
    }

    @Override
    public Map<String, Object> getReviewTags() {
        return reviewTagsCatalog.getCatalogForApi();
    }

    @Override
    public Map<String, Object> getMeSummary(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        long fc = favoriteMapper.selectCount(Wrappers.<StudentFavoriteJob>lambdaQuery().eq(StudentFavoriteJob::getStudentId, sid));
        long fl = followMapper.selectCount(Wrappers.<StudentFollowCompany>lambdaQuery().eq(StudentFollowCompany::getStudentId, sid));
        long jc = jobReviewMapper.selectCount(Wrappers.<StudentJobReview>lambdaQuery().eq(StudentJobReview::getStudentId, sid));
        long cc = companyReviewMapper.selectCount(Wrappers.<StudentCompanyReview>lambdaQuery().eq(StudentCompanyReview::getStudentId, sid));
        long ac = applicationMapper.selectCount(Wrappers.<StudentJobApplication>lambdaQuery().eq(StudentJobApplication::getStudentId, sid));
        long ic = interviewRecordMapper.selectCount(Wrappers.<StudentInterviewRecordEntity>lambdaQuery().eq(StudentInterviewRecordEntity::getStudentId, sid));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("favorite_job_count", fc);
        out.put("followed_company_count", fl);
        out.put("job_review_count", jc);
        out.put("company_review_count", cc);
        out.put("application_count", ac);
        out.put("interview_count", ic);
        return out;
    }

    @Override
    public Map<String, Object> getMeContext(String studentId, String jobId, String creditCode) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("job_favorited", false);
        out.put("job_applied", false);
        out.put("company_followed", false);
        out.put("my_job_review", null);
        out.put("my_company_review", null);
        String jid = jobId == null ? "" : jobId.trim();
        if (!jid.isEmpty()) {
            out.put("job_favorited", favoriteMapper.selectCount(Wrappers.<StudentFavoriteJob>lambdaQuery()
                    .eq(StudentFavoriteJob::getStudentId, sid)
                    .eq(StudentFavoriteJob::getJobId, jid)) > 0);
            out.put("job_applied", applicationMapper.selectCount(Wrappers.<StudentJobApplication>lambdaQuery()
                    .eq(StudentJobApplication::getStudentId, sid)
                    .eq(StudentJobApplication::getJobId, jid)) > 0);
            StudentJobReview rj = jobReviewMapper.selectOne(Wrappers.<StudentJobReview>lambdaQuery()
                    .eq(StudentJobReview::getStudentId, sid)
                    .eq(StudentJobReview::getJobId, jid)
                    .last("limit 1"));
            if (rj != null) {
                Map<Long, List<String>> tmap = loadJobReviewTags(List.of(rj.getId()));
                out.put("my_job_review", reviewPayload(rj, tmap.getOrDefault(rj.getId(), List.of())));
            }
        }
        String cc = creditCode == null ? "" : creditCode.trim();
        if (!cc.isEmpty()) {
            out.put("company_followed", followMapper.selectCount(Wrappers.<StudentFollowCompany>lambdaQuery()
                    .eq(StudentFollowCompany::getStudentId, sid)
                    .eq(StudentFollowCompany::getCreditCode, cc)) > 0);
            StudentCompanyReview rc = companyReviewMapper.selectOne(Wrappers.<StudentCompanyReview>lambdaQuery()
                    .eq(StudentCompanyReview::getStudentId, sid)
                    .eq(StudentCompanyReview::getCreditCode, cc)
                    .last("limit 1"));
            if (rc != null) {
                Map<Long, List<String>> tmap = loadCompanyReviewTags(List.of(rc.getId()));
                out.put("my_company_review", reviewPayload(rc, tmap.getOrDefault(rc.getId(), List.of())));
            }
        }
        return out;
    }

    @Override
    public Map<String, Object> getMeFavorites(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        List<String> ids = listFavoriteJobIds(sid);
        List<Map<String, Object>> jobs = new ArrayList<>();
        for (String jid : ids) {
            BizJobsInfo j = bizJobsInfoService.getById(jid);
            if (j != null) {
                jobs.add(hydrateJob(j));
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("job_ids", ids);
        out.put("jobs", jobs);
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> toggleFavorite(String studentId, String jobId) {
        String sid = normalizeStudentId(studentId);
        String jid = requireNonBlank(jobId, "job_id");
        ensureStudent(sid);
        requireJob(jid);
        boolean exists = favoriteMapper.selectCount(Wrappers.<StudentFavoriteJob>lambdaQuery()
                .eq(StudentFavoriteJob::getStudentId, sid)
                .eq(StudentFavoriteJob::getJobId, jid)) > 0;
        boolean favorited;
        if (exists) {
            favoriteMapper.delete(Wrappers.<StudentFavoriteJob>lambdaQuery()
                    .eq(StudentFavoriteJob::getStudentId, sid)
                    .eq(StudentFavoriteJob::getJobId, jid));
            favorited = false;
        } else {
            StudentFavoriteJob row = new StudentFavoriteJob();
            row.setStudentId(sid);
            row.setJobId(jid);
            favoriteMapper.insert(row);
            favorited = true;
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("favorited", favorited);
        out.put("favorite_jobs", listFavoriteJobIds(sid));
        log.info("toggleFavorite studentId={}, jobId={}, favorited={}", sid, jid, favorited);
        return out;
    }

    @Override
    public Map<String, Object> getMeFollows(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        List<String> codes = listFollowedCreditCodes(sid);
        List<Map<String, Object>> companies = new ArrayList<>();
        for (String code : codes) {
            BizCompanyInfo c = bizCompanyInfoService.getById(code);
            if (c != null) {
                companies.add(hydrateCompany(c));
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("credit_codes", codes);
        out.put("companies", companies);
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> toggleFollow(String studentId, String creditCode) {
        String sid = normalizeStudentId(studentId);
        String cc = requireNonBlank(creditCode, "credit_code");
        ensureStudent(sid);
        requireCompany(cc);
        boolean exists = followMapper.selectCount(Wrappers.<StudentFollowCompany>lambdaQuery()
                .eq(StudentFollowCompany::getStudentId, sid)
                .eq(StudentFollowCompany::getCreditCode, cc)) > 0;
        boolean following;
        if (exists) {
            followMapper.delete(Wrappers.<StudentFollowCompany>lambdaQuery()
                    .eq(StudentFollowCompany::getStudentId, sid)
                    .eq(StudentFollowCompany::getCreditCode, cc));
            following = false;
        } else {
            StudentFollowCompany row = new StudentFollowCompany();
            row.setStudentId(sid);
            row.setCreditCode(cc);
            followMapper.insert(row);
            following = true;
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("following", following);
        out.put("followed_companies", listFollowedCreditCodes(sid));
        log.info("toggleFollow studentId={}, creditCode={}, following={}", sid, cc, following);
        return out;
    }

    @Override
    public Map<String, Object> listMyJobReviewsEnriched(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        List<StudentJobReview> rows = jobReviewMapper.selectList(Wrappers.<StudentJobReview>lambdaQuery()
                .eq(StudentJobReview::getStudentId, sid));
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentJobReview r : rows) {
            Map<Long, List<String>> tmap = loadJobReviewTags(List.of(r.getId()));
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("job_id", r.getJobId());
            row.put("review", reviewPayload(r, tmap.getOrDefault(r.getId(), List.of())));
            BizJobsInfo job = bizJobsInfoService.getById(r.getJobId());
            if (job != null) {
                row.put("job", hydrateJob(job));
            } else {
                Map<String, Object> missing = new LinkedHashMap<>();
                missing.put("job_id", r.getJobId());
                missing.put("job_title", "（岗位不存在）");
                missing.put("_missing", true);
                row.put("job", missing);
            }
            items.add(row);
        }
        return Map.of("student_id", sid, "items", items);
    }

    @Override
    public Map<String, Object> listMyCompanyReviewsEnriched(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        List<StudentCompanyReview> rows = companyReviewMapper.selectList(Wrappers.<StudentCompanyReview>lambdaQuery()
                .eq(StudentCompanyReview::getStudentId, sid));
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentCompanyReview r : rows) {
            Map<Long, List<String>> tmap = loadCompanyReviewTags(List.of(r.getId()));
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("credit_code", r.getCreditCode());
            row.put("review", reviewPayload(r, tmap.getOrDefault(r.getId(), List.of())));
            BizCompanyInfo co = bizCompanyInfoService.getById(r.getCreditCode());
            if (co != null) {
                row.put("company", hydrateCompany(co));
            } else {
                Map<String, Object> missing = new LinkedHashMap<>();
                missing.put("credit_code", r.getCreditCode());
                missing.put("company_name", "（企业不存在）");
                missing.put("_missing", true);
                row.put("company", missing);
            }
            items.add(row);
        }
        return Map.of("student_id", sid, "items", items);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> upsertJobReview(String studentId, String jobId, int stars, String comment, List<String> tags) {
        String sid = normalizeStudentId(studentId);
        String jid = requireNonBlank(jobId, "job_id");
        ensureStudent(sid);
        requireJob(jid);
        if (stars < 1 || stars > 5) {
            throw new ResponseStatusException(BAD_REQUEST, "stars 须在 1～5 之间");
        }
        String cm = stripComment(comment);
        List<String> normTags = reviewTagsCatalog.normalizeJobTags(tags);
        StudentJobReview existing = jobReviewMapper.selectOne(Wrappers.<StudentJobReview>lambdaQuery()
                .eq(StudentJobReview::getStudentId, sid)
                .eq(StudentJobReview::getJobId, jid)
                .last("limit 1"));
        StudentJobReview row;
        if (existing == null) {
            row = new StudentJobReview();
            row.setStudentId(sid);
            row.setJobId(jid);
            row.setStars(stars);
            row.setComment(cm);
            jobReviewMapper.insert(row);
        } else {
            row = existing;
            row.setStars(stars);
            row.setComment(cm);
            jobReviewMapper.updateById(row);
        }
        row = jobReviewMapper.selectOne(Wrappers.<StudentJobReview>lambdaQuery()
                .eq(StudentJobReview::getStudentId, sid)
                .eq(StudentJobReview::getJobId, jid)
                .last("limit 1"));
        Objects.requireNonNull(row);
        jobReviewTagMapper.delete(Wrappers.<StudentJobReviewTag>lambdaQuery()
                .eq(StudentJobReviewTag::getJobReviewId, row.getId()));
        for (String tid : normTags) {
            StudentJobReviewTag t = new StudentJobReviewTag();
            t.setJobReviewId(row.getId());
            t.setTagId(tid);
            jobReviewTagMapper.insert(t);
        }
        Map<String, Object> review = reviewPayload(row, normTags);
        return Map.of("job_id", jid, "review", review);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> upsertCompanyReview(String studentId, String creditCode, int stars, String comment, List<String> tags) {
        String sid = normalizeStudentId(studentId);
        String cc = requireNonBlank(creditCode, "credit_code");
        ensureStudent(sid);
        requireCompany(cc);
        if (stars < 1 || stars > 5) {
            throw new ResponseStatusException(BAD_REQUEST, "stars 须在 1～5 之间");
        }
        String cm = stripComment(comment);
        List<String> normTags = reviewTagsCatalog.normalizeCompanyTags(tags);
        StudentCompanyReview existing = companyReviewMapper.selectOne(Wrappers.<StudentCompanyReview>lambdaQuery()
                .eq(StudentCompanyReview::getStudentId, sid)
                .eq(StudentCompanyReview::getCreditCode, cc)
                .last("limit 1"));
        StudentCompanyReview row;
        if (existing == null) {
            row = new StudentCompanyReview();
            row.setStudentId(sid);
            row.setCreditCode(cc);
            row.setStars(stars);
            row.setComment(cm);
            companyReviewMapper.insert(row);
        } else {
            row = existing;
            row.setStars(stars);
            row.setComment(cm);
            companyReviewMapper.updateById(row);
        }
        row = companyReviewMapper.selectOne(Wrappers.<StudentCompanyReview>lambdaQuery()
                .eq(StudentCompanyReview::getStudentId, sid)
                .eq(StudentCompanyReview::getCreditCode, cc)
                .last("limit 1"));
        Objects.requireNonNull(row);
        companyReviewTagMapper.delete(Wrappers.<StudentCompanyReviewTag>lambdaQuery()
                .eq(StudentCompanyReviewTag::getCompanyReviewId, row.getId()));
        for (String tid : normTags) {
            StudentCompanyReviewTag t = new StudentCompanyReviewTag();
            t.setCompanyReviewId(row.getId());
            t.setTagId(tid);
            companyReviewTagMapper.insert(t);
        }
        Map<String, Object> review = reviewPayload(row, normTags);
        return Map.of("credit_code", cc, "review", review);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> deleteJobReview(String studentId, String jobId) {
        String sid = normalizeStudentId(studentId);
        String jid = requireNonBlank(jobId, "job_id");
        ensureStudent(sid);
        requireJob(jid);
        int n = jobReviewMapper.delete(Wrappers.<StudentJobReview>lambdaQuery()
                .eq(StudentJobReview::getStudentId, sid)
                .eq(StudentJobReview::getJobId, jid));
        return Map.of("deleted", n > 0, "job_id", jid);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> deleteCompanyReview(String studentId, String creditCode) {
        String sid = normalizeStudentId(studentId);
        String cc = requireNonBlank(creditCode, "credit_code");
        ensureStudent(sid);
        requireCompany(cc);
        int n = companyReviewMapper.delete(Wrappers.<StudentCompanyReview>lambdaQuery()
                .eq(StudentCompanyReview::getStudentId, sid)
                .eq(StudentCompanyReview::getCreditCode, cc));
        return Map.of("deleted", n > 0, "credit_code", cc);
    }

    @Override
    public Map<String, Object> aggregateJobReviews(String jobId) {
        String jid = requireNonBlank(jobId, "job_id");
        requireJob(jid);
        List<StudentJobReview> rows = jobReviewMapper.selectList(Wrappers.<StudentJobReview>lambdaQuery()
                .eq(StudentJobReview::getJobId, jid)
                .orderByDesc(StudentJobReview::getUpdatedAt));
        if (rows.isEmpty()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("job_id", jid);
            empty.put("count", 0);
            empty.put("avg_stars", null);
            empty.put("items", List.of());
            empty.put("review_tag_distribution", List.of());
            return empty;
        }
        List<Long> ids = rows.stream().map(StudentJobReview::getId).toList();
        Map<Long, List<String>> tagMap = loadJobReviewTags(ids);
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentJobReview r : rows) {
            Map<String, Object> it = new LinkedHashMap<>();
            it.put("student_id", r.getStudentId());
            it.put("stars", r.getStars());
            it.put("comment", r.getComment() == null ? "" : r.getComment());
            it.put("updated_at", toIso(r.getUpdatedAt()));
            it.put("tags", tagMap.getOrDefault(r.getId(), List.of()));
            items.add(it);
        }
        double avg = rows.stream().mapToInt(StudentJobReview::getStars).average().orElse(0);
        double avgStars = BigDecimal.valueOf(avg).setScale(2, RoundingMode.HALF_UP).doubleValue();
        List<Map<String, Object>> dist = new ArrayList<>();
        for (Map<String, Object> row : jobReviewMapper.tagDistributionForJob(jid)) {
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("tag_id", String.valueOf(row.get("tag_id")));
            Object cnt = row.get("cnt");
            d.put("count", cnt instanceof Number ? ((Number) cnt).intValue() : Integer.parseInt(String.valueOf(cnt)));
            dist.add(d);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("job_id", jid);
        out.put("count", rows.size());
        out.put("avg_stars", avgStars);
        out.put("items", items);
        out.put("review_tag_distribution", dist);
        return out;
    }

    @Override
    public Map<String, Object> aggregateCompanyReviews(String creditCode) {
        String cc = requireNonBlank(creditCode, "credit_code");
        requireCompany(cc);
        long followerCount = followMapper.selectCount(Wrappers.<StudentFollowCompany>lambdaQuery()
                .eq(StudentFollowCompany::getCreditCode, cc));
        List<StudentCompanyReview> rows = companyReviewMapper.selectList(Wrappers.<StudentCompanyReview>lambdaQuery()
                .eq(StudentCompanyReview::getCreditCode, cc)
                .orderByDesc(StudentCompanyReview::getUpdatedAt));
        if (rows.isEmpty()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("credit_code", cc);
            empty.put("count", 0);
            empty.put("avg_stars", null);
            empty.put("items", List.of());
            empty.put("follower_count", followerCount);
            empty.put("review_tag_distribution", List.of());
            return empty;
        }
        List<Long> ids = rows.stream().map(StudentCompanyReview::getId).toList();
        Map<Long, List<String>> tagMap = loadCompanyReviewTags(ids);
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentCompanyReview r : rows) {
            Map<String, Object> it = new LinkedHashMap<>();
            it.put("student_id", r.getStudentId());
            it.put("stars", r.getStars());
            it.put("comment", r.getComment() == null ? "" : r.getComment());
            it.put("updated_at", toIso(r.getUpdatedAt()));
            it.put("tags", tagMap.getOrDefault(r.getId(), List.of()));
            items.add(it);
        }
        double avg = rows.stream().mapToInt(StudentCompanyReview::getStars).average().orElse(0);
        double avgStars = BigDecimal.valueOf(avg).setScale(2, RoundingMode.HALF_UP).doubleValue();
        List<Map<String, Object>> dist = new ArrayList<>();
        for (Map<String, Object> row : companyReviewMapper.tagDistributionForCompany(cc)) {
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("tag_id", String.valueOf(row.get("tag_id")));
            Object cnt = row.get("cnt");
            d.put("count", cnt instanceof Number ? ((Number) cnt).intValue() : Integer.parseInt(String.valueOf(cnt)));
            dist.add(d);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("credit_code", cc);
        out.put("count", rows.size());
        out.put("avg_stars", avgStars);
        out.put("items", items);
        out.put("follower_count", followerCount);
        out.put("review_tag_distribution", dist);
        return out;
    }

    private Map<String, Object> reviewPayload(StudentJobReview r, List<String> tags) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("stars", r.getStars());
        m.put("comment", r.getComment() == null ? "" : r.getComment());
        m.put("updated_at", toIso(r.getUpdatedAt()));
        m.put("tags", tags);
        return m;
    }

    private Map<String, Object> reviewPayload(StudentCompanyReview r, List<String> tags) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("stars", r.getStars());
        m.put("comment", r.getComment() == null ? "" : r.getComment());
        m.put("updated_at", toIso(r.getUpdatedAt()));
        m.put("tags", tags);
        return m;
    }

    private static String toIso(java.time.LocalDateTime t) {
        if (t == null) {
            return "";
        }
        return ISO_TS.format(t.withNano(0));
    }

    private static String stripComment(String comment) {
        String t = comment == null ? "" : comment.trim();
        if (t.length() > MAX_COMMENT) {
            return t.substring(0, MAX_COMMENT);
        }
        return t;
    }

    private Map<Long, List<String>> loadJobReviewTags(Collection<Long> reviewIds) {
        if (reviewIds == null || reviewIds.isEmpty()) {
            return Map.of();
        }
        Set<Long> idSet = new LinkedHashSet<>(reviewIds);
        List<StudentJobReviewTag> rows = jobReviewTagMapper.selectList(Wrappers.<StudentJobReviewTag>lambdaQuery()
                .in(StudentJobReviewTag::getJobReviewId, idSet)
                .orderByAsc(StudentJobReviewTag::getTagId));
        return rows.stream().collect(Collectors.groupingBy(
                StudentJobReviewTag::getJobReviewId,
                Collectors.mapping(StudentJobReviewTag::getTagId, Collectors.toList())
        ));
    }

    private Map<Long, List<String>> loadCompanyReviewTags(Collection<Long> reviewIds) {
        if (reviewIds == null || reviewIds.isEmpty()) {
            return Map.of();
        }
        Set<Long> idSet = new LinkedHashSet<>(reviewIds);
        List<StudentCompanyReviewTag> rows = companyReviewTagMapper.selectList(Wrappers.<StudentCompanyReviewTag>lambdaQuery()
                .in(StudentCompanyReviewTag::getCompanyReviewId, idSet)
                .orderByAsc(StudentCompanyReviewTag::getTagId));
        return rows.stream().collect(Collectors.groupingBy(
                StudentCompanyReviewTag::getCompanyReviewId,
                Collectors.mapping(StudentCompanyReviewTag::getTagId, Collectors.toList())
        ));
    }

    private List<String> listFavoriteJobIds(String sid) {
        return favoriteMapper.selectList(Wrappers.<StudentFavoriteJob>lambdaQuery()
                        .eq(StudentFavoriteJob::getStudentId, sid)
                        .orderByDesc(StudentFavoriteJob::getCreatedAt))
                .stream()
                .map(StudentFavoriteJob::getJobId)
                .toList();
    }

    private List<String> listFollowedCreditCodes(String sid) {
        return followMapper.selectList(Wrappers.<StudentFollowCompany>lambdaQuery()
                        .eq(StudentFollowCompany::getStudentId, sid)
                        .orderByDesc(StudentFollowCompany::getCreatedAt))
                .stream()
                .map(StudentFollowCompany::getCreditCode)
                .toList();
    }

    private Map<String, Object> hydrateJob(BizJobsInfo j) {
        BizCompanyInfo company = bizCompanyInfoService.getByZzjgdm(j.getYrdw());
        Map<String, Object> cr = new LinkedHashMap<>();
        cr.put("company_name", company != null ? company.getGsmc() : j.getYrdw());
        cr.put("credit_code", j.getYrdw());
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("job_id", j.getJobid());
        m.put("job_title", j.getZwmc());
        m.put("city", j.getGzdd());
        m.put("district", j.getGzdd());
        m.put("salary_range_month", j.getYxjb() == null ? null : String.valueOf(j.getYxjb()));
        m.put("salary_months", "-");
        m.put("company_relation", cr);
        return m;
    }

    private Map<String, Object> hydrateCompany(BizCompanyInfo c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("credit_code", c.getWid());
        m.put("company_name", c.getGsmc());
        m.put("industry", dictLabelSupport.industryLabel(c.getHylx()));
        m.put("employee_count_range", dictLabelSupport.gsgmLabel(c.getGsgm()));
        m.put("company_type", dictLabelSupport.dwxzLabel(c.getDwxz()));
        return m;
    }

    @Override
    public Map<String, Object> getMeApplications(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        List<StudentJobApplication> rows = applicationMapper.selectList(Wrappers.<StudentJobApplication>lambdaQuery()
                .eq(StudentJobApplication::getStudentId, sid)
                .orderByDesc(StudentJobApplication::getCreatedAt));
        List<String> ids = rows.stream().map(StudentJobApplication::getJobId).toList();
        List<Map<String, Object>> jobs = new ArrayList<>();
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentJobApplication row : rows) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("job_id", row.getJobId());
            item.put("resume_id", row.getResumeId());
            item.put("source", row.getSource());
            item.put("applied_at", toIso(row.getCreatedAt()));
            BizJobsInfo j = bizJobsInfoService.getById(row.getJobId());
            if (j != null) {
                Map<String, Object> hydrated = hydrateJob(j);
                jobs.add(hydrated);
                item.put("job", hydrated);
            }
            items.add(item);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("job_ids", ids);
        out.put("jobs", jobs);
        out.put("items", items);
        out.put("application_count", rows.size());
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> submitJobApplication(String studentId, String jobId, String resumeId, String source) {
        String sid = normalizeStudentId(studentId);
        String jid = requireNonBlank(jobId, "job_id");
        ensureStudent(sid);
        requireJob(jid);
        boolean exists = applicationMapper.selectCount(Wrappers.<StudentJobApplication>lambdaQuery()
                .eq(StudentJobApplication::getStudentId, sid)
                .eq(StudentJobApplication::getJobId, jid)) > 0;
        if (exists) {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("applied", true);
            out.put("already_applied", true);
            out.put("job_id", jid);
            out.put("application_count", applicationMapper.selectCount(Wrappers.<StudentJobApplication>lambdaQuery()
                    .eq(StudentJobApplication::getStudentId, sid)));
            return out;
        }
        StudentJobApplication row = new StudentJobApplication();
        row.setStudentId(sid);
        row.setJobId(jid);
        String rid = resumeId == null ? "" : resumeId.trim();
        row.setResumeId(rid.isEmpty() ? null : rid);
        String src = source == null ? "" : source.trim();
        row.setSource(src.isEmpty() ? "one_click" : src);
        applicationMapper.insert(row);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("applied", true);
        out.put("already_applied", false);
        out.put("job_id", jid);
        out.put("application_count", applicationMapper.selectCount(Wrappers.<StudentJobApplication>lambdaQuery()
                .eq(StudentJobApplication::getStudentId, sid)));
        log.info("submitJobApplication studentId={}, jobId={}, resumeId={}", sid, jid, row.getResumeId());
        return out;
    }

    @Override
    public Map<String, Object> getMeInterviewBookings(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        List<StudentJobInterviewBooking> rows = interviewBookingMapper.selectList(
                Wrappers.<StudentJobInterviewBooking>lambdaQuery()
                        .eq(StudentJobInterviewBooking::getStudentId, sid)
                        .orderByDesc(StudentJobInterviewBooking::getCreatedAt)
        );
        List<String> ids = rows.stream().map(StudentJobInterviewBooking::getJobId).toList();
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentJobInterviewBooking row : rows) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("booking_id", row.getId());
            item.put("job_id", row.getJobId());
            item.put("job_title", row.getJobTitle());
            item.put("company_name", row.getCompanyName());
            item.put("source", row.getSource());
            item.put("booked_at", toIso(row.getCreatedAt()));
            BizJobsInfo j = bizJobsInfoService.getById(row.getJobId());
            if (j != null) {
                item.put("job", hydrateJob(j));
            }
            items.add(item);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("job_ids", ids);
        out.put("items", items);
        out.put("booking_count", rows.size());
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> submitJobInterviewBooking(String studentId, String jobId, String source) {
        String sid = normalizeStudentId(studentId);
        String jid = requireNonBlank(jobId, "job_id");
        ensureStudent(sid);
        requireJob(jid);
        BizJobsInfo job = bizJobsInfoService.getById(jid);
        boolean exists = interviewBookingMapper.selectCount(Wrappers.<StudentJobInterviewBooking>lambdaQuery()
                .eq(StudentJobInterviewBooking::getStudentId, sid)
                .eq(StudentJobInterviewBooking::getJobId, jid)) > 0;
        if (exists) {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("booked", true);
            out.put("already_booked", true);
            out.put("job_id", jid);
            out.put("booking_count", interviewBookingMapper.selectCount(
                    Wrappers.<StudentJobInterviewBooking>lambdaQuery()
                            .eq(StudentJobInterviewBooking::getStudentId, sid)
            ));
            return out;
        }
        Map<String, Object> hydrated = hydrateJob(job);
        String jobTitle = String.valueOf(hydrated.getOrDefault("job_title", ""));
        String companyName = "";
        Object cr = hydrated.get("company_relation");
        if (cr instanceof Map companyRel) {
            companyName = String.valueOf(companyRel.getOrDefault("company_name", ""));
        }
        StudentJobInterviewBooking row = new StudentJobInterviewBooking();
        row.setStudentId(sid);
        row.setJobId(jid);
        row.setJobTitle(jobTitle);
        row.setCompanyName(companyName);
        String src = source == null ? "" : source.trim();
        row.setSource(src.isEmpty() ? "job_card" : src);
        interviewBookingMapper.insert(row);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("booked", true);
        out.put("already_booked", false);
        out.put("job_id", jid);
        out.put("booking_id", row.getId());
        out.put("booking_count", interviewBookingMapper.selectCount(
                Wrappers.<StudentJobInterviewBooking>lambdaQuery()
                        .eq(StudentJobInterviewBooking::getStudentId, sid)
        ));
        log.info("submitJobInterviewBooking studentId={}, jobId={}, bookingId={}", sid, jid, row.getId());
        return out;
    }

    private String normalizeStudentId(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, "student_id 不能为空");
        }
        String cleaned = raw.trim();
        String upper = cleaned.toUpperCase();
        if (upper.startsWith("STU")) {
            cleaned = cleaned.substring(3).trim();
        }
        try {
            return String.valueOf(Integer.parseInt(cleaned));
        } catch (NumberFormatException e) {
            throw new ResponseStatusException(BAD_REQUEST, "student_id 格式不正确");
        }
    }

    private void ensureStudent(String canonicalStudentId) {
        Integer xh = Integer.valueOf(canonicalStudentId);
        BizStudentInfo one = bizStudentInfoService.getOne(Wrappers.<BizStudentInfo>lambdaQuery()
                .eq(BizStudentInfo::getXh, xh)
                .last("limit 1"));
        if (one == null) {
            throw new ResponseStatusException(NOT_FOUND, "学生不存在");
        }
    }

    private void requireJob(String jobId) {
        if (bizJobsInfoService.getById(jobId) == null) {
            throw new ResponseStatusException(NOT_FOUND, "岗位不存在");
        }
    }

    private void requireCompany(String creditCode) {
        if (bizCompanyInfoService.getById(creditCode) == null) {
            throw new ResponseStatusException(NOT_FOUND, "企业不存在");
        }
    }

    private static String requireNonBlank(String v, String field) {
        if (v == null || v.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, field + " 不能为空");
        }
        return v.trim();
    }
}
