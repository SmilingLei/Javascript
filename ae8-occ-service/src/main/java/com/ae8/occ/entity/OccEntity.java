package com.ae8.occ.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "occ")
public class OccEntity {

    @Id
    @Column(name = "bl_object_uuid", nullable = false, length = 64)
    private String blObjectUuid;

    @Column(name = "parent_object_uuid", length = 64)
    private String parentObjectUuid;

    @Column(name = "ae8_type", length = 128)
    private String ae8Type;

    @Column(name = "bl_object_type", length = 64)
    private String blObjectType;

    @Column(name = "ae8_drawing_no", length = 128)
    private String ae8DrawingNo;

    public OccEntity() {
    }

    public OccEntity(String blObjectUuid, String parentObjectUuid, String ae8Type,
                     String blObjectType, String ae8DrawingNo) {
        this.blObjectUuid = blObjectUuid;
        this.parentObjectUuid = parentObjectUuid;
        this.ae8Type = ae8Type;
        this.blObjectType = blObjectType;
        this.ae8DrawingNo = ae8DrawingNo;
    }

    public String getBlObjectUuid() {
        return blObjectUuid;
    }

    public void setBlObjectUuid(String blObjectUuid) {
        this.blObjectUuid = blObjectUuid;
    }

    public String getParentObjectUuid() {
        return parentObjectUuid;
    }

    public void setParentObjectUuid(String parentObjectUuid) {
        this.parentObjectUuid = parentObjectUuid;
    }

    public String getAe8Type() {
        return ae8Type;
    }

    public void setAe8Type(String ae8Type) {
        this.ae8Type = ae8Type;
    }

    public String getBlObjectType() {
        return blObjectType;
    }

    public void setBlObjectType(String blObjectType) {
        this.blObjectType = blObjectType;
    }

    public String getAe8DrawingNo() {
        return ae8DrawingNo;
    }

    public void setAe8DrawingNo(String ae8DrawingNo) {
        this.ae8DrawingNo = ae8DrawingNo;
    }
}
