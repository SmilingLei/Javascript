package com.example.columnconfig.repository;

import com.example.columnconfig.entity.ConfigColumn;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ConfigColumnRepository extends JpaRepository<ConfigColumn, String> {

    Optional<ConfigColumn> findByOwningUserAndModuleMarkAndRange(String owningUser,
                                                                 String moduleMark,
                                                                 String range);
}
