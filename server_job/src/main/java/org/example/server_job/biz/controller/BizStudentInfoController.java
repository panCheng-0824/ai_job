package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.biz.vo.BizStudentPortraitVO;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/student-info")
public class BizStudentInfoController {

    private final BizStudentInfoService bizStudentInfoService;

    public BizStudentInfoController(BizStudentInfoService bizStudentInfoService) {
        this.bizStudentInfoService = bizStudentInfoService;
    }

    @GetMapping
    public List<BizStudentInfo> list() {
        return bizStudentInfoService.list();
    }

    @GetMapping("/portrait/{xh}")
    public BizStudentPortraitVO portrait(@PathVariable Integer xh) {
        return bizStudentInfoService.getStudentPortraitByXh(xh);
    }

    @PostMapping
    public boolean save(@RequestBody BizStudentInfo request) {
        return bizStudentInfoService.save(request);
    }
}
