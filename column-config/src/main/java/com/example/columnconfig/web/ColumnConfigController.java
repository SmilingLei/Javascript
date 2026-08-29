package com.example.columnconfig.web;

import com.example.columnconfig.dto.ColumnFieldsResponse;
import com.example.columnconfig.dto.ColumnItemDto;
import com.example.columnconfig.dto.SaveColumnConfigRequest;
import com.example.columnconfig.dto.SaveColumnConfigResponse;
import com.example.columnconfig.service.ColumnConfigService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/column-config")
public class ColumnConfigController {

    private final ColumnConfigService columnConfigService;

    public ColumnConfigController(ColumnConfigService columnConfigService) {
        this.columnConfigService = columnConfigService;
    }

    @GetMapping("/fields")
    public ColumnFieldsResponse fields(@RequestParam String moduleMark) {
        return columnConfigService.queryFields(CurrentUser.require(), moduleMark);
    }

    @GetMapping("/table-columns")
    public List<ColumnItemDto> tableColumns(@RequestParam String moduleMark) {
        return columnConfigService.queryTableColumns(CurrentUser.require(), moduleMark);
    }

    @PostMapping("/save")
    public SaveColumnConfigResponse save(@Valid @RequestBody SaveColumnConfigRequest request) {
        return columnConfigService.saveOrUpdate(CurrentUser.require(), request);
    }
}
