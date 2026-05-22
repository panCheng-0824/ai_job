package org.example.server_job.biz.controller;

import org.example.server_job.biz.entity.BizXlzxGy;
import org.example.server_job.biz.service.BizXlzxGyService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/biz/xlzx-gy")
public class BizXlzxGyController {

    private final BizXlzxGyService bizXlzxGyService;

    public BizXlzxGyController(BizXlzxGyService bizXlzxGyService) {
        this.bizXlzxGyService = bizXlzxGyService;
    }

    @GetMapping
    public List<BizXlzxGy> list() {
        return bizXlzxGyService.list();
    }

    @PostMapping
    public boolean save(@RequestBody BizXlzxGy request) {
        return bizXlzxGyService.save(request);
    }
}
