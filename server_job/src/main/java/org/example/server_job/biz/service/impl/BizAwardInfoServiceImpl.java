package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.server_job.biz.entity.BizAwardInfo;
import org.example.server_job.biz.mapper.BizAwardInfoMapper;
import org.example.server_job.biz.service.BizAwardInfoService;
import org.springframework.stereotype.Service;

@Service
public class BizAwardInfoServiceImpl extends ServiceImpl<BizAwardInfoMapper, BizAwardInfo> implements BizAwardInfoService {
}
