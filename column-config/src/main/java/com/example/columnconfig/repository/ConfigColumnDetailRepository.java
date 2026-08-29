package com.example.columnconfig.repository;

import com.example.columnconfig.entity.ConfigColumnDetail;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ConfigColumnDetailRepository extends JpaRepository<ConfigColumnDetail, Long> {

    List<ConfigColumnDetail> findByConfigColumnIdOrderByArrangeOrderAsc(String configColumnId);

    void deleteByConfigColumnId(String configColumnId);
}
