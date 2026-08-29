package com.example.columnconfig.service.impl;

import com.example.columnconfig.dto.ColumnFieldsResponse;
import com.example.columnconfig.dto.ColumnItemDto;
import com.example.columnconfig.dto.SaveColumnConfigRequest;
import com.example.columnconfig.dto.SaveColumnConfigResponse;
import com.example.columnconfig.entity.ConfigColumn;
import com.example.columnconfig.entity.ConfigColumnDetail;
import com.example.columnconfig.entity.ConfigDetailRecord;
import com.example.columnconfig.meta.ColumnMetaDefinition;
import com.example.columnconfig.meta.ColumnMetaRegistry;
import com.example.columnconfig.meta.ColumnMetaScanner;
import com.example.columnconfig.repository.ConfigColumnDetailRepository;
import com.example.columnconfig.repository.ConfigColumnRepository;
import com.example.columnconfig.repository.ConfigDetailRecordRepository;
import com.example.columnconfig.service.ColumnConfigService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class ColumnConfigServiceImpl implements ColumnConfigService {

    private static final String DEFAULT_CONFIG_NAME = "默认方案";

    private final ColumnMetaScanner columnMetaScanner;
    private final ColumnMetaRegistry columnMetaRegistry;
    private final ConfigColumnRepository configColumnRepository;
    private final ConfigColumnDetailRepository configColumnDetailRepository;
    private final ConfigDetailRecordRepository configDetailRecordRepository;
    private final ObjectMapper objectMapper;

    public ColumnConfigServiceImpl(ColumnMetaScanner columnMetaScanner,
                                   ColumnMetaRegistry columnMetaRegistry,
                                   ConfigColumnRepository configColumnRepository,
                                   ConfigColumnDetailRepository configColumnDetailRepository,
                                   ConfigDetailRecordRepository configDetailRecordRepository,
                                   ObjectMapper objectMapper) {
        this.columnMetaScanner = columnMetaScanner;
        this.columnMetaRegistry = columnMetaRegistry;
        this.configColumnRepository = configColumnRepository;
        this.configColumnDetailRepository = configColumnDetailRepository;
        this.configDetailRecordRepository = configDetailRecordRepository;
        this.objectMapper = objectMapper;
    }

    @Override
    @Transactional(readOnly = true)
    public ColumnFieldsResponse queryFields(String userId, String moduleMark) {
        ensureMetaLoaded();
        List<ColumnMetaDefinition> configurable = columnMetaRegistry.getConfigurable(moduleMark);
        Map<String, ColumnItemDto> selectedMap = loadSelectedColumns(userId, moduleMark).stream()
                .collect(Collectors.toMap(ColumnItemDto::getColumnName, Function.identity(), (a, b) -> a, LinkedHashMap::new));

        ColumnFieldsResponse response = new ColumnFieldsResponse();
        List<ColumnItemDto> allFields = new ArrayList<>();
        for (ColumnMetaDefinition definition : configurable) {
            allFields.add(toItem(definition, selectedMap.get(definition.getColumnName())));
        }
        response.setAllFields(allFields);
        response.setSelected(new ArrayList<>(selectedMap.values()));
        return response;
    }

    @Override
    @Transactional(readOnly = true)
    public List<ColumnItemDto> queryTableColumns(String userId, String moduleMark) {
        ensureMetaLoaded();
        return loadSelectedColumns(userId, moduleMark);
    }

    /**
     * First save inserts header + details; later saves keep the same header UUID
     * and replace details. An operation row is always appended to configDetailRecord.
     */
    @Override
    @Transactional
    public SaveColumnConfigResponse saveOrUpdate(String userId, SaveColumnConfigRequest request) {
        ensureMetaLoaded();
        String moduleMark = request.getModuleMark();
        Optional<ConfigColumn> existing = configColumnRepository
                .findByOwningUserAndModuleMarkAndRange(userId, moduleMark, ConfigColumn.RANGE_USER);

        boolean created = existing.isEmpty();
        ConfigColumn header = created
                ? insertHeader(userId, moduleMark, request.getConfigName())
                : updateHeader(existing.get(), request.getConfigName());

        replaceDetails(header.getUuid(), moduleMark, request.getColumns());
        appendRecord(userId, moduleMark, header.getUuid(),
                created ? ConfigDetailRecord.ACTION_SAVE : ConfigDetailRecord.ACTION_UPDATE,
                request.getColumns());

        return new SaveColumnConfigResponse(header.getUuid(), created, request.getColumns().size());
    }

    private void ensureMetaLoaded() {
        columnMetaScanner.scanIfNecessary();
    }

    /**
     * Query: personal details if present, otherwise entity default displayable columns.
     */
    private List<ColumnItemDto> loadSelectedColumns(String userId, String moduleMark) {
        Optional<ConfigColumn> header = configColumnRepository
                .findByOwningUserAndModuleMarkAndRange(userId, moduleMark, ConfigColumn.RANGE_USER);
        if (header.isEmpty()) {
            return defaultDisplayColumns(moduleMark);
        }
        List<ConfigColumnDetail> details = configColumnDetailRepository
                .findByConfigColumnIdOrderByArrangeOrderAsc(header.get().getUuid());
        if (details.isEmpty()) {
            return List.of();
        }
        List<ColumnItemDto> result = new ArrayList<>();
        int fallbackOrder = 1;
        for (ConfigColumnDetail detail : details) {
            Optional<ColumnMetaDefinition> meta = columnMetaRegistry.find(moduleMark, detail.getColumnName());
            if (meta.isPresent() && !meta.get().isDisplay()) {
                continue;
            }
            ColumnItemDto item = new ColumnItemDto();
            item.setColumnName(detail.getColumnName());
            item.setLabel(meta.map(ColumnMetaDefinition::getLabel).orElse(detail.getColumnName()));
            item.setWidth(detail.getColumnWidth() != null
                    ? detail.getColumnWidth()
                    : meta.map(ColumnMetaDefinition::getDefaultWidth).orElse(120));
            item.setOrder(detail.getArrangeOrder() != null ? detail.getArrangeOrder() : fallbackOrder);
            item.setDisplay(meta.map(ColumnMetaDefinition::isDisplay).orElse(Boolean.TRUE));
            item.setConfigurable(meta.map(ColumnMetaDefinition::isConfigurable).orElse(Boolean.TRUE));
            result.add(item);
            fallbackOrder++;
        }
        return result;
    }

    private List<ColumnItemDto> defaultDisplayColumns(String moduleMark) {
        List<ColumnItemDto> result = new ArrayList<>();
        int order = 1;
        for (ColumnMetaDefinition definition : columnMetaRegistry.getDisplayable(moduleMark)) {
            ColumnItemDto item = toItem(definition, null);
            item.setOrder(order++);
            result.add(item);
        }
        return result;
    }

    private ColumnItemDto toItem(ColumnMetaDefinition definition, ColumnItemDto selected) {
        ColumnItemDto item = new ColumnItemDto();
        item.setColumnName(definition.getColumnName());
        item.setLabel(definition.getLabel());
        item.setWidth(selected != null && selected.getWidth() != null
                ? selected.getWidth()
                : definition.getDefaultWidth());
        item.setOrder(selected != null ? selected.getOrder() : definition.getDefaultOrder());
        item.setDisplay(definition.isDisplay());
        item.setConfigurable(definition.isConfigurable());
        return item;
    }

    private ConfigColumn insertHeader(String userId, String moduleMark, String configName) {
        ConfigColumn header = new ConfigColumn();
        header.setUuid(UUID.randomUUID().toString().replace("-", ""));
        header.setConfigName(StringUtils.hasText(configName) ? configName : DEFAULT_CONFIG_NAME);
        header.setRange(ConfigColumn.RANGE_USER);
        header.setOwningUser(userId);
        header.setModuleMark(moduleMark);
        return configColumnRepository.save(header);
    }

    private ConfigColumn updateHeader(ConfigColumn header, String configName) {
        if (StringUtils.hasText(configName)) {
            header.setConfigName(configName);
        }
        return configColumnRepository.save(header);
    }

    private void replaceDetails(String configUuid,
                                String moduleMark,
                                List<SaveColumnConfigRequest.SaveColumnItem> columns) {
        configColumnDetailRepository.deleteByConfigColumnId(configUuid);
        configColumnDetailRepository.flush();
        List<ConfigColumnDetail> rows = new ArrayList<>();
        int order = 1;
        for (SaveColumnConfigRequest.SaveColumnItem column : columns) {
            ConfigColumnDetail detail = new ConfigColumnDetail();
            detail.setConfigColumnId(configUuid);
            detail.setColumnName(column.getColumnName());
            detail.setArrangeOrder(order++);
            Integer width = column.getWidth();
            if (width == null) {
                width = columnMetaRegistry.find(moduleMark, column.getColumnName())
                        .map(ColumnMetaDefinition::getDefaultWidth)
                        .orElse(120);
            }
            detail.setColumnWidth(width);
            rows.add(detail);
        }
        if (!rows.isEmpty()) {
            configColumnDetailRepository.saveAll(rows);
        }
    }

    private void appendRecord(String userId,
                              String moduleMark,
                              String configUuid,
                              String action,
                              List<SaveColumnConfigRequest.SaveColumnItem> columns) {
        ConfigDetailRecord record = new ConfigDetailRecord();
        record.setUuid(UUID.randomUUID().toString().replace("-", ""));
        record.setOwningUser(userId);
        record.setModuleMark(moduleMark);
        record.setConfigColumnId(configUuid);
        record.setAction(action);
        record.setContent(writeContent(columns));
        configDetailRecordRepository.save(record);
    }

    private String writeContent(List<SaveColumnConfigRequest.SaveColumnItem> columns) {
        try {
            return objectMapper.writeValueAsString(columns);
        } catch (JsonProcessingException ex) {
            return "[]";
        }
    }
}
