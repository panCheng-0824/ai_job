package org.example.server_job.biz.vo;

import lombok.Data;
import org.example.server_job.biz.entity.BizAwardInfo;
import org.example.server_job.biz.entity.BizFamilyInfo;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.entity.BizXlzxGd;
import org.example.server_job.biz.entity.BizXlzxGy;
import org.example.server_job.biz.entity.BizXlzxZx;

import java.util.List;

@Data
public class BizStudentPortraitVO {

    private BizStudentInfo studentInfo;

    private List<BizFamilyInfo> familyInfoList;

    private List<BizAwardInfo> awardInfoList;

    private List<BizXlzxZx> counselingRecordList;

    private List<BizXlzxGy> counselorRecordList;

    private List<BizXlzxGd> trackingRecordList;
}
