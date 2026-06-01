package org.example.server_job.interview.api.controller;

import org.example.server_job.interview.dto.InterviewIndustryCategorySaveRequest;
import org.example.server_job.interview.service.InterviewIndustryCategoryService;
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
 * 行业分类 API：字典查询 + 维护 CRUD。
 */
@RestController
@RequestMapping("/api/interview/industry")
public class InterviewIndustryCategoryApiController {

    private final InterviewIndustryCategoryService categoryService;

    public InterviewIndustryCategoryApiController(InterviewIndustryCategoryService categoryService) {
        this.categoryService = categoryService;
    }

    /**
     * 列表：维护页传 include_all=true 含 disabled；意图/分类候选传 for=intent|classify。
     */
    @GetMapping("/categories")
    public Map<String, Object> categories(
            @RequestParam(value = "for", required = false) String forPurpose,
            @RequestParam(value = "tree", defaultValue = "true") boolean tree,
            @RequestParam(value = "include_all", defaultValue = "false") boolean includeAll
    ) {
        return categoryService.listCategories(forPurpose, tree, includeAll);
    }

    @GetMapping("/categories/{categoryId}")
    public Map<String, Object> detail(@PathVariable("categoryId") String categoryId) {
        return categoryService.getDetail(categoryId);
    }

    @PostMapping("/categories")
    public Map<String, Object> create(@RequestBody InterviewIndustryCategorySaveRequest body) {
        return categoryService.create(body);
    }

    @PutMapping("/categories/{categoryId}")
    public Map<String, Object> update(
            @PathVariable("categoryId") String categoryId,
            @RequestBody InterviewIndustryCategorySaveRequest body
    ) {
        return categoryService.update(categoryId, body);
    }

    @DeleteMapping("/categories/{categoryId}")
    public Map<String, Object> delete(@PathVariable("categoryId") String categoryId) {
        return categoryService.delete(categoryId);
    }
}
