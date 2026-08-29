package com.example.columnconfig.meta;

import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * In-memory index: moduleMark -> fields declared on the main entity.
 */
@Component
public class ColumnMetaRegistry {

    private final Map<String, List<ColumnMetaDefinition>> moduleFields = new ConcurrentHashMap<>();

    public void register(String moduleMark, List<ColumnMetaDefinition> fields) {
        moduleFields.put(moduleMark, List.copyOf(fields));
    }

    public boolean isEmpty() {
        return moduleFields.isEmpty();
    }

    public List<ColumnMetaDefinition> getAll(String moduleMark) {
        return moduleFields.getOrDefault(moduleMark, Collections.emptyList());
    }

    public List<ColumnMetaDefinition> getDisplayable(String moduleMark) {
        return getAll(moduleMark).stream()
                .filter(ColumnMetaDefinition::isDisplay)
                .collect(Collectors.toList());
    }

    public List<ColumnMetaDefinition> getConfigurable(String moduleMark) {
        return getAll(moduleMark).stream()
                .filter(item -> item.isDisplay() && item.isConfigurable())
                .collect(Collectors.toList());
    }

    public Optional<ColumnMetaDefinition> find(String moduleMark, String columnName) {
        return getAll(moduleMark).stream()
                .filter(item -> item.getColumnName().equals(columnName))
                .findFirst();
    }
}
