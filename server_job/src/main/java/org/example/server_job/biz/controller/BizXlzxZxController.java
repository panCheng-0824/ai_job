package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizXlzxZx;
import org.example.server_job.biz.service.BizXlzxZxService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/xlzx-zx")
public class BizXlzxZxController {

    private final BizXlzxZxService bizXlzxZxService;

    public BizXlzxZxController(BizXlzxZxService bizXlzxZxService) {
        this.bizXlzxZxService = bizXlzxZxService;
    }

    @GetMapping
    public List<BizXlzxZx> list() {
        return bizXlzxZxService.list();
    }

    @PostMapping
    public boolean save(@RequestBody BizXlzxZx request) {
        return bizXlzxZxService.save(request);
    }
}
