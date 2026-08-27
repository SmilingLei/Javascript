package com.ae8.occ.controller;

import com.ae8.occ.constant.OccConstants;
import com.ae8.occ.dto.ApiResult;
import com.ae8.occ.service.OccRecursiveService;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/occ")
public class OccRecursiveController {

    private final OccRecursiveService occRecursiveService;

    public OccRecursiveController(OccRecursiveService occRecursiveService) {
        this.occRecursiveService = occRecursiveService;
    }

    /**
     * 根据 OCC 节点 bl_object_uuid 递归收集连接构型项下的零件图号。
     * 请求体为前端 Map，至少包含 bl_object_uuid。
     */
    @PostMapping("/part-drawing-nos")
    public ApiResult<List<String>> collectPartDrawingNos(@RequestBody Map<String, Object> params) {
        Map<String, Object> query = params == null ? new HashMap<>() : params;
        if (!StringUtils.hasText(asText(query.get(OccConstants.PARAM_BL_OBJECT_UUID)))) {
            return ApiResult.fail("bl_object_uuid 不能为空");
        }
        return ApiResult.ok(occRecursiveService.collectDrawingNos(query));
    }

    private String asText(Object value) {
        return value == null ? null : String.valueOf(value).trim();
    }
}
