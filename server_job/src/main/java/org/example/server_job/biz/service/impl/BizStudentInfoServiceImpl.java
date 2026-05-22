package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.biz.entity.BizAwardInfo;
import org.example.server_job.biz.entity.BizFamilyInfo;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.entity.BizXlzxGd;
import org.example.server_job.biz.entity.BizXlzxGy;
import org.example.server_job.biz.entity.BizXlzxZx;
import org.example.server_job.biz.mapper.BizAwardInfoMapper;
import org.example.server_job.biz.mapper.BizFamilyInfoMapper;
import org.example.server_job.biz.mapper.BizStudentInfoMapper;
import org.example.server_job.biz.mapper.BizXlzxGdMapper;
import org.example.server_job.biz.mapper.BizXlzxGyMapper;
import org.example.server_job.biz.mapper.BizXlzxZxMapper;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.biz.vo.BizStudentPortraitVO;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class BizStudentInfoServiceImpl extends ServiceImpl<BizStudentInfoMapper, BizStudentInfo> implements BizStudentInfoService {

    private static final Logger log = LogManager.getLogger(BizStudentInfoServiceImpl.class);

    private final BizAwardInfoMapper bizAwardInfoMapper;
    private final BizFamilyInfoMapper bizFamilyInfoMapper;
    private final BizXlzxZxMapper bizXlzxZxMapper;
    private final BizXlzxGyMapper bizXlzxGyMapper;
    private final BizXlzxGdMapper bizXlzxGdMapper;

    public BizStudentInfoServiceImpl(
            BizAwardInfoMapper bizAwardInfoMapper,
            BizFamilyInfoMapper bizFamilyInfoMapper,
            BizXlzxZxMapper bizXlzxZxMapper,
            BizXlzxGyMapper bizXlzxGyMapper,
            BizXlzxGdMapper bizXlzxGdMapper
    ) {
        this.bizAwardInfoMapper = bizAwardInfoMapper;
        this.bizFamilyInfoMapper = bizFamilyInfoMapper;
        this.bizXlzxZxMapper = bizXlzxZxMapper;
        this.bizXlzxGyMapper = bizXlzxGyMapper;
        this.bizXlzxGdMapper = bizXlzxGdMapper;
    }

    @Override
    public BizStudentPortraitVO getStudentPortraitByXh(Integer xh) {
        log.info("加载学生画像开始, xh={}", xh);
        BizStudentInfo studentInfo = this.getOne(new LambdaQueryWrapper<BizStudentInfo>()
                .eq(BizStudentInfo::getXh, xh)
                .last("limit 1"));
        List<BizFamilyInfo> familyInfoList = bizFamilyInfoMapper.selectList(new LambdaQueryWrapper<BizFamilyInfo>()
                .eq(BizFamilyInfo::getXh, xh));
        List<BizAwardInfo> awardInfoList = bizAwardInfoMapper.selectList(new LambdaQueryWrapper<BizAwardInfo>()
                .eq(BizAwardInfo::getXh, xh));
        List<BizXlzxZx> counselingRecordList = bizXlzxZxMapper.selectList(new LambdaQueryWrapper<BizXlzxZx>()
                .eq(BizXlzxZx::getXh, xh));
        List<BizXlzxGy> counselorRecordList = bizXlzxGyMapper.selectList(new LambdaQueryWrapper<BizXlzxGy>()
                .eq(BizXlzxGy::getXh, xh));
        List<BizXlzxGd> trackingRecordList = bizXlzxGdMapper.selectList(new LambdaQueryWrapper<BizXlzxGd>()
                .eq(BizXlzxGd::getXh, xh));
        log.info("加载学生画像完成, xh={}, hasStudent={}, familyCount={}, awardCount={}, counselingCount={}, counselorCount={}, trackingCount={}",
                xh, studentInfo != null, familyInfoList.size(), awardInfoList.size(),
                counselingRecordList.size(), counselorRecordList.size(), trackingRecordList.size());

        BizStudentPortraitVO portrait = new BizStudentPortraitVO();
        portrait.setStudentInfo(studentInfo);
        portrait.setFamilyInfoList(familyInfoList);
        portrait.setAwardInfoList(awardInfoList);
        portrait.setCounselingRecordList(counselingRecordList);
        portrait.setCounselorRecordList(counselorRecordList);
        portrait.setTrackingRecordList(trackingRecordList);
        return portrait;
    }
}
