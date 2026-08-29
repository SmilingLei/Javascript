package com.example.columnconfig.service;

import com.example.columnconfig.dto.ColumnFieldsResponse;
import com.example.columnconfig.dto.ColumnItemDto;
import com.example.columnconfig.dto.SaveColumnConfigRequest;
import com.example.columnconfig.dto.SaveColumnConfigResponse;

import java.util.List;

public interface ColumnConfigService {

    ColumnFieldsResponse queryFields(String userId, String moduleMark);

    List<ColumnItemDto> queryTableColumns(String userId, String moduleMark);

    SaveColumnConfigResponse saveOrUpdate(String userId, SaveColumnConfigRequest request);
}
