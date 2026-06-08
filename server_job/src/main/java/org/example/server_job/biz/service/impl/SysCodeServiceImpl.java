package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.biz.dto.SysCodeSaveRequest;
import org.example.server_job.biz.entity.SysCode;
import org.example.server_job.biz.mapper.SysCodeMapper;
import org.example.server_job.biz.service.SysCodeService;
import org.example.server_job.biz.support.SysCodeRedisCache;
import org.example.server_job.biz.support.SysCodeSupport;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;

/**
 * 系统字典 CRUD 与 Redis 查询实现。
 */
@Service
public class SysCodeServiceImpl implements SysCodeService {

    private static final Logger log = LoggerFactory.getLogger(SysCodeServiceImpl.class);

    private final SysCodeMapper sysCodeMapper;
    private final SysCodeRedisCache sysCodeRedisCache;

    public SysCodeServiceImpl(SysCodeMapper sysCodeMapper, SysCodeRedisCache sysCodeRedisCache) {
        this.sysCodeMapper = sysCodeMapper;
        this.sysCodeRedisCache = sysCodeRedisCache;
    }

    @Override
    public Map<String, Object> listTypes() {
        Optional<Map<String, Object>> cached = sysCodeRedisCache.readAllTypes();
        if (cached.isPresent()) {
            return cached.get();
        }
        refreshRedis();
        return sysCodeRedisCache.readAllTypes().orElseGet(() -> Map.of("types", List.of(), "count", 0));
    }

    @Override
    public Map<String, Object> listByBm(String bm, boolean tree) {
        String normalizedBm = requireBm(bm);
        Optional<Map<String, Object>> cached = sysCodeRedisCache.readBucket(normalizedBm);
        if (cached.isPresent()) {
            return withTreeFlag(cached.get(), tree);
        }
        refreshRedis();
        Optional<Map<String, Object>> after = sysCodeRedisCache.readBucket(normalizedBm);
        if (after.isEmpty()) {
            return Map.of("bm", normalizedBm, "items", List.of(), "count", 0);
        }
        return withTreeFlag(after.get(), tree);
    }

    @Override
    public Map<String, Object> lookup(String bm, Integer dm) {
        String normalizedBm = requireBm(bm);
        if (dm == null) {
            throw new ResponseStatusException(BAD_REQUEST, "dm 不能为空");
        }
        Optional<String> name = sysCodeRedisCache.lookupName(normalizedBm, dm);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("bm", normalizedBm);
        out.put("dm", dm);
        out.put("name", name.orElse(null));
        out.put("found", name.isPresent());
        return out;
    }

    @Override
    public Map<String, Object> getDetail(String id) {
        SysCode row = requireExists(id);
        return SysCodeSupport.toItem(row);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> create(SysCodeSaveRequest request) {
        validateSave(request, false);
        SysCode row = fromRequest(request, null);
        if (row.getId() == null || row.getId().isBlank()) {
            row.setId("sc_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16));
        }
        if (sysCodeMapper.selectById(row.getId()) != null) {
            row.setId(row.getId() + "_" + System.currentTimeMillis() % 10000);
        }
        sysCodeMapper.insert(row);
        refreshRedis();
        return Map.of("id", row.getId(), "item", SysCodeSupport.toItem(row));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> update(String id, SysCodeSaveRequest request) {
        SysCode existing = requireExists(id);
        validateSave(request, true);
        SysCode row = fromRequest(request, existing);
        row.setId(existing.getId());
        sysCodeMapper.updateById(row);
        refreshRedis();
        return Map.of("id", row.getId(), "item", SysCodeSupport.toItem(row));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> delete(String id) {
        SysCode row = requireExists(id);
        sysCodeMapper.deleteById(row.getId());
        refreshRedis();
        return Map.of("deleted", true, "id", row.getId());
    }

    /** 字典 CRUD 后重建 Redis 桶 */
    private void refreshRedis() {
        try {
            sysCodeRedisCache.rebuildAll();
        } catch (Exception e) {
            log.warn("系统字典 Redis 重建失败: {}", e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> withTreeFlag(Map<String, Object> bucket, boolean tree) {
        Map<String, Object> out = new LinkedHashMap<>(bucket);
        Object itemsObj = bucket.get("items");
        if (!(itemsObj instanceof List<?> rawItems)) {
            return out;
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (Object o : rawItems) {
            if (o instanceof Map<?, ?> m) {
                items.add((Map<String, Object>) m);
            }
        }
        out.put("items", tree ? SysCodeSupport.buildTree(items) : items);
        out.put("tree", tree);
        return out;
    }

    private SysCode requireExists(String id) {
        if (id == null || id.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, "id 不能为空");
        }
        SysCode row = sysCodeMapper.selectById(id.trim());
        if (row == null) {
            throw new ResponseStatusException(NOT_FOUND, "字典项不存在");
        }
        return row;
    }

    private static String requireBm(String bm) {
        if (bm == null || bm.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, "bm 不能为空");
        }
        return bm.trim();
    }

    private static void validateSave(SysCodeSaveRequest request, boolean isUpdate) {
        if (request == null) {
            throw new ResponseStatusException(BAD_REQUEST, "请求体不能为空");
        }
        if (!isUpdate && (request.bm() == null || request.bm().isBlank())) {
            throw new ResponseStatusException(BAD_REQUEST, "bm 不能为空");
        }
        if (request.dm() == null) {
            throw new ResponseStatusException(BAD_REQUEST, "dm 不能为空");
        }
        if (request.name() == null || request.name().isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, "name 不能为空");
        }
    }

    private static SysCode fromRequest(SysCodeSaveRequest req, SysCode existing) {
        SysCode row = new SysCode();
        row.setId(trimOrNull(req.id()));
        row.setFid(trimOrNull(req.fid()));
        row.setName(req.name().trim());
        row.setDm(req.dm() == null ? null : String.valueOf(req.dm()));
        row.setMc(req.mc() != null ? req.mc().trim() : (existing != null ? existing.getMc() : null));
        row.setBm(req.bm() != null ? req.bm().trim() : (existing != null ? existing.getBm() : null));
        row.setLbmc(trimOrNull(req.lbmc()));
        return row;
    }

    private static String trimOrNull(String v) {
        if (v == null || v.isBlank()) {
            return null;
        }
        return v.trim();
    }
}
