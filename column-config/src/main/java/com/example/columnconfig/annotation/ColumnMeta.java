package com.example.columnconfig.annotation;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks a main-table entity field as a candidate column for per-user layout.
 * Spring Boot does not interpret this annotation; {@code ColumnMetaScanner} reads it.
 */
@Documented
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ColumnMeta {

    String label();

    boolean display() default true;

    boolean configurable() default true;

    int defaultWidth() default 120;

    int defaultOrder() default 0;
}
