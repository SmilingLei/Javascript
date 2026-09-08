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
        <template v-slot="{ node, data }">
          <span
            class="tree-row gridrow"
            :class="resolveRowClass(data)"
            :style="gridStyle"
            :data-code="nodeKeyOf(data)"
          >
            <span
              v-for="col in columns"
              :key="col.field"
              :class="['cell', `cell-${col.field}`]"
            >
              <span
                v-if="col.treeNode"
                class="c1"
                :style="{ paddingLeft: `${indentLeft(node)}px` }"
              >
                <span class="tw" @click.stop="toggleExpand(node)">{{ expandIcon(node) }}</span>
                <slot :name="slotName(col)" :node="node" :data="data">
                  <render-cell v-if="col.render" :render="col.render" :scope="{ node, data }" />
                  <span v-else class="name">{{ formatCell(data, col.field) }}</span>
                </slot>
              </span>
              <slot v-else :name="slotName(col)" :node="node" :data="data">
                <render-cell v-if="col.render" :render="col.render" :scope="{ node, data }" />
                <span v-else>{{ formatCell(data, col.field) }}</span>
              </slot>
            </span>
          </span>
        </template>
      </el-tree>
    </div>
  </div>
</template>

<script>
/**
 * 公共 el-tree 封装（Vue 2.x + Element UI）
 * 按列渲染树节点，左右对比树可复用。
 */
const ROW_MARK_CLASS = ['d-add', 'd-del', 'd-mov', 'd-chg', 'd-rev', 'd-rep', 'is-sel', 'is-linked']

const RenderCell = {
  name: 'RenderCell',
  functional: true,
  props: {
    render: Function,
    scope: Object
  },
  render: (h, { props }) => props.render(h, props.scope)
}

export default {
  name: 'ElTree',
  components: { RenderCell },
  props: {
    data: {
      type: Array,
      default: () => []
    },
    columns: {
      type: Array,
      default: () => []
    },
    nodeKey: {
      type: String,
      default: 'id'
    },
    treeProps: {
      type: Object,
      default: () => ({})
    },
    expandedKeys: {
      type: Array,
      default: () => []
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
    mergedProps() {
      return {
        children: 'children',
        label: 'name',
        isLeaf: 'isLeaf',
        ...this.treeProps
      }
    },
    gridStyle() {
      const cols = (this.columns || []).map((col) => {
        if (col.width) return `${col.width}px`
        if (col.minWidth) return `minmax(${col.minWidth}px, 1fr)`
        return '1fr'
      })
      return { gridTemplateColumns: cols.join(' ') }
    }
  },
  watch: {
    expandedKeys: {
      handler() {
        this.$nextTick(() => {
          this.applyExpandedKeys()
          this.syncContentClass()
        })
      },
      deep: true
    },
    currentKey(key) {
      this.$refs.tree?.setCurrentKey(key || null)
      this.$nextTick(() => this.syncContentClass())
    },
    data: {
      handler() {
        this.$nextTick(() => this.syncContentClass())
      },
      deep: true
    }
  },
  updated() {
    this.syncContentClass()
  },
  methods: {
    getTree() {
      return this.$refs.tree
    },
    getNode(key) {
      return this.$refs.tree?.getNode(key) ?? null
    },
    hasNode(key) {
      return Boolean(this.getNode(key))
    },
    nodeKeyOf(data) {
      return data?.[this.nodeKey]
    },
    setCurrentKey(key) {
      this.$refs.tree?.setCurrentKey(key || null)
    },
    toggleExpand(node) {
      if (!node || node.isLeaf) return
      node.expanded = !node.expanded
    },
    expandIcon(node) {
      if (!node || node.isLeaf) return '·'
      return node.expanded ? '▼' : '▶'
    },
    indentLeft(node) {
      return ((node?.level || 1) - 1) * this.indent
    },
    slotName(col) {
      return col.slots?.default || col.field
    },
    formatCell(row, field) {
      if (!row || !field) return ''
      const val = row[field]
      return val == null || val === '' ? '' : val
    },
    resolveRowClass(data) {
      return typeof this.rowClassName === 'function'
        ? this.rowClassName(data)
        : (this.rowClassName || '')
    },
    applyExpandedKeys(keys = this.expandedKeys) {
      const map = this.$refs.tree?.store?.nodesMap
      if (!map) return
      const opened = new Set(keys || [])
      Object.entries(map).forEach(([key, node]) => {
        if (!node.isLeaf) node.expanded = opened.has(key)
      })
    },
    expandAll(expand = true) {
      const map = this.$refs.tree?.store?.nodesMap
      if (!map) return
      Object.values(map).forEach((node) => {
        if (!node.isLeaf) node.expanded = expand
      })
    },
    setExpandedKeys(keys) {
      this.applyExpandedKeys(keys)
    },
    scrollTo(top) {
      if (this.$refs.wrap) this.$refs.wrap.scrollTop = top
    },
    getScrollEl() {
      return this.$refs.wrap
    },
    scrollToKey(key) {
      const node = this.getNode(key)
      if (!node) return false
      this.expandParent(node)
      this.setCurrentKey(key)
      this.$nextTick(() => {
        const el = this.$refs.wrap?.querySelector(`[data-code="${key}"]`)
        el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      })
      return true
    },
    expandParent(node) {
      let parent = node?.parent
      while (parent && parent.level > 0) {
        parent.expanded = true
        parent = parent.parent
      }
    },
    syncContentClass() {
      if (!this.$el) return
      this.$el.querySelectorAll('.tree-row').forEach((row) => {
        const content = row.closest('.el-tree-node__content')
        if (!content) return
        content.classList.remove(...ROW_MARK_CLASS)
        const marks = [...row.classList].filter((cls) => ROW_MARK_CLASS.includes(cls))
        if (marks.length) content.classList.add(...marks)
      })
    },
    onNodeClick(data, node, component) {
      this.$emit('node-click', { data, node, component })
    },
    onScroll({ target }) {
      const { scrollTop, scrollHeight, clientHeight } = target
      this.$emit('scroll', {
        scrollTop,
        scrollHeight,
        bodyHeight: clientHeight,
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
