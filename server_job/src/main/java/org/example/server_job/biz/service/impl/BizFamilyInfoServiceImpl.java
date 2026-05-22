package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.server_job.biz.entity.BizFamilyInfo;
import org.example.server_job.biz.mapper.BizFamilyInfoMapper;
import org.example.server_job.biz.service.BizFamilyInfoService;
import org.springframework.stereotype.Service;

@Service
public class BizFamilyInfoServiceImpl extends ServiceImpl<BizFamilyInfoMapper, BizFamilyInfo> implements BizFamilyInfoService {
}
