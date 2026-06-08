package org.example.server_job.biz.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.example.server_job.biz.dto.JobFacetCountRow;
import org.example.server_job.biz.entity.BizJobsInfo;

import java.util.List;

@Mapper
public interface BizJobsInfoMapper extends BaseMapper<BizJobsInfo> {

    List<JobFacetCountRow> countJobsGroupByCompanyDwxz(@Param("keyword") String keyword);

    List<JobFacetCountRow> countJobsGroupByCompanyHylx(@Param("keyword") String keyword);
}

