package org.example.server_job.biz.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.biz.entity.SysCode;
import org.example.server_job.biz.mapper.SysCodeMapper;
import org.example.server_job.client.redis.RedisStringClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 系统字典 Redis 缓存：按 BM 分桶 + DM→NAME 翻译映射。
 * CRUD 后全量或按类型重建，供查询接口与主数据翻译读取。
 */
@Component
public class SysCodeRedisCache {

    private static final Logger log = LoggerFactory.getLogger(SysCodeRedisCache.class);

    private final SysCodeMapper sysCodeMapper;
    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;

    public SysCodeRedisCache(SysCodeMapper sysCodeMapper, RedisStringClient redis, ObjectMapper objectMapper) {
        this.sysCodeMapper = sysCodeMapper;
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    /** 从 DB 全量重建全部字典 Redis 桶 */
    public void rebuildAll() {
        List<SysCode> allRows = sysCodeMapper.selectList(
                Wrappers.<SysCode>lambdaQuery().orderByAsc(SysCode::getBm).orderByAsc(SysCode::getDm)
        );
        Map<String, List<SysCode>> byBm = new LinkedHashMap<>();
        for (SysCode row : allRows) {
            String bm = row.getBm() == null ? "" : row.getBm().trim();
            byBm.computeIfAbsent(bm, k -> new ArrayList<>()).add(row);
        }
        for (Map.Entry<String, List<SysCode>> entry : byBm.entrySet()) {
            rebuildBucket(entry.getKey(), entry.getValue());
        }
        writeAllTypesBucket(byBm);
        log.info("系统字典 Redis 缓存已重建：类型 {} 个，总条目 {}", byBm.size(), allRows.size());
    }

    /**
     * 按 BM + DM 从 Redis 翻译字典名称；缓存未命中时回退 DB 并触发全量重建。
     *
     * @param bm 类型编码，如 job_dwxz、job_xzqh
     * @param dm 字典项编码
     * @return 字典文本 NAME，未找到返回 empty
     */
    public Optional<String> lookupName(String bm, Integer dm) {
        if (bm == null || bm.isBlank() || dm == null) {
            return Optional.empty();
        }
        return lookupNameByCode(bm, String.valueOf(dm));
    }

    /**
     * 按 BM + 字典项编码（DM，可为数字或字母）从 Redis 翻译名称。
     */
    public Optional<String> lookupNameByCode(String bm, String code) {
        if (bm == null || bm.isBlank() || code == null || code.isBlank()) {
            return Optional.empty();
        }
        String normalizedBm = bm.trim();
        String normalizedCode = code.trim();
        Optional<Map<String, String>> mapOpt = readLookupMap(normalizedBm);
        if (mapOpt.isEmpty()) {
            Optional<String> fromBucket = lookupFromBucket(normalizedBm, "dm", normalizedCode, "name");
            if (fromBucket.isPresent()) {
                return fromBucket;
            }
            rebuildAll();
            mapOpt = readLookupMap(normalizedBm);
        }
        if (mapOpt.isPresent()) {
            Optional<String> hit = Optional.ofNullable(mapOpt.get().get(normalizedCode));
            if (hit.isPresent()) {
                return hit;
            }
        }
        return lookupFromBucket(normalizedBm, "dm", normalizedCode, "name");
    }

    /**
     * 按 BM + 字典项 ID 从 Redis 翻译名称；缓存未命中时回退 DB 并触发全量重建。
     *
     * @param bm 类型编码
     * @param id 字典项主键 ID（如行业门类 808）
     */
    public Optional<String> lookupNameById(String bm, String id) {
        if (bm == null || bm.isBlank() || id == null || id.isBlank()) {
            return Optional.empty();
        }
        String normalizedBm = bm.trim();
        String normalizedId = id.trim();
        Optional<Map<String, String>> mapOpt = readIdLookupMap(normalizedBm);
        if (mapOpt.isEmpty()) {
            Optional<String> fromBucket = lookupFromBucket(normalizedBm, "id", normalizedId, "name");
            if (fromBucket.isPresent()) {
                return fromBucket;
            }
            rebuildAll();
            mapOpt = readIdLookupMap(normalizedBm);
        }
        if (mapOpt.isPresent()) {
            Optional<String> hit = Optional.ofNullable(mapOpt.get().get(normalizedId));
            if (hit.isPresent()) {
                return hit;
            }
        }
        return lookupFromBucket(normalizedBm, "id", normalizedId, "name");
    }

    /** 读取某 BM 下全部字典项桶 */
    public Optional<Map<String, Object>> readBucket(String bm) {
        if (bm == null || bm.isBlank()) {
            return Optional.empty();
        }
        return readJsonBucket(SysCodeRedisKeys.bucket(bm.trim()));
    }

    /** 读取全部 BM 类型汇总桶 */
    public Optional<Map<String, Object>> readAllTypes() {
        return readJsonBucket(SysCodeRedisKeys.ALL_TYPES);
    }

    private void rebuildBucket(String bm, List<SysCode> rows) {
        List<Map<String, Object>> items = new ArrayList<>();
        Map<String, String> lookup = new LinkedHashMap<>();
        Map<String, String> idLookup = new LinkedHashMap<>();
        String mc = null;
        for (SysCode row : rows) {
            items.add(SysCodeSupport.toItem(row));
            if (row.getDm() != null && !row.getDm().isBlank() && row.getName() != null) {
                lookup.put(row.getDm().trim(), row.getName());
            }
            if (row.getId() != null && !row.getId().isBlank() && row.getName() != null) {
                idLookup.put(row.getId().trim(), row.getName());
            }
            if (mc == null && row.getMc() != null && !row.getMc().isBlank()) {
                mc = row.getMc();
            }
        }
        writeBucket(SysCodeRedisKeys.bucket(bm), Map.of(
                "bm", bm,
                "mc", mc == null ? "" : mc,
                "items", items,
                "count", items.size(),
                "updated_at", LocalDateTime.now().toString()
        ));
        writeBucket(SysCodeRedisKeys.lookup(bm), Map.of(
                "bm", bm,
                "lookup", lookup,
                "count", lookup.size(),
                "updated_at", LocalDateTime.now().toString()
        ));
        writeBucket(SysCodeRedisKeys.lookupById(bm), Map.of(
                "bm", bm,
                "lookup", idLookup,
                "count", idLookup.size(),
                "updated_at", LocalDateTime.now().toString()
        ));
    }

    private void writeAllTypesBucket(Map<String, List<SysCode>> byBm) {
        List<Map<String, Object>> types = new ArrayList<>();
        for (Map.Entry<String, List<SysCode>> entry : byBm.entrySet()) {
            String bm = entry.getKey();
            List<SysCode> rows = entry.getValue();
            String mc = rows.stream()
                    .map(SysCode::getMc)
                    .filter(s -> s != null && !s.isBlank())
                    .findFirst()
                    .orElse("");
            Map<String, Object> typeInfo = new LinkedHashMap<>();
            typeInfo.put("bm", bm);
            typeInfo.put("mc", mc);
            typeInfo.put("count", rows.size());
            types.add(typeInfo);
        }
        writeBucket(SysCodeRedisKeys.ALL_TYPES, Map.of(
                "types", types,
                "count", types.size(),
                "updated_at", LocalDateTime.now().toString()
        ));
    }

    @SuppressWarnings("unchecked")
    private Optional<Map<String, String>> readLookupMap(String bm) {
        Optional<Map<String, Object>> bucket = readJsonBucket(SysCodeRedisKeys.lookup(bm));
        if (bucket.isEmpty()) {
            return Optional.empty();
        }
        Object lookupObj = bucket.get().get("lookup");
        if (!(lookupObj instanceof Map<?, ?> raw)) {
            return Optional.empty();
        }
        Map<String, String> result = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : raw.entrySet()) {
            if (e.getKey() != null && e.getValue() != null) {
                result.put(String.valueOf(e.getKey()), String.valueOf(e.getValue()));
            }
        }
        return Optional.of(result);
    }

    /** 缓存桶 items 列表内按字段匹配（避免 lookup 桶缺失时触发全量重建） */
    @SuppressWarnings("unchecked")
    private Optional<String> lookupFromBucket(String bm, String matchKey, String matchValue, String valueKey) {
        Optional<Map<String, Object>> bucket = readJsonBucket(SysCodeRedisKeys.bucket(bm));
        if (bucket.isEmpty()) {
            return Optional.empty();
        }
        Object itemsObj = bucket.get().get("items");
        if (!(itemsObj instanceof List<?> items)) {
            return Optional.empty();
        }
        for (Object itemObj : items) {
            if (!(itemObj instanceof Map<?, ?> item)) {
                continue;
            }
            Object mk = item.get(matchKey);
            if (mk == null || !matchValue.equals(String.valueOf(mk).trim())) {
                continue;
            }
            Object val = item.get(valueKey);
            if (val != null && !String.valueOf(val).isBlank()) {
                return Optional.of(String.valueOf(val).trim());
            }
        }
        return Optional.empty();
    }

    @SuppressWarnings("unchecked")
    private Optional<Map<String, String>> readIdLookupMap(String bm) {
        Optional<Map<String, Object>> bucket = readJsonBucket(SysCodeRedisKeys.lookupById(bm));
        if (bucket.isEmpty()) {
            return Optional.empty();
        }
        Object lookupObj = bucket.get().get("lookup");
        if (!(lookupObj instanceof Map<?, ?> raw)) {
            return Optional.empty();
        }
        Map<String, String> result = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : raw.entrySet()) {
            if (e.getKey() != null && e.getValue() != null) {
                result.put(String.valueOf(e.getKey()), String.valueOf(e.getValue()));
            }
        }
        return Optional.of(result);
    }

    private void writeBucket(String key, Map<String, Object> payload) {
        try {
            redis.set(key, objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("系统字典 Redis 序列化失败: " + key, e);
        }
    }

    @SuppressWarnings("unchecked")
    private Optional<Map<String, Object>> readJsonBucket(String key) {
        String raw = redis.get(key);
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        try {
            return Optional.of(objectMapper.readValue(raw, Map.class));
        } catch (JsonProcessingException e) {
            log.warn("系统字典 Redis 反序列化失败 key={}: {}", key, e.getMessage());
            return Optional.empty();
        }
    }
}
