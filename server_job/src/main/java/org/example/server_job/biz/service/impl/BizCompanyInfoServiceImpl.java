package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.mapper.BizCompanyInfoMapper;
import org.example.server_job.biz.service.BizCompanyInfoService;
import org.springframework.stereotype.Service;

@Service
public class BizCompanyInfoServiceImpl extends ServiceImpl<BizCompanyInfoMapper, BizCompanyInfo> implements BizCompanyInfoService {
}
