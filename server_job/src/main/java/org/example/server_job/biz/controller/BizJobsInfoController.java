package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.service.BizJobsInfoService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/jobs-info")
public class BizJobsInfoController {

    private final BizJobsInfoService bizJobsInfoService;

    public BizJobsInfoController(BizJobsInfoService bizJobsInfoService) {
        this.bizJobsInfoService = bizJobsInfoService;
    }

    @GetMapping
    public List<BizJobsInfo> list() {
        return bizJobsInfoService.list();
    }

    @GetMapping("/{id}")
    public BizJobsInfo getById(@PathVariable String id) {
        return bizJobsInfoService.getById(id);
    }

    @PostMapping
    public boolean save(@RequestBody BizJobsInfo request) {
        return bizJobsInfoService.save(request);
    }
}
