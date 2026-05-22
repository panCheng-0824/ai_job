package org.example.server_job.biz.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.vo.BizStudentPortraitVO;

public interface BizStudentInfoService extends IService<BizStudentInfo> {

    BizStudentPortraitVO getStudentPortraitByXh(Integer xh);
}
