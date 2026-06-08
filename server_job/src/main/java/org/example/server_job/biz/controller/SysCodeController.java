package org.example.server_job.biz.controller;

import org.example.server_job.biz.dto.SysCodeSaveRequest;
import org.example.server_job.biz.service.SysCodeService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 系统字典 API：类型列表、按 BM 查询、编码翻译、维护 CRUD。
 */
@RestController
@RequestMapping("/api/biz/sys-code")
public class SysCodeController {

    private final SysCodeService sysCodeService;

    public SysCodeController(SysCodeService sysCodeService) {
        this.sysCodeService = sysCodeService;
    }

    /** 全部字典类型（BM）汇总，数据来自 Redis */
    @GetMapping("/types")
    public Map<String, Object> types() {
        return sysCodeService.listTypes();
    }

    /**
     * 按类型编码查字典项；省市区等级联传 tree=true。
     *
     * @param bm   类型编码，如 dwxz、gzszsf
     * @param tree 是否组装为树
     */
    @GetMapping
    public Map<String, Object> listByBm(
            @RequestParam String bm,
            @RequestParam(defaultValue = "false") boolean tree
    ) {
        return sysCodeService.listByBm(bm, tree);
    }

    /** 按 BM + DM 翻译字典名称，优先读 Redis */
    @GetMapping("/lookup")
    public Map<String, Object> lookup(
            @RequestParam String bm,
            @RequestParam Integer dm
    ) {
        return sysCodeService.lookup(bm, dm);
    }

    @GetMapping("/{id}")
    public Map<String, Object> detail(@PathVariable String id) {
        return sysCodeService.getDetail(id);
    }

    @PostMapping
    public Map<String, Object> create(@RequestBody SysCodeSaveRequest body) {
        return sysCodeService.create(body);
    }

    @PutMapping("/{id}")
    public Map<String, Object> update(@PathVariable String id, @RequestBody SysCodeSaveRequest body) {
        return sysCodeService.update(id, body);
    }

    @DeleteMapping("/{id}")
    public Map<String, Object> delete(@PathVariable String id) {
        return sysCodeService.delete(id);
    }
}
