package com.ae8.occ.service;

import java.util.List;
import java.util.Map;

public interface OccRecursiveService {

    /**
     * 从 OCC 节点出发，沿父节点判定连接构型项后递归收集零件图号。
     *
     * @param params 前端传递的查询 Map，需包含 bl_object_uuid
     * @return ae8_drawingNo 列表
     */
    List<String> collectDrawingNos(Map<String, Object> params);
}
