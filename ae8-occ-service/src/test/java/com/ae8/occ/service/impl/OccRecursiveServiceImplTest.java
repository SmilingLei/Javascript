package com.ae8.occ.service.impl;

import com.ae8.occ.constant.OccConstants;
import com.ae8.occ.entity.OccEntity;
import com.ae8.occ.mapper.OccMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OccRecursiveServiceImplTest {

    @Mock
    private OccMapper occMapper;

    private OccRecursiveServiceImpl service;

    @BeforeEach
    void setUp() {
        service = new OccRecursiveServiceImpl(occMapper);
    }

    @Test
    void collectDrawingNosReturnsEmptyWhenParamsMissing() {
        assertThat(service.collectDrawingNos(null)).isEmpty();
        assertThat(service.collectDrawingNos(Collections.emptyMap())).isEmpty();
    }

    @Test
    void collectDrawingNosReturnsEmptyWhenOccNotFound() {
        when(occMapper.find(any())).thenReturn(Collections.emptyList());

        Map<String, Object> params = new HashMap<>();
        params.put(OccConstants.PARAM_BL_OBJECT_UUID, "missing");

        assertThat(service.collectDrawingNos(params)).isEmpty();
    }

    @Test
    void collectDrawingNosReturnsEmptyWhenParentIsNotConnectCi() {
        OccEntity start = occ("occ-start", "plain-parent", "普通项", "AE8CIRevision", null);
        OccEntity parent = occ("plain-parent", null, "普通项", "AE8CIRevision", null);
        stubFind(start, parent);

        Map<String, Object> params = new HashMap<>();
        params.put(OccConstants.PARAM_BL_OBJECT_UUID, "occ-start");

        assertThat(service.collectDrawingNos(params)).isEmpty();
    }

    @Test
    void collectDrawingNosRecursesUntilPartRevision() {
        OccEntity start = occ("occ-start", "ci-root", "结构", "AE8Occurrence", null);
        OccEntity ciRoot = occ("ci-root", null, OccConstants.AE8_TYPE_CONNECT_CI,
                OccConstants.OBJECT_TYPE_CI_REVISION, null);
        OccEntity partA = occ("part-a", "ci-root", "零件", OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-A");
        OccEntity ciChild = occ("ci-child", "ci-root", OccConstants.AE8_TYPE_CONNECT_CI,
                OccConstants.OBJECT_TYPE_CI_REVISION, null);
        OccEntity partB = occ("part-b", "ci-child", "零件", OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-B");
        OccEntity other = occ("other", "ci-root", "目录", "AE8Folder", null);
        OccEntity partC = occ("part-c", "other", "零件", OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-C");
        stubFind(start, ciRoot, partA, ciChild, partB, other, partC);

        Map<String, Object> params = new HashMap<>();
        params.put(OccConstants.PARAM_BL_OBJECT_UUID, "occ-start");

        assertThat(service.collectDrawingNos(params)).containsExactly("DWG-A", "DWG-B", "DWG-C");
    }

    @Test
    void collectDrawingNosStopsOnCycle() {
        OccEntity start = occ("occ-start", "ci-root", "结构", "AE8Occurrence", null);
        OccEntity ciRoot = occ("ci-root", "part-loop", OccConstants.AE8_TYPE_CONNECT_CI,
                OccConstants.OBJECT_TYPE_CI_REVISION, null);
        OccEntity partLoop = occ("part-loop", "ci-root", "零件", OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-LOOP");
        stubFind(start, ciRoot, partLoop);

        Map<String, Object> params = new HashMap<>();
        params.put(OccConstants.PARAM_BL_OBJECT_UUID, "occ-start");

        assertThat(service.collectDrawingNos(params)).containsExactly("DWG-LOOP");
    }

    private void stubFind(OccEntity... nodes) {
        List<OccEntity> all = List.of(nodes);
        when(occMapper.find(any())).thenAnswer(invocation -> {
            Map<String, Object> params = invocation.getArgument(0);
            return all.stream().filter(node -> matches(node, params)).collect(Collectors.toList());
        });
    }

    private boolean matches(OccEntity node, Map<String, Object> params) {
        if (params.containsKey(OccConstants.PARAM_BL_OBJECT_UUID)) {
            return node.getBlObjectUuid().equals(String.valueOf(params.get(OccConstants.PARAM_BL_OBJECT_UUID)));
        }
        if (params.containsKey(OccConstants.PARAM_PARENT_OBJECT_UUID)) {
            return String.valueOf(params.get(OccConstants.PARAM_PARENT_OBJECT_UUID)).equals(node.getParentObjectUuid());
        }
        return false;
    }

    private OccEntity occ(String uuid, String parent, String ae8Type, String objectType, String drawingNo) {
        return new OccEntity(uuid, parent, ae8Type, objectType, drawingNo);
    }
}
