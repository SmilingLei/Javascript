package com.example.columnconfig;

import com.example.columnconfig.dto.ColumnFieldsResponse;
import com.example.columnconfig.dto.ColumnItemDto;
import com.example.columnconfig.dto.SaveColumnConfigRequest;
import com.example.columnconfig.dto.SaveColumnConfigResponse;
import com.example.columnconfig.entity.ConfigColumn;
import com.example.columnconfig.entity.ConfigDetailRecord;
import com.example.columnconfig.meta.ColumnMetaDefinition;
import com.example.columnconfig.meta.ColumnMetaRegistry;
import com.example.columnconfig.repository.ConfigColumnDetailRepository;
import com.example.columnconfig.repository.ConfigColumnRepository;
import com.example.columnconfig.repository.ConfigDetailRecordRepository;
import com.example.columnconfig.service.ColumnConfigService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Transactional
class ColumnConfigServiceImplTest {

    private static final String MODULE = "implement_table";

    @Autowired
    private ColumnConfigService columnConfigService;

    @Autowired
    private ColumnMetaRegistry columnMetaRegistry;

    @Autowired
    private ConfigColumnRepository configColumnRepository;

    @Autowired
    private ConfigColumnDetailRepository configColumnDetailRepository;

    @Autowired
    private ConfigDetailRecordRepository configDetailRecordRepository;

    @Test
    void scannerLoadsEntityAnnotationsIntoMemory() {
        List<ColumnMetaDefinition> all = columnMetaRegistry.getAll(MODULE);
        assertThat(all).extracting(ColumnMetaDefinition::getColumnName)
                .contains("fileName", "filePath", "bizType", "createdAt", "updatedAt", "innerRemark");

        assertThat(columnMetaRegistry.find(MODULE, "innerRemark"))
                .hasValueSatisfying(meta -> {
                    assertThat(meta.isDisplay()).isFalse();
                    assertThat(meta.isConfigurable()).isFalse();
                });
        assertThat(columnMetaRegistry.getConfigurable(MODULE))
                .extracting(ColumnMetaDefinition::getColumnName)
                .doesNotContain("innerRemark");
    }

    @Test
    void queryUsesEntityDefaultWhenUserNeverSaved() {
        List<ColumnItemDto> columns = columnConfigService.queryTableColumns("u001", MODULE);
        assertThat(columns).isNotEmpty();
        assertThat(columns).extracting(ColumnItemDto::getColumnName)
                .containsExactly("fileName", "filePath", "bizType", "createdAt", "updatedAt")
                .doesNotContain("innerRemark");
        assertThat(configColumnRepository.findByOwningUserAndModuleMarkAndRange(
                "u001", MODULE, ConfigColumn.RANGE_USER)).isEmpty();
    }

    @Test
    void firstSaveInsertsHeaderDetailsAndRecord() {
        SaveColumnConfigResponse response = columnConfigService.saveOrUpdate("u001", saveRequest("fileName", "filePath"));

        assertThat(response.isCreated()).isTrue();
        assertThat(response.getColumnCount()).isEqualTo(2);

        ConfigColumn header = configColumnRepository
                .findByOwningUserAndModuleMarkAndRange("u001", MODULE, ConfigColumn.RANGE_USER)
                .orElseThrow();
        assertThat(header.getUuid()).isEqualTo(response.getConfigUuid());
        assertThat(header.getConfigName()).isEqualTo("默认方案");

        assertThat(configColumnDetailRepository.findByConfigColumnIdOrderByArrangeOrderAsc(header.getUuid()))
                .extracting(detail -> detail.getColumnName() + ":" + detail.getArrangeOrder())
                .containsExactly("fileName:1", "filePath:2");

        List<ConfigDetailRecord> records = configDetailRecordRepository
                .findByOwningUserAndModuleMarkOrderByCreateTimeDesc("u001", MODULE);
        assertThat(records).hasSize(1);
        assertThat(records.get(0).getAction()).isEqualTo(ConfigDetailRecord.ACTION_SAVE);
        assertThat(records.get(0).getConfigColumnId()).isEqualTo(header.getUuid());
    }

    @Test
    void updateKeepsHeaderAndReplacesDetails() {
        SaveColumnConfigResponse first = columnConfigService.saveOrUpdate("u001", saveRequest("fileName", "filePath"));
        SaveColumnConfigResponse second = columnConfigService.saveOrUpdate("u001", saveRequest("createdAt", "fileName"));

        assertThat(second.isCreated()).isFalse();
        assertThat(second.getConfigUuid()).isEqualTo(first.getConfigUuid());

        assertThat(configColumnDetailRepository.findByConfigColumnIdOrderByArrangeOrderAsc(second.getConfigUuid()))
                .extracting(detail -> detail.getColumnName() + ":" + detail.getArrangeOrder())
                .containsExactly("createdAt:1", "fileName:2");

        List<String> actions = configDetailRecordRepository
                .findByOwningUserAndModuleMarkOrderByCreateTimeDesc("u001", MODULE)
                .stream()
                .map(ConfigDetailRecord::getAction)
                .collect(Collectors.toList());
        assertThat(actions).containsExactly(ConfigDetailRecord.ACTION_UPDATE, ConfigDetailRecord.ACTION_SAVE);

        List<ColumnItemDto> columns = columnConfigService.queryTableColumns("u001", MODULE);
        assertThat(columns).extracting(ColumnItemDto::getColumnName)
                .containsExactly("createdAt", "fileName");
    }

    @Test
    void differentUsersHaveIsolatedSchemes() {
        columnConfigService.saveOrUpdate("u001", saveRequest("fileName"));
        columnConfigService.saveOrUpdate("u002", saveRequest("filePath", "bizType"));

        assertThat(columnConfigService.queryTableColumns("u001", MODULE))
                .extracting(ColumnItemDto::getColumnName)
                .containsExactly("fileName");
        assertThat(columnConfigService.queryTableColumns("u002", MODULE))
                .extracting(ColumnItemDto::getColumnName)
                .containsExactly("filePath", "bizType");

        ColumnFieldsResponse fields = columnConfigService.queryFields("u001", MODULE);
        assertThat(fields.getSelected()).extracting(ColumnItemDto::getColumnName).containsExactly("fileName");
        assertThat(fields.getAllFields()).extracting(ColumnItemDto::getColumnName)
                .contains("fileName", "filePath", "bizType")
                .doesNotContain("innerRemark");
    }

    private SaveColumnConfigRequest saveRequest(String... names) {
        SaveColumnConfigRequest request = new SaveColumnConfigRequest();
        request.setModuleMark(MODULE);
        for (String name : names) {
            SaveColumnConfigRequest.SaveColumnItem item = new SaveColumnConfigRequest.SaveColumnItem();
            item.setColumnName(name);
            request.getColumns().add(item);
        }
        return request;
    }
}
