package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.service.BizCompanyInfoService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/company-info")
public class BizCompanyInfoController {

    private final BizCompanyInfoService bizCompanyInfoService;

    public BizCompanyInfoController(BizCompanyInfoService bizCompanyInfoService) {
        this.bizCompanyInfoService = bizCompanyInfoService;
    }

    @GetMapping
    public List<BizCompanyInfo> list() {
        return bizCompanyInfoService.list();
    }

    @GetMapping("/{id}")
    public BizCompanyInfo getById(@PathVariable String id) {
        return bizCompanyInfoService.getById(id);
    }

    @PostMapping
    public boolean save(@RequestBody BizCompanyInfo request) {
        return bizCompanyInfoService.save(request);
    }
}
