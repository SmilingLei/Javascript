<template>
  <vxe-table
    ref="xTable"
    class="c-vxe-table"
    v-bind="tableBind"
        v-on="$listeners"
  >
    <vxe-column
      v-for="col in innerColumns"
      :key="col._key"
      v-bind="col.bind"
    >
      <template v-if="col.defaultSlot" #default="scope">
        <slot :name="col.defaultSlot" v-bind="scope">
          <span>{{ formatCell(scope.row, col.bind.field) }}</span>
        </slot>
      </template>
      <template v-if="col.headerSlot" #header="scope">
        <slot :name="col.headerSlot" v-bind="scope">
          <span>{{ col.bind.title }}</span>
        </slot>
      </template>
    </vxe-column>
    <slot />
  </vxe-table>
</template>

<script>
/**
 * 公共 vxe-table 封装（Vue 2.x）
 * 统一列配置、树表、插槽转发与常用方法代理，页面侧只关心数据和列定义。
 */
const PROXY_METHODS = [
  'getTableData',
  'getRowById',
  'getCurrentRecord',
  'setCurrentRow',
  'clearCurrentRow',
  'scrollTo',
  'scrollToRow',
  'setTreeExpand',
  'setAllTreeExpand',
  'toggleTreeExpand',
  'clearTreeExpand',
  'getTreeExpandRecords',
  'recalculate',
  'refreshColumn',
  'reloadData',
  'loadData',
  'updateData',
  'getScroll'
]

export default {
  name: 'VxeTable',
  inheritAttrs: false,
  props: {
    data: {
      type: Array,
      default: function () {
        return []
      }
    },
    columns: {
      type: Array,
      default: function () {
        return []
      }
    },
    height: {
      type: [String, Number],
      default: undefined
    },
    maxHeight: {
      type: [String, Number],
      default: undefined
    },
    loading: {
      type: Boolean,
      default: false
    },
    border: {
      type: [Boolean, String],
      default: true
    },
    stripe: {
      type: Boolean,
      default: false
    },
    showOverflow: {
      type: [Boolean, String],
      default: 'tooltip'
    },
    showHeaderOverflow: {
      type: [Boolean, String],
      default: 'tooltip'
    },
    emptyText: {
      type: String,
      default: '暂无数据'
    },
    autoResize: {
      type: Boolean,
      default: true
    },
    treeConfig: {
      type: [Boolean, Object],
      default: null
    },
    rowConfig: {
      type: Object,
      default: function () {
        return {}
      }
    },
    columnConfig: {
      type: Object,
      default: function () {
        return { resizable: true }
      }
    },
    rowClassName: {
      type: [String, Function],
      default: undefined
    },
    headerRowClassName: {
      type: [String, Function],
      default: undefined
    },
    spanMethod: {
      type: Function,
      default: undefined
    },
    rowId: {
      type: String,
      default: 'id'
    }
  },
  computed: {
    innerColumns: function () {
      return (this.columns || []).map(function (col, idx) {
        var bind = Object.assign({}, col)
        var slots = bind.slots || {}
        delete bind.slots
        return {
          _key: bind.field || bind.type || bind.title || String(idx),
          bind: bind,
          defaultSlot: slots.default || null,
          headerSlot: slots.header || null
        }
      })
    },
    mergedRowConfig: function () {
      return Object.assign(
        { keyField: this.rowId, isHover: true, isCurrent: true },
        this.rowConfig
      )
    },
    mergedTreeConfig: function () {
      if (!this.treeConfig) return undefined
      var conf = this.treeConfig === true ? {} : this.treeConfig
      return Object.assign(
        {
          children: 'children',
          rowField: this.rowId,
          reserve: true,
          accordion: false,
          indent: 16
        },
        conf
      )
    },
    tableBind: function () {
      var bind = Object.assign({}, this.$attrs, {
        data: this.data,
        height: this.height,
        maxHeight: this.maxHeight,
        loading: this.loading,
        border: this.border,
        stripe: this.stripe,
        showOverflow: this.showOverflow,
        showHeaderOverflow: this.showHeaderOverflow,
        emptyText: this.emptyText,
        autoResize: this.autoResize,
        rowConfig: this.mergedRowConfig,
        columnConfig: this.columnConfig,
        rowClassName: this.rowClassName,
        headerRowClassName: this.headerRowClassName,
        spanMethod: this.spanMethod,
        rowId: this.rowId
      })
      if (this.mergedTreeConfig) {
        bind.treeConfig = this.mergedTreeConfig
      }
      return bind
    },
  },
  created: function () {
    var self = this
    PROXY_METHODS.forEach(function (name) {
      self[name] = function () {
        var table = self.$refs.xTable
        if (!table || typeof table[name] !== 'function') return
        return table[name].apply(table, arguments)
      }
    })
  },
  methods: {
    getTable: function () {
      return this.$refs.xTable
    },
    formatCell: function (row, field) {
      if (!row || !field) return ''
      var val = row[field]
      return val === undefined || val === null || val === '' ? '' : val
    }
  }
}
</script>

<style scoped>
.c-vxe-table {
  width: 100%;
}
</style>
