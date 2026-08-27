package com.ae8.occ.service.impl;

import com.ae8.occ.constant.OccConstants;
import com.ae8.occ.entity.OccEntity;
import com.ae8.occ.mapper.OccMapper;
import com.ae8.occ.service.OccRecursiveService;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class OccRecursiveServiceImpl implements OccRecursiveService {

    private final OccMapper occMapper;

    public OccRecursiveServiceImpl(OccMapper occMapper) {
        this.occMapper = occMapper;
    }

    @Override
    public List<String> collectDrawingNos(Map<String, Object> params) {
        List<String> result = new ArrayList<>();
        if (params == null || params.isEmpty()) {
            return result;
        }

        List<OccEntity> occNodes = occMapper.find(params);
        if (occNodes.isEmpty()) {
            return result;
        }

        Set<String> visited = new HashSet<>();
        for (OccEntity occ : occNodes) {
            walkFromOccNode(occ, result, visited);
        }
        return result;
    }

    /**
     * 取当前 OCC 的 parent_object_uuid，再查询父节点；
     * 仅当父节点为「连接构型项 + AE8CIRevision」时，取其子节点 List 并递归。
     */
    private void walkFromOccNode(OccEntity occ, List<String> result, Set<String> visited) {
        if (occ == null || !StringUtils.hasText(occ.getParentObjectUuid())) {
            return;
        }

        Map<String, Object> parentParams = new HashMap<>();
        parentParams.put(OccConstants.PARAM_BL_OBJECT_UUID, occ.getParentObjectUuid());
        List<OccEntity> parents = occMapper.find(parentParams);

        for (OccEntity parent : parents) {
            if (!isConnectCiRevision(parent)) {
                continue;
            }
            List<String> childUuids = listChildObjectUuids(parent.getBlObjectUuid());
            for (String childUuid : childUuids) {
                recurseUntilPartRevision(childUuid, result, visited);
            }
        }
    }

    /**
     * 按 parent_object_uuid 查询该节点下所有子 OCC，返回 bl_object_uuid 列表。
     */
    private List<String> listChildObjectUuids(String parentObjectUuid) {
        Map<String, Object> childParams = new HashMap<>();
        childParams.put(OccConstants.PARAM_PARENT_OBJECT_UUID, parentObjectUuid);
        List<OccEntity> children = occMapper.find(childParams);
        List<String> uuids = new ArrayList<>();
        for (OccEntity child : children) {
            if (child != null && StringUtils.hasText(child.getBlObjectUuid())) {
                uuids.add(child.getBlObjectUuid());
            }
        }
        return uuids;
    }

    /**
     * 按 bl_object_uuid 查询节点；若为 AE8PartRevision 则收集图号，否则继续向下递归。
     */
    private void recurseUntilPartRevision(String blObjectUuid, List<String> result, Set<String> visited) {
        if (!StringUtils.hasText(blObjectUuid) || !visited.add(blObjectUuid)) {
            return;
        }

        Map<String, Object> nodeParams = new HashMap<>();
        nodeParams.put(OccConstants.PARAM_BL_OBJECT_UUID, blObjectUuid);
        List<OccEntity> nodes = occMapper.find(nodeParams);
        if (nodes.isEmpty()) {
            return;
        }

        for (OccEntity node : nodes) {
            if (isPartRevision(node)) {
                if (StringUtils.hasText(node.getAe8DrawingNo())) {
                    result.add(node.getAe8DrawingNo());
                }
                continue;
            }
            List<String> childUuids = listChildObjectUuids(node.getBlObjectUuid());
            for (String childUuid : childUuids) {
                recurseUntilPartRevision(childUuid, result, visited);
            }
        }
    }

    private boolean isConnectCiRevision(OccEntity node) {
        return node != null
                && OccConstants.AE8_TYPE_CONNECT_CI.equals(node.getAe8Type())
                && OccConstants.OBJECT_TYPE_CI_REVISION.equals(node.getBlObjectType());
    }

    private boolean isPartRevision(OccEntity node) {
        return node != null && OccConstants.OBJECT_TYPE_PART_REVISION.equals(node.getBlObjectType());
    }
}
