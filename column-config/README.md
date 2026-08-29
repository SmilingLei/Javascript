# 列配置（Spring Boot + JPA）

贯彻表字段是否可显示、可配置由实体上的 `@ColumnMeta` 声明。启动时（或第一次请求时）扫描实体，按「模块 → 字段列表」放入内存。

用户方案写入 `config_column` + `config_column_detail`；`config_detail_record` 只追加操作流水，不参与读列和保存校验。

## 接口

均需请求头 `X-User-Id`。

- `GET /api/column-config/fields?moduleMark=implement_table`
- `GET /api/column-config/table-columns?moduleMark=implement_table`
- `POST /api/column-config/save`

```json
{
  "moduleMark": "implement_table",
  "configName": "默认方案",
  "columns": [
    { "columnName": "fileName", "width": 160 },
    { "columnName": "filePath", "width": 240 }
  ]
}
```

## 运行

```bash
cd column-config
mvn test
mvn spring-boot:run
```
