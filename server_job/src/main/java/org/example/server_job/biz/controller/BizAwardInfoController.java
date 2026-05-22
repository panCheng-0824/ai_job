package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizAwardInfo;
import org.example.server_job.biz.service.BizAwardInfoService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/award-info")
public class BizAwardInfoController {

    private final BizAwardInfoService bizAwardInfoService;

    public BizAwardInfoController(BizAwardInfoService bizAwardInfoService) {
        this.bizAwardInfoService = bizAwardInfoService;
    }

    @GetMapping
    public List<BizAwardInfo> list() {
        return bizAwardInfoService.list();
    }

    @PostMapping
    public boolean save(@RequestBody BizAwardInfo request) {
        return bizAwardInfoService.save(request);
    }
}
