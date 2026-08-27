package com.ae8.occ.controller;

import com.ae8.occ.constant.OccConstants;
import com.ae8.occ.entity.OccEntity;
import com.ae8.occ.repository.OccRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.hamcrest.Matchers.containsInAnyOrder;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class OccRecursiveControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private OccRepository occRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        occRepository.deleteAll();
        occRepository.save(new OccEntity("ci-root", null, OccConstants.AE8_TYPE_CONNECT_CI,
                OccConstants.OBJECT_TYPE_CI_REVISION, null));
        occRepository.save(new OccEntity("occ-start", "ci-root", "结构", "AE8Occurrence", null));
        occRepository.save(new OccEntity("part-a", "ci-root", "零件",
                OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-A"));
        occRepository.save(new OccEntity("ci-child", "ci-root", OccConstants.AE8_TYPE_CONNECT_CI,
                OccConstants.OBJECT_TYPE_CI_REVISION, null));
        occRepository.save(new OccEntity("part-b", "ci-child", "零件",
                OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-B"));
        occRepository.save(new OccEntity("other", "ci-root", "目录", "AE8Folder", null));
        occRepository.save(new OccEntity("part-c", "other", "零件",
                OccConstants.OBJECT_TYPE_PART_REVISION, "DWG-C"));
        occRepository.save(new OccEntity("plain-parent", null, "普通项",
                OccConstants.OBJECT_TYPE_CI_REVISION, null));
        occRepository.save(new OccEntity("occ-plain", "plain-parent", "结构", "AE8Occurrence", null));
    }

    @Test
    void collectPartDrawingNosRejectsBlankUuid() throws Exception {
        mockMvc.perform(post("/api/occ/part-drawing-nos")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("bl_object_uuid", "  "))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(-1))
                .andExpect(jsonPath("$.message").value("bl_object_uuid 不能为空"));
    }

    @Test
    void collectPartDrawingNosReturnsDrawingNosFromConnectCiTree() throws Exception {
        mockMvc.perform(post("/api/occ/part-drawing-nos")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("bl_object_uuid", "occ-start"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data", hasSize(3)))
                .andExpect(jsonPath("$.data", containsInAnyOrder("DWG-A", "DWG-B", "DWG-C")));
    }

    @Test
    void collectPartDrawingNosReturnsEmptyWhenParentIsNotConnectCi() throws Exception {
        mockMvc.perform(post("/api/occ/part-drawing-nos")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("bl_object_uuid", "occ-plain"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data", hasSize(0)));
    }
}
