package com.example.columnconfig.repository;

import com.example.columnconfig.entity.ConfigDetailRecord;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ConfigDetailRecordRepository extends JpaRepository<ConfigDetailRecord, String> {

    List<ConfigDetailRecord> findByOwningUserAndModuleMarkOrderByCreateTimeDesc(String owningUser,
                                                                                String moduleMark);
}
