package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.mapper.BizCompanyInfoMapper;
import org.example.server_job.biz.service.BizCompanyInfoService;
import org.springframework.stereotype.Service;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
public class BizCompanyInfoServiceImpl extends ServiceImpl<BizCompanyInfoMapper, BizCompanyInfo> implements BizCompanyInfoService {

    @Override
    public BizCompanyInfo getByZzjgdm(String zzjgdm) {
        if (zzjgdm == null || zzjgdm.isBlank()) {
            return null;
        }
        return getOne(new LambdaQueryWrapper<BizCompanyInfo>()
                .eq(BizCompanyInfo::getZzjgdm, zzjgdm.trim())
                .last("limit 1"));
    }

    @Override
    public Map<String, BizCompanyInfo> mapByZzjgdm(Collection<String> zzjgdmList) {
        if (zzjgdmList == null || zzjgdmList.isEmpty()) {
            return Map.of();
        }
        List<String> codes = zzjgdmList.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .distinct()
                .toList();
        if (codes.isEmpty()) {
            return Map.of();
        }
        return list(new LambdaQueryWrapper<BizCompanyInfo>().in(BizCompanyInfo::getZzjgdm, codes)).stream()
                .filter(c -> c.getZzjgdm() != null && !c.getZzjgdm().isBlank())
                .collect(Collectors.toMap(c -> c.getZzjgdm().trim(), c -> c, (a, b) -> a));
    }

    @Override
    public BizCompanyInfo getByIdOrZzjgdm(String idOrZzjgdm) {
        if (idOrZzjgdm == null || idOrZzjgdm.isBlank()) {
            return null;
        }
        String key = idOrZzjgdm.trim();
        BizCompanyInfo byWid = getById(key);
        if (byWid != null) {
            return byWid;
        }
        return getByZzjgdm(key);
    }
}
