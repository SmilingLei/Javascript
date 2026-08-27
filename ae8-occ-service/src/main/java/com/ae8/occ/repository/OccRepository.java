package com.ae8.occ.repository;

import com.ae8.occ.entity.OccEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

public interface OccRepository extends JpaRepository<OccEntity, String>, JpaSpecificationExecutor<OccEntity> {
}
