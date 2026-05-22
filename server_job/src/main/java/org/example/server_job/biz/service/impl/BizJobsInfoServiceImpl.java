package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.mapper.BizJobsInfoMapper;
import org.example.server_job.biz.service.BizJobsInfoService;
import org.springframework.stereotype.Service;

@Service
public class BizJobsInfoServiceImpl extends ServiceImpl<BizJobsInfoMapper, BizJobsInfo> implements BizJobsInfoService {
}
