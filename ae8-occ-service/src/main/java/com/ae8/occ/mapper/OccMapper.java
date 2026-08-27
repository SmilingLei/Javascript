package com.ae8.occ.mapper;

import com.ae8.occ.entity.OccEntity;

import java.util.List;
import java.util.Map;

/**
 * OCC 动态查询，入参为前端传递的 Map。
 */
public interface OccMapper {

    /**
     * 按 Map 条件动态查询 OCC 节点。
     * 支持键：bl_object_uuid、parent_object_uuid、ae8_type、bl_object_type、ae8_drawingNo。
     */
    List<OccEntity> find(Map<String, Object> params);
}
