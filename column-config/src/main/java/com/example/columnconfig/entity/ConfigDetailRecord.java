package com.example.columnconfig.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

/**
 * 用户列配置操作流水，不参与读列和保存校验。
 */
@Entity
@Table(name = "config_detail_record")
public class ConfigDetailRecord {

    public static final String ACTION_SAVE = "SAVE";
    public static final String ACTION_UPDATE = "UPDATE";

    @Id
    @Column(name = "C_UUID", length = 64, nullable = false)
    private String uuid;

    @Column(name = "C_owning_user", length = 64, nullable = false)
    private String owningUser;

    @Column(name = "C_module_mark", length = 64, nullable = false)
    private String moduleMark;

    @Column(name = "C_configColumn_id", length = 64)
    private String configColumnId;

    @Column(name = "C_action", length = 32, nullable = false)
    private String action;

    @Lob
    @Column(name = "C_content")
    private String content;

    @Column(name = "C_create_time", nullable = false)
    private LocalDateTime createTime;

    @PrePersist
    public void prePersist() {
        if (createTime == null) {
            createTime = LocalDateTime.now();
        }
    }

    public String getUuid() {
        return uuid;
    }

    public void setUuid(String uuid) {
        this.uuid = uuid;
    }

    public String getOwningUser() {
        return owningUser;
    }

    public void setOwningUser(String owningUser) {
        this.owningUser = owningUser;
    }

    public String getModuleMark() {
        return moduleMark;
    }

    public void setModuleMark(String moduleMark) {
        this.moduleMark = moduleMark;
    }

    public String getConfigColumnId() {
        return configColumnId;
    }

    public void setConfigColumnId(String configColumnId) {
        this.configColumnId = configColumnId;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }
}
