package com.ae8.occ.mapper.impl;

import com.ae8.occ.constant.OccConstants;
import com.ae8.occ.entity.OccEntity;
import com.ae8.occ.mapper.OccMapper;
import com.ae8.occ.repository.OccRepository;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.Path;
import jakarta.persistence.criteria.Predicate;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Repository;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@Repository
public class OccMapperImpl implements OccMapper {

    private final OccRepository occRepository;

    public OccMapperImpl(OccRepository occRepository) {
        this.occRepository = occRepository;
    }

    @Override
    public List<OccEntity> find(Map<String, Object> params) {
        if (params == null || params.isEmpty()) {
            return Collections.emptyList();
        }
        return occRepository.findAll(buildSpecification(params));
    }

    private Specification<OccEntity> buildSpecification(Map<String, Object> params) {
        return (root, query, cb) -> {
            List<Predicate> predicates = new ArrayList<>();
            addEqual(predicates, cb, root.get("blObjectUuid"), params.get(OccConstants.PARAM_BL_OBJECT_UUID));
            addEqual(predicates, cb, root.get("parentObjectUuid"), params.get(OccConstants.PARAM_PARENT_OBJECT_UUID));
            addEqual(predicates, cb, root.get("ae8Type"), params.get(OccConstants.PARAM_AE8_TYPE));
            addEqual(predicates, cb, root.get("blObjectType"), params.get(OccConstants.PARAM_BL_OBJECT_TYPE));
            addEqual(predicates, cb, root.get("ae8DrawingNo"), params.get(OccConstants.PARAM_AE8_DRAWING_NO));
            if (predicates.isEmpty()) {
                return cb.disjunction();
            }
            return cb.and(predicates.toArray(Predicate[]::new));
        };
    }

    private void addEqual(List<Predicate> predicates, CriteriaBuilder cb, Path<String> path, Object value) {
        if (value == null) {
            return;
        }
        String text = String.valueOf(value).trim();
        if (!StringUtils.hasText(text)) {
            return;
        }
        predicates.add(cb.equal(path, text));
    }
}
