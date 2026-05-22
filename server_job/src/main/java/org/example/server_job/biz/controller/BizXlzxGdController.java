package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizXlzxGd;
import org.example.server_job.biz.service.BizXlzxGdService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/xlzx-gd")
public class BizXlzxGdController {

    private final BizXlzxGdService bizXlzxGdService;

    public BizXlzxGdController(BizXlzxGdService bizXlzxGdService) {
        this.bizXlzxGdService = bizXlzxGdService;
    }

    @GetMapping
    public List<BizXlzxGd> list() {
        return bizXlzxGdService.list();
    }

    @PostMapping
    public boolean save(@RequestBody BizXlzxGd request) {
        return bizXlzxGdService.save(request);
    }
}
