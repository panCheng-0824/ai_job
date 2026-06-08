package org.example.server_job.biz.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.biz.entity.SysCode;

/**
 * 系统字典表数据访问。
 */
@Mapper
public interface SysCodeMapper extends BaseMapper<SysCode> {
}
