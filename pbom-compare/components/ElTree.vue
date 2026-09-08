<template>
  <div class="c-el-tree">
    <div v-if="columns.length" class="c-el-tree__header gridrow" :style="gridStyle">
      <span v-for="col in columns" :key="col.field || col.title">{{ col.title }}</span>
    </div>
    <div ref="wrap" class="c-el-tree__body" @scroll="onScroll">
      <el-tree
        ref="tree"
        :data="data"
        :props="mergedProps"
        :node-key="nodeKey"
        :default-expanded-keys="expandedKeys"
        :current-node-key="currentKey"
        :expand-on-click-node="false"
        :highlight-current="highlightCurrent"
        :empty-text="emptyText"
        :indent="0"
        @node-click="onNodeClick"
        @node-expand="$emit('node-expand', $event)"
        @node-collapse="$emit('node-collapse', $event)"
      >
        <span
          slot-scope="scope"
          class="tree-row gridrow"
          :class="resolveRowClass(scope.data)"
          :style="gridStyle"
          :data-code="scope.data[nodeKey]"
        >
          <span
            v-for="col in columns"
            :key="col.field"
            :class="['cell', 'cell-' + col.field]"
          >
            <span v-if="col.treeNode" class="c1" :style="{ paddingLeft: indentLeft(scope.node) + 'px' }">
              <span class="tw" @click.stop="toggleExpand(scope.node)">{{ expandIcon(scope.node) }}</span>
              <slot :name="slotName(col)" v-bind="scope">
                <span class="name">{{ scope.data[col.field] }}</span>
              </slot>
            </span>
            <slot v-else :name="slotName(col)" v-bind="scope">
              {{ formatCell(scope.data, col.field) }}
            </slot>
          </span>
        </span>
      </el-tree>
    </div>
  </div>
</template>

<script>
/**
 * 公共 el-tree 封装（Vue 2.x + Element UI）
 * 按列渲染树节点，左右对比树可复用；对外暴露展开、定位、滚动方法。
 */
export default {
  name: 'ElTree',
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
    nodeKey: {
      type: String,
      default: 'id'
    },
    props: {
      type: Object,
      default: function () {
        return {}
      }
    },
    expandedKeys: {
      type: Array,
      default: function () {
        return []
      }
    },
    currentKey: {
      type: [String, Number],
      default: null
    },
    highlightCurrent: {
      type: Boolean,
      default: true
    },
    emptyText: {
      type: String,
      default: '暂无数据'
    },
    indent: {
      type: Number,
      default: 16
    },
    rowClassName: {
      type: [String, Function],
      default: ''
    }
  },
  computed: {
    mergedProps: function () {
      return Object.assign(
        { children: 'children', label: 'name', isLeaf: 'isLeaf' },
        this.props
      )
    },
    gridStyle: function () {
      var cols = (this.columns || []).map(function (c) {
        if (c.width) return c.width + 'px'
        if (c.minWidth) return 'minmax(' + c.minWidth + 'px, 1fr)'
        return '1fr'
      })
      return { gridTemplateColumns: cols.join(' ') }
    }
  },
  watch: {
    expandedKeys: {
      handler: function () {
        var self = this
        this.$nextTick(function () {
          self.applyExpandedKeys()
          self.syncContentClass()
        })
      },
      deep: true
    },
    currentKey: function (key) {
      if (this.$refs.tree) this.$refs.tree.setCurrentKey(key || null)
      var self = this
      this.$nextTick(function () { self.syncContentClass() })
    },
    data: {
      handler: function () {
        var self = this
        this.$nextTick(function () { self.syncContentClass() })
      },
      deep: true
    }
  },
  updated: function () {
    this.syncContentClass()
  },
  methods: {
    getTree: function () {
      return this.$refs.tree
    },
    getNode: function (key) {
      return this.$refs.tree ? this.$refs.tree.getNode(key) : null
    },
    hasNode: function (key) {
      return !!this.getNode(key)
    },
    setCurrentKey: function (key) {
      if (this.$refs.tree) this.$refs.tree.setCurrentKey(key || null)
    },
    toggleExpand: function (node) {
      if (!node || node.isLeaf) return
      node.expanded = !node.expanded
    },
    expandIcon: function (node) {
      if (!node || node.isLeaf) return '·'
      return node.expanded ? '▼' : '▶'
    },
    indentLeft: function (node) {
      return ((node && node.level ? node.level : 1) - 1) * this.indent
    },
    slotName: function (col) {
      return (col.slots && col.slots.default) || col.field
    },
    formatCell: function (row, field) {
      if (!row || !field) return ''
      var val = row[field]
      return val === undefined || val === null || val === '' ? '' : val
    },
    resolveRowClass: function (data) {
      if (typeof this.rowClassName === 'function') return this.rowClassName(data)
      return this.rowClassName || ''
    },
    applyExpandedKeys: function () {
      var tree = this.$refs.tree
      if (!tree || !tree.store) return
      var map = tree.store.nodesMap || {}
      var set = {}
      ;(this.expandedKeys || []).forEach(function (k) { set[k] = true })
      Object.keys(map).forEach(function (k) {
        if (!map[k].isLeaf) map[k].expanded = !!set[k]
      })
    },
    expandAll: function (expand) {
      var tree = this.$refs.tree
      if (!tree || !tree.store) return
      var map = tree.store.nodesMap || {}
      var open = expand !== false
      Object.keys(map).forEach(function (k) {
        if (!map[k].isLeaf) map[k].expanded = open
      })
    },
    setExpandedKeys: function (keys) {
      this.applyExpandedKeys()
      if (keys) {
        var tree = this.$refs.tree
        if (!tree || !tree.store) return
        var map = tree.store.nodesMap || {}
        var set = {}
        keys.forEach(function (k) { set[k] = true })
        Object.keys(map).forEach(function (k) {
          if (!map[k].isLeaf) map[k].expanded = !!set[k]
        })
      }
    },
    scrollTo: function (top) {
      if (this.$refs.wrap) this.$refs.wrap.scrollTop = top
    },
    getScrollEl: function () {
      return this.$refs.wrap
    },
    scrollToKey: function (key) {
      var self = this
      var node = this.getNode(key)
      if (!node) return false
      this.expandParent(node)
      this.setCurrentKey(key)
      this.$nextTick(function () {
        var el = self.$refs.wrap && self.$refs.wrap.querySelector('[data-code="' + key + '"]')
        if (el && el.scrollIntoView) el.scrollIntoView({ block: 'center', behavior: 'smooth' })
      })
      return true
    },
    expandParent: function (node) {
      var p = node && node.parent
      while (p && p.level > 0) {
        p.expanded = true
        p = p.parent
      }
    },
    syncContentClass: function () {
      if (!this.$el) return
      var rows = this.$el.querySelectorAll('.tree-row')
      Array.prototype.forEach.call(rows, function (row) {
        var content = row.parentNode
        while (content && content.className && String(content.className).indexOf('el-tree-node__content') === -1) {
          content = content.parentNode
        }
        if (!content || !content.classList) return
        ;['d-add', 'd-del', 'd-mov', 'd-chg', 'd-rev', 'd-rep', 'is-sel', 'is-linked'].forEach(function (c) {
          content.classList.remove(c)
        })
        String(row.className).split(/\s+/).forEach(function (c) {
          if (/^(d-add|d-del|d-mov|d-chg|d-rev|d-rep|is-sel|is-linked)$/.test(c)) content.classList.add(c)
        })
      })
    },
    onNodeClick: function (data, node, comp) {
      this.$emit('node-click', { data: data, node: node, component: comp })
    },
    onScroll: function (e) {
      var el = e.target
      this.$emit('scroll', {
        scrollTop: el.scrollTop,
        scrollHeight: el.scrollHeight,
        bodyHeight: el.clientHeight,
        isY: true
      })
    }
  }
}
</script>

<style scoped>
.c-el-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.c-el-tree__header {
  background: #fffdf8;
  border-bottom: 1.5px solid #1c2430;
  font-size: 11px;
  color: #5a6675;
  font-weight: 700;
  flex-shrink: 0;
}
.c-el-tree__header span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.c-el-tree__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.gridrow {
  display: grid;
  align-items: center;
  gap: 8px;
  padding: 2px 10px;
}
.tree-row {
  width: 100%;
  white-space: nowrap;
}
.cell {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
}
.c1 {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}
.tw {
  width: 14px;
  text-align: center;
  color: #5a6675;
  font-size: 10px;
  flex-shrink: 0;
  user-select: none;
  cursor: pointer;
}
.name {
  overflow: hidden;
  text-overflow: ellipsis;
}

.c-el-tree >>> .el-tree {
  background: transparent;
}
.c-el-tree >>> .el-tree-node__content {
  height: 28px;
  padding-left: 0 !important;
  border-left: 3px solid transparent;
}
.c-el-tree >>> .el-tree-node__content:hover {
  background: rgba(28, 36, 48, 0.05);
}
.c-el-tree >>> .el-tree-node__expand-icon {
  display: none;
}
.c-el-tree >>> .el-tree-node__label {
  width: 100%;
  overflow: visible;
}
.c-el-tree >>> .el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content {
  background: transparent;
}
</style>
