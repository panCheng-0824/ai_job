package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizFamilyInfo;
import org.example.server_job.biz.service.BizFamilyInfoService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/family-info")
public class BizFamilyInfoController {

    private final BizFamilyInfoService bizFamilyInfoService;

    public BizFamilyInfoController(BizFamilyInfoService bizFamilyInfoService) {
        this.bizFamilyInfoService = bizFamilyInfoService;
    }

    @GetMapping
    public List<BizFamilyInfo> list() {
        return bizFamilyInfoService.list();
    }

    @PostMapping
    public boolean save(@RequestBody BizFamilyInfo request) {
        return bizFamilyInfoService.save(request);
    }
}
