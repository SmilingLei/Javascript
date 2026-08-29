package com.example.columnconfig.meta;

import com.example.columnconfig.annotation.ColumnMeta;
import com.example.columnconfig.annotation.ColumnModule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.ClassPathScanningCandidateComponentProvider;
import org.springframework.core.type.filter.AnnotationTypeFilter;
import org.springframework.stereotype.Component;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Reads {@link ColumnMeta} from entity classes. Triggered at startup and
 * again on first request if the registry is still empty.
 */
@Component
public class ColumnMetaScanner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(ColumnMetaScanner.class);

    private final ColumnMetaRegistry registry;
    private final String basePackage;
    private final AtomicBoolean scanned = new AtomicBoolean(false);

    public ColumnMetaScanner(ColumnMetaRegistry registry,
                             @Value("${column-config.entity-base-package:com.example.columnconfig.entity}") String basePackage) {
        this.registry = registry;
        this.basePackage = basePackage;
    }

    @Override
    public void run(ApplicationArguments args) {
        scanIfNecessary();
    }

    public void scanIfNecessary() {
        if (scanned.get() && !registry.isEmpty()) {
            return;
        }
        synchronized (this) {
            if (scanned.get() && !registry.isEmpty()) {
                return;
            }
            doScan();
            scanned.set(true);
        }
    }

    private void doScan() {
        ClassPathScanningCandidateComponentProvider provider =
                new ClassPathScanningCandidateComponentProvider(false);
        provider.addIncludeFilter(new AnnotationTypeFilter(ColumnModule.class));
        Set<BeanDefinition> candidates = provider.findCandidateComponents(basePackage);
        int modules = 0;
        for (BeanDefinition candidate : candidates) {
            try {
                Class<?> clazz = Class.forName(candidate.getBeanClassName());
                registerClass(clazz);
                modules++;
            } catch (ClassNotFoundException ex) {
                log.warn("Skip unreadable entity {}", candidate.getBeanClassName(), ex);
            }
        }
        log.info("Column meta scan finished, modules={}, package={}", modules, basePackage);
    }

    private void registerClass(Class<?> clazz) {
        ColumnModule module = clazz.getAnnotation(ColumnModule.class);
        if (module == null) {
            return;
        }
        List<ColumnMetaDefinition> fields = new ArrayList<>();
        for (Class<?> current = clazz; current != null && current != Object.class; current = current.getSuperclass()) {
            for (Field field : current.getDeclaredFields()) {
                ColumnMeta meta = field.getAnnotation(ColumnMeta.class);
                if (meta == null) {
                    continue;
                }
                fields.add(new ColumnMetaDefinition(
                        field.getName(),
                        meta.label(),
                        meta.display(),
                        meta.configurable(),
                        meta.defaultWidth(),
                        meta.defaultOrder()
                ));
            }
        }
        fields.sort(Comparator.comparingInt(ColumnMetaDefinition::getDefaultOrder)
                .thenComparing(ColumnMetaDefinition::getColumnName));
        registry.register(module.value(), fields);
        log.info("Registered module {} with {} annotated fields from {}",
                module.value(), fields.size(), clazz.getName());
    }
}
