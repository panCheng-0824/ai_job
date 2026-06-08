package org.example.server_job.biz.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.server_job.biz.entity.BizCompanyInfo;

import java.util.Collection;
import java.util.Map;

public interface BizCompanyInfoService extends IService<BizCompanyInfo> {

    /** 按组织机构代码 {@code zzjgdm} 查单条企业（岗位表 {@code yrdw} 存此字段）。 */
    BizCompanyInfo getByZzjgdm(String zzjgdm);

    /** 批量按 {@code zzjgdm} 索引，供岗位列表关联企业名称等。 */
    Map<String, BizCompanyInfo> mapByZzjgdm(Collection<String> zzjgdmList);

    /**
     * 按企业主键 {@code WID} 或组织机构代码 {@code zzjgdm} 查单条。
     * 详情页路由参数可能是 WID，岗位关联字段 {@code yrdw} 存的是 zzjgdm。
     */
    BizCompanyInfo getByIdOrZzjgdm(String idOrZzjgdm);
}
