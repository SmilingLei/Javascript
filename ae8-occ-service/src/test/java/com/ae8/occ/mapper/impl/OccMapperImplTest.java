package com.ae8.occ.mapper.impl;

import com.ae8.occ.constant.OccConstants;
import com.ae8.occ.entity.OccEntity;
import com.ae8.occ.mapper.OccMapper;
import com.ae8.occ.repository.OccRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@Import(OccMapperImpl.class)
class OccMapperImplTest {

    @Autowired
    private OccRepository occRepository;

    @Autowired
    private OccMapper occMapper;

    @BeforeEach
    void setUp() {
        occRepository.save(new OccEntity("n1", "p1", OccConstants.AE8_TYPE_CONNECT_CI,
                OccConstants.OBJECT_TYPE_CI_REVISION, null));
        occRepository.save(new OccEntity("n2", "p1", "零件",
                OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-1"));
    }

    @Test
    void findByBlObjectUuid() {
        Map<String, Object> params = new HashMap<>();
        params.put(OccConstants.PARAM_BL_OBJECT_UUID, "n1");
        List<OccEntity> found = occMapper.find(params);
        assertThat(found).hasSize(1);
        assertThat(found.get(0).getAe8Type()).isEqualTo(OccConstants.AE8_TYPE_CONNECT_CI);
    }

    @Test
    void findByParentObjectUuid() {
        Map<String, Object> params = new HashMap<>();
        params.put(OccConstants.PARAM_PARENT_OBJECT_UUID, "p1");
        assertThat(occMapper.find(params)).hasSize(2);
    }

    @Test
    void findReturnsEmptyWhenParamsEmpty() {
        assertThat(occMapper.find(null)).isEmpty();
        assertThat(occMapper.find(new HashMap<>())).isEmpty();
    }
}
