<template>
  <div class="pbom-page">
    <header class="pbom-header">
      <div class="logo">PBOM 对比</div>
      <div class="snapshot-chip">
        基准快照：<b>SNAP-CN-2026-0091</b> · 下发于 2026-08-10 14:32 · 来源：系统A下发工艺系统（不可变）
      </div>
      <div class="vsel">
        <span>基准版本</span>
        <el-select v-model="selBase" size="mini" disabled>
          <el-option
            v-for="opt in baseOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <span class="lock">🔒 锁定</span>
      </div>
      <div class="vsel">
        <span>对比版本</span>
        <el-select v-model="selTgt" size="mini">
          <el-option
            v-for="opt in targetOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>
      <el-button
        v-for="btn in headerActions"
        :key="btn.key"
        size="mini"
        :type="btn.type"
        :class="btn.className"
        @click="btn.handler"
      >
        {{ btn.label }}
      </el-button>
    </header>

    <div class="toolbar">
      <div class="legend">
        <span class="lg-title">图例：</span>
        <span v-for="item in legendItems" :key="item.key" class="lg">
          <i :class="`lg-${item.key}`"></i>{{ item.label }}
        </span>
      </div>
      <div class="sep"></div>
      <el-checkbox v-model="diffOnly">仅显示差异项</el-checkbox>
      <label class="type-filter">
        类型筛选
        <el-select v-model="typeFilter" size="mini" clearable placeholder="全部">
          <el-option
            v-for="opt in typeFilters"
            :key="opt.value || 'all'"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </label>
      <el-checkbox v-model="syncScroll" @change="onSyncChange">同步滚动</el-checkbox>
      <span class="hint">提示：点击任一侧树节点，另一侧自动联动定位</span>
    </div>

    <div class="stats">
      <div class="stat total">
        <span class="n">{{ stats.total }}</span>
        <span class="t">差异总计</span>
      </div>
      <div v-for="item in statItems" :key="item.key" class="stat">
        <span class="n" :style="{ color: item.color }">{{ item.count }}</span>
        <span class="t">{{ item.label }}</span>
      </div>
      <div class="stat">
        <span class="n">{{ retNodeCount }}</span>
        <span class="t">回传节点数</span>
      </div>
    </div>

    <main class="pbom-main">
      <div v-for="panel in treePanels" :key="panel.side" class="treecol">
        <div class="treehead">
          <span class="side">{{ panel.title }}</span>
          <span class="rev">{{ panel.rev }}</span>
        </div>
        <div class="tree-body">
          <el-tree-x
            :ref="panel.ref"
            :data="panel.data"
            :columns="treeColumns"
            node-key="code"
            :expanded-keys="panel.expandedKeys"
            :current-key="panel.currentKey"
            :row-class-name="panel.rowClassName"
            empty-text="暂无节点"
            @node-click="(params) => onTreeClick(params, panel.side)"
            @scroll="(params) => onTreeScroll(panel.side, params)"
          />
        </div>
      </div>
    </main>

    <div class="bottom">
      <el-tabs v-model="activeTab" class="btabs">
        <el-tab-pane label="变更明细清单" name="detail">
          <el-table :data="diffList" border size="mini" height="210" empty-text="暂无差异">
            <el-table-column label="类型" width="110">
              <template slot-scope="{ row }">
                <span class="tt" :style="{ background: ttColor[row.cls] }">{{ row.tt }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="code" label="件号" min-width="160" />
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column prop="detail" label="变更明细" min-width="280" />
            <el-table-column label="状态" width="180">
              <template slot-scope="{ row }">
                <span v-if="row.status === 'accepted'" class="st-ok">✓ 已接受</span>
                <span v-else-if="row.status === 'rejected'" class="st-no">✗ 已驳回</span>
                <span v-else class="st-wait">
                  待确认
                  <el-button size="mini" @click.stop="acceptDiff(row)">接受</el-button>
                  <el-button size="mini" @click.stop="rejectDiff(row)">驳回</el-button>
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="属性差异明细（物料 / BOMLine引用）" name="attr">
          <el-table
            :data="attrRows"
            border
            size="mini"
            height="210"
            :span-method="attrSpanMethod"
            :row-class-name="attrRowClassName"
            empty-text="暂无属性级差异"
          >
            <el-table-column label="件号" min-width="150">
              <template slot-scope="{ row }">
                <span v-if="row._group" class="agroup">{{ row.title }}</span>
                <span v-else class="mono">{{ row.code }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="属性组" min-width="140" />
            <el-table-column prop="f" label="属性字段" width="120" />
            <el-table-column label="旧值（基准快照）" min-width="140">
              <template slot-scope="{ row }">
                <span v-if="!row._group" class="old">{{ row.o }}</span>
              </template>
            </el-table-column>
            <el-table-column label="新值（回传版本）" min-width="140">
              <template slot-scope="{ row }">
                <span v-if="!row._group" class="new">{{ row.n }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="path" label="所属 BOMLine 路径" min-width="180" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="协同日志（含二次回传）" name="log">
          <div class="log-wrap">
            <div v-for="(item, idx) in logs" :key="idx" class="logline">
              <span class="lt">{{ item.t }}</span>
              <span class="badge" :class="item.badge">{{ item.tag }}</span>
              <span>{{ item.txt }}</span>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="变更影响分析" name="imp">
          <div class="imp">
            <div class="impcard">
              <h4>结构影响（波及系统）</h4>
              <ul>
                <li v-for="(n, s) in affectedSys" :key="s">{{ s }}（{{ n }} 项）</li>
              </ul>
            </div>
            <div class="impcard">
              <h4>受影响技术文件</h4>
              <ul>
                <li v-for="doc in impactDocs" :key="doc">{{ doc }}</li>
              </ul>
            </div>
            <div class="impcard">
              <h4>下游同步清单</h4>
              <ul>
                <li>ERP 物料主数据：<span class="num">3</span> 项（新增2/替换1）</li>
                <li>MES 工艺路线：<span class="num">4</span> 条需更新</li>
                <li>需重算工时：+38.5h</li>
              </ul>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-show="toastVisible" id="toast" :class="{ warn: toastWarn }" v-html="toastHtml"></div>
  </div>
</template>

<script>
import ElTree from '../components/ElTree.vue'

const REPLACE_MAP = {
  'WS10-CMB-S03-001': 'WS10-CMB-S03-001N'
}

const TT_COLOR = {
  add: '#2e7d32',
  del: '#c62828',
  mov: '#7b1fa2',
  chg: '#b28704',
  rev: '#1565c0',
  rep: '#ef6c00'
}

const STAT_META = [
  { key: 'add', label: '新增', color: TT_COLOR.add },
  { key: 'del', label: '删除', color: TT_COLOR.del },
  { key: 'mov', label: '移动', color: TT_COLOR.mov },
  { key: 'chg', label: '数量/属性变更', color: TT_COLOR.chg },
  { key: 'rev', label: '版本变更', color: TT_COLOR.rev },
  { key: 'rep', label: '替换', color: TT_COLOR.rep }
]

const DIFF_TYPE_ALIAS = {
  del: 'del',
  add: 'add',
  mov: 'mov',
  rev: 'rev',
  chg: 'chg',
  'rep-old': 'rep',
  'rep-new': 'rep'
}

const DIFF_TAG = {
  add: '＋新增',
  del: '－删除',
  mov: '⇄移动',
  rev: 'Rev↑',
  chg: '✎变更'
}

const BASE_OPTIONS = [{ label: 'Rev.B（下发快照）', value: 'revB' }]
const TARGET_OPTIONS = [
  { label: '工艺系统回传 RT-2026-0820-01', value: 'rt0820' },
  { label: 'Rev.C（升版后）', value: 'revC' }
]
const TYPE_FILTERS = [
  { label: '全部', value: '' },
  ...STAT_META.map(({ key, label }) => ({ label, value: key }))
]
const IMPACT_DOCS = [
  '燃烧室装配工艺规程 AP-CMB-012（Rev.B→C）',
  '密封环图纸 TZ-CMB-0034（作废）',
  '整体石墨密封环图纸 TZ-CMB-0034N（新编）',
  '滑油系统装配卡 AC-LUB-006（增补）'
]

const flatten = (tree) => {
  const out = []
  const walk = (nodes, parent = '', level = 0) => {
    nodes.forEach((n) => {
      out.push({ node: n, parent, level })
      if (n.children?.length) walk(n.children, n.code, level + 1)
    })
  }
  walk(tree)
  return out
}

const findNode = (tree, code) => {
  for (const n of tree) {
    if (n.code === code) return n
    if (n.children?.length) {
      const found = findNode(n.children, code)
      if (found) return found
    }
  }
  return null
}

const findParent = (tree, code, parent = '') => {
  for (const n of tree) {
    if (n.code === code) return parent
    if (n.children?.length) {
      const found = findParent(n.children, code, n.code)
      if (found !== '') return found
    }
  }
  return ''
}

const collectKeys = (tree, onlyParents = false) => {
  const keys = []
  const walk = (nodes = []) => {
    nodes.forEach((n) => {
      const hasChildren = Boolean(n.children?.length)
      if (!onlyParents || hasChildren) keys.push(n.code)
      if (hasChildren) walk(n.children)
    })
  }
  walk(tree)
  return keys
}

const keysToLevel = (tree, level) => {
  const keys = []
  const walk = (nodes = [], lv = 0) => {
    nodes.forEach((n) => {
      if (lv < level && n.children?.length) {
        keys.push(n.code)
        walk(n.children, lv + 1)
      }
    })
  }
  walk(tree)
  return keys
}

const createBaseTree = () => ([
  { code: 'WS10-ENG-0000', name: 'WS10 涡扇发动机 整机', dwg: 'ZZ-WS10-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
    { code: 'WS10-FAN-000', name: '风扇系统', dwg: 'ZP-FAN-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-FAN-R01-001', name: '风扇叶片', dwg: 'TZ-FAN-0101', qty: 24, rev: 'A', mat: 'TC4(Ti-6Al-4V)', effSer: '0101-0150', effDate: '2026-01-01', pos: 'C01～C24', children: [] },
      { code: 'WS10-FAN-C01-001', name: '风扇机匣', dwg: 'TZ-FAN-0201', qty: 1, rev: 'B', mat: 'TC4', effSer: '0101-0150', effDate: '2026-01-01', pos: 'A1', children: [] },
      { code: 'WS10-FAN-A01-001', name: '附件机匣', dwg: 'TZ-FAN-0301', qty: 1, rev: 'A', mat: 'ZL114A', effSer: '0101-0150', effDate: '2026-01-01', pos: 'B2', children: [] }
    ] },
    { code: 'WS10-CMB-000', name: '燃烧室系统', dwg: 'ZP-CMB-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-CMB-C01-001', name: '燃烧室机匣', dwg: 'TZ-CMB-0101', qty: 1, rev: 'B', mat: 'GH4169', effSer: '0101-0150', effDate: '2026-01-01', pos: 'A1', children: [] },
      { code: 'WS10-CMB-S03-001', name: '燃烧室密封环', dwg: 'TZ-CMB-0301', qty: 2, rev: 'A', mat: 'GH3030', effSer: '0101-0150', effDate: '2026-01-01', pos: ['S1', 'S2'], children: [] },
      { code: 'WS10-CMB-F01-016', name: '燃油喷嘴', dwg: 'TZ-CMB-0401', qty: 16, rev: 'B', mat: 'GH3536', effSer: '0101-0150', effDate: '2026-01-01', pos: 'P01～P16', children: [] }
    ] },
    { code: 'WS10-TUR-000', name: '涡轮系统', dwg: 'ZP-TUR-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-TUR-B01-001', name: '涡轮叶片', dwg: 'TZ-TUR-0101', qty: 72, rev: 'A', mat: 'DD6单晶', effSer: '0101-0150', effDate: '2026-01-01', pos: 'T01～T72', children: [] },
      { code: 'WS10-TUR-D01-001', name: '涡轮盘', dwg: 'TZ-TUR-0201', qty: 1, rev: 'B', mat: 'GH4169', effSer: '0101-0150', effDate: '2026-01-01', pos: 'A1', children: [] }
    ] },
    { code: 'WS10-TRN-000', name: '传动系统', dwg: 'ZP-TRN-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-TRN-S01-002', name: '传动轴', dwg: 'TZ-TRN-0102', qty: 1, rev: 'A', mat: '40CrNiMoA', effSer: '0101-0150', effDate: '2026-01-01', pos: 'A1', children: [] }
    ] },
    { code: 'WS10-LUB-000', name: '滑油系统', dwg: 'ZP-LUB-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-LUB-T01-001', name: '滑油箱', dwg: 'TZ-LUB-0101', qty: 1, rev: 'B', mat: '1Cr18Ni9Ti', effSer: '0101-0150', effDate: '2026-01-01', pos: 'L1', children: [] }
    ] }
  ] }
])

const createRetTree = () => ([
  { code: 'WS10-ENG-0000', name: 'WS10 涡扇发动机 整机', dwg: 'ZZ-WS10-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
    { code: 'WS10-FAN-000', name: '风扇系统', dwg: 'ZP-FAN-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-FAN-R01-001', name: '风扇叶片', dwg: 'TZ-FAN-0101', qty: 24, rev: 'A', mat: 'TC4(Ti-6Al-4V)', effSer: '0101-0150', effDate: '2026-01-01', pos: 'C01～C24', children: [] },
      { code: 'WS10-FAN-C01-001', name: '风扇机匣', dwg: 'TZ-FAN-0201', qty: 1, rev: 'B', mat: 'TC4', effSer: '0101-0150', effDate: '2026-01-01', pos: 'A1', children: [] }
    ] },
    { code: 'WS10-CMB-000', name: '燃烧室系统', dwg: 'ZP-CMB-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-CMB-C01-001', name: '燃烧室机匣', dwg: 'TZ-CMB-0101', qty: 1, rev: 'B', mat: 'GH4738', effSer: '0101-0150', effDate: '2026-01-01', pos: 'A1', children: [] },
      { code: 'WS10-CMB-F01-016', name: '燃油喷嘴', dwg: 'TZ-CMB-0401', qty: 20, rev: 'B', mat: 'GH3536', effSer: '0101-0180', effDate: '2026-01-01', pos: 'P01～P20', children: [] },
      { code: 'WS10-CMB-I01-001', name: '点火电嘴支架', dwg: 'TZ-CMB-0501', qty: 2, rev: 'A', mat: 'GH3030', effSer: '0101-', effDate: '2026-08-01', pos: ['12点位', '3点位'], children: [] },
      { code: 'WS10-CMB-S03-001N', name: '燃烧室密封环(整体石墨)', dwg: 'TZ-CMB-0301N', qty: 2, rev: 'A', mat: '柔性石墨', effSer: '0101-', effDate: '2026-08-01', pos: ['S1', 'S2'], children: [] }
    ] },
    { code: 'WS10-TUR-000', name: '涡轮系统', dwg: 'ZP-TUR-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-TUR-B01-001', name: '涡轮叶片', dwg: 'TZ-TUR-0101', qty: 72, rev: 'B', mat: 'DD6单晶', effSer: '0101-0150', effDate: '2026-01-01', pos: 'T01～T72', children: [] },
      { code: 'WS10-TUR-D01-001', name: '涡轮盘', dwg: 'TZ-TUR-0201', qty: 1, rev: 'B', mat: 'GH4169', effSer: '0101-0150', effDate: '2026-03-15', pos: 'A1', children: [] }
    ] },
    { code: 'WS10-TRN-000', name: '传动系统', dwg: 'ZP-TRN-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-FAN-A01-001', name: '附件机匣', dwg: 'TZ-FAN-0301', qty: 1, rev: 'A', mat: 'ZL114A', effSer: '0101-0150', effDate: '2026-01-01', pos: 'B2', children: [] }
    ] },
    { code: 'WS10-LUB-000', name: '滑油系统', dwg: 'ZP-LUB-000', qty: 1, rev: 'B', mat: '—', effSer: '—', effDate: '—', children: [
      { code: 'WS10-LUB-T01-001', name: '滑油箱', dwg: 'TZ-LUB-0101', qty: 1, rev: 'B', mat: '1Cr18Ni9Ti', effSer: '0101-0150', effDate: '2026-01-01', pos: 'L1', children: [] },
      { code: 'WS10-LUB-P01-001', name: '滑油泵', dwg: 'TZ-LUB-0201', qty: 1, rev: 'A', mat: 'ZL114A', effSer: '0101-', effDate: '2026-08-01', pos: 'L2', children: [] }
    ] }
  ] }
])

export default {
  name: 'PbomCompare',
  components: { ElTreeX: ElTree },
  data() {
    return {
      selBase: 'revB',
      selTgt: 'rt0820',
      diffOnly: false,
      typeFilter: '',
      syncScroll: false,
      scrollLock: false,
      activeTab: 'detail',
      selCode: null,
      clickSide: null,
      linkedCode: null,
      rowClsTick: 0,
      diffDone: false,
      secondReturnCount: 0,
      toastVisible: false,
      toastWarn: false,
      toastHtml: '',
      toastTimer: null,
      ttColor: TT_COLOR,
      legendItems: STAT_META,
      typeFilters: TYPE_FILTERS,
      impactDocs: IMPACT_DOCS,
      baseOptions: BASE_OPTIONS,
      targetOptions: TARGET_OPTIONS,
      baseTree: createBaseTree(),
      retTree: createRetTree(),
      expandedL: [],
      expandedR: [],
      diffMap: {},
      diffList: [],
      logs: [
        { t: '2026-08-10 14:32', badge: 'b-info', tag: '下发', txt: '系统A下发 PBOM 基准快照 SNAP-CN-2026-0091（Rev.B）至工艺系统，快照锁定不可变' },
        { t: '2026-08-12 09:15', badge: 'b-ok', tag: '签收', txt: '工艺系统确认签收，进入工艺规程编制' },
        { t: '2026-08-18 16:40', badge: 'b-warn', tag: '驳回', txt: '工艺系统驳回 2 条 BOMLine（燃油喷嘴数量待确认），要求系统A复核' },
        { t: '2026-08-19 10:05', badge: 'b-ok', tag: '确认', txt: '系统A确认数量 16→20，通知工艺系统按新数量执行' },
        { t: '2026-08-20 11:30', badge: 'b-info', tag: '回传', txt: '工艺系统回传调整后 PBOM（RT-2026-0820-01），触发自动对比' }
      ]
    }
  },
  computed: {
    headerActions() {
      return [
        { key: 'run', label: '执行对比', type: 'warning', className: 'btn-primary', handler: this.runDiff },
        { key: 'second', label: '模拟二次回传', handler: this.simSecondReturn },
        { key: 'export', label: '导出报告', handler: this.exportReport }
      ]
    },
    currentKeyL() {
      return this.clickSide === 'L' ? this.selCode : this.linkedCode
    },
    currentKeyR() {
      return this.clickSide === 'R' ? this.selCode : this.linkedCode
    },
    treePanels() {
      return [
        {
          side: 'L',
          ref: 'treeL',
          title: '◀ 基准：下发快照',
          rev: 'SNAP-CN-2026-0091 · Rev.B · 2026-08-10',
          data: this.displayBaseTree,
          expandedKeys: this.expandedL,
          currentKey: this.currentKeyL,
          rowClassName: this.rowClassNameL
        },
        {
          side: 'R',
          ref: 'treeR',
          title: '对比：工艺系统回传',
          rev: 'RT-2026-0820-01 · 2026-08-20',
          data: this.displayRetTree,
          expandedKeys: this.expandedR,
          currentKey: this.currentKeyR,
          rowClassName: this.rowClassNameR
        }
      ]
    },
    treeColumns() {
      return [
        {
          field: 'name',
          title: '零组件名称（层级）',
          minWidth: 200,
          treeNode: true,
          render: (h, { data }) => {
            const extra = this.nameExtra(data)
            return h('span', { class: 'name-cell' }, [
              h('span', { class: 'name' }, data.name),
              extra ? h('span', { class: ['name-extra', `ex-${this.typeOf(data.code)}`] }, extra) : null
            ])
          }
        },
        {
          field: 'dwg',
          title: '图号',
          width: 116,
          render: (h, { data }) => h('span', { class: { miss: !data.dwg } }, data.dwg || '—')
        },
        { field: 'code', title: '件号', minWidth: 150 },
        {
          field: 'qty',
          title: '数量',
          width: 56,
          render: (h, { data }) => h('span', `×${data.qty}`)
        },
        {
          field: 'pos',
          title: '位置号',
          width: 98,
          render: (h, { data }) => h('span', {
            class: { miss: !data.pos },
            attrs: { title: this.posTitle(data) }
          }, this.fmtPos(data))
        },
        {
          field: 'rev',
          title: '版本',
          width: 62,
          render: (h, { data }) => h('span', { class: 'revtag' }, `Rev.${data.rev}`)
        },
        {
          field: 'diff',
          title: '差异',
          width: 88,
          render: (h, { data }) => {
            const tag = this.diffTag(data)
            return tag ? h('span', { class: ['dtag', `tag-${this.typeOf(data.code)}`] }, tag) : null
          }
        }
      ]
    },
    isFiltering() {
      return this.diffDone && (this.diffOnly || Boolean(this.typeFilter))
    },
    displayBaseTree() {
      return this.filterTree(this.baseTree)
    },
    displayRetTree() {
      return this.filterTree(this.retTree)
    },
    stats() {
      const cnt = { add: 0, del: 0, mov: 0, chg: 0, rev: 0, rep: 0 }
      this.diffList.forEach(({ cls }) => {
        if (cnt[cls] !== undefined) cnt[cls] += 1
      })
      return { total: this.diffList.length, ...cnt }
    },
    statItems() {
      return STAT_META.map((meta) => ({ ...meta, count: this.stats[meta.key] }))
    },
    retNodeCount() {
      return flatten(this.retTree).length
    },
    attrRows() {
      const mat = []
      const line = []
      this.diffList.forEach((row) => {
        (row.changes || []).forEach((change, i) => {
          const rec = {
            _id: `${row.code}-${change.f}-${i}`,
            code: row.code,
            name: row.name,
            f: change.f,
            o: change.o,
            n: change.n,
            path: findParent(this.retTree, row.code) || row.code
          }
          ;(change.g === 'mat' ? mat : line).push(rec)
        })
      })
      const rows = []
      if (mat.length) rows.push({ _id: 'g-mat', _group: true, title: '—— 物料属性 ——' }, ...mat)
      if (line.length) rows.push({ _id: 'g-line', _group: true, title: '—— BOMLine 引用属性 ——' }, ...line)
      return rows
    },
    affectedSys() {
      return this.diffList.reduce((map, { code }) => {
        const parent = findParent(this.retTree, code) || findParent(this.baseTree, code)
        if (parent) map[parent] = (map[parent] || 0) + 1
        return map
      }, {})
    }
  },
  watch: {
    displayBaseTree() {
      this.syncTreeExpand()
    },
    displayRetTree() {
      this.syncTreeExpand()
    }
  },
  mounted() {
    this.runDiff()
  },
  beforeDestroy() {
    if (this.toastTimer) clearTimeout(this.toastTimer)
  },
  methods: {
    getTreeRef(side) {
      const ref = this.$refs[`tree${side}`]
      return Array.isArray(ref) ? ref[0] : ref
    },
    typeOf(code) {
      const type = this.diffMap[code]?.type
      return DIFF_TYPE_ALIAS[type] || (type ? 'chg' : '')
    },
    nodeMatches(code) {
      if (!this.diffDone) return true
      const type = this.typeOf(code)
      if (this.diffOnly && !type) return false
      if (this.typeFilter && type !== this.typeFilter) return false
      return true
    },
    filterTree(tree) {
      const walk = (nodes) => nodes.reduce((out, n) => {
        const children = n.children?.length ? walk(n.children) : []
        if (!this.isFiltering || this.nodeMatches(n.code) || children.length) {
          out.push({ ...n, children, isLeaf: !children.length })
        }
        return out
      }, [])
      return walk(tree)
    },
    nameExtra({ code }) {
      const d = this.diffMap[code]
      if (!d) return ''
      if (d.type === 'rep-old') return `→ ${d.newCode}`
      if (d.type === 'rep-new') return `← ${d.oldCode}`
      if (d.type === 'mov') {
        return `${(d.from || '').replace('WS10-', '')} → ${(d.to || '').replace('WS10-', '')}`
      }
      return ''
    },
    diffTag(row) {
      const type = this.typeOf(row.code)
      if (DIFF_TAG[type]) return DIFF_TAG[type]
      if (type === 'rep') return this.diffMap[row.code]?.type === 'rep-old' ? '⭮旧件' : '⭮新件'
      return ''
    },
    fmtPos({ pos } = {}) {
      if (!pos) return '—'
      if (Array.isArray(pos)) {
        return pos.length <= 1 ? `${pos[0]}` : `${pos[0]} +${pos.length - 1}`
      }
      return `${pos}`
    },
    posTitle({ pos } = {}) {
      return Array.isArray(pos) && pos.length > 1 ? `全部位置号：${pos.join('、')}` : ''
    },
    rowClassNameL(data) {
      return this.buildRowClass(data, 'L')
    },
    rowClassNameR(data) {
      return this.buildRowClass(data, 'R')
    },
    buildRowClass(row, side) {
      void this.rowClsTick
      const cls = []
      const type = this.typeOf(row.code)
      if (type) cls.push(`d-${type}`)
      if (row.code === this.selCode && this.clickSide === side) cls.push('is-sel')
      if (row.code === this.linkedCode && this.clickSide !== side) cls.push('is-linked')
      return cls.join(' ')
    },
    attrRowClassName({ row }) {
      return row?._group ? 'agroup-row' : ''
    },
    attrSpanMethod({ row, columnIndex }) {
      if (row?._group) return columnIndex === 0 ? [1, 6] : [0, 0]
    },
    runDiff() {
      const diffMap = {}
      const diffList = []
      const flatB = flatten(this.baseTree)
      const flatR = flatten(this.retTree)
      const mapB = Object.fromEntries(flatB.map((r) => [r.node.code, r]))
      const mapR = Object.fromEntries(flatR.map((r) => [r.node.code, r]))

      flatB.forEach(({ node: b }) => {
        const { code } = b
        if (!mapR[code]) {
          diffMap[code] = { type: 'del' }
          return
        }
        const a = mapR[code].node
        const d = { type: '', changes: [] }
        const from = findParent(this.baseTree, code)
        const to = findParent(this.retTree, code)
        if (from !== to) {
          d.type = 'mov'
          d.from = from
          d.to = to
          diffMap[code] = d
        }
        const lineFields = [
          ['qty', '单件数量'],
          ['effSer', '有效架次'],
          ['effDate', '有效性日期']
        ]
        lineFields.forEach(([key, label]) => {
          if (b[key] !== a[key]) d.changes.push({ g: 'line', f: label, o: b[key], n: a[key] })
        })
        if (b.mat !== a.mat) d.changes.push({ g: 'mat', f: '材料', o: b.mat, n: a.mat })
        if (b.name !== a.name) d.changes.push({ g: 'mat', f: '名称', o: b.name, n: a.name })
        if (b.rev !== a.rev) {
          d.changes.push({ g: 'mat', f: '零组件版本', o: `Rev.${b.rev}`, n: `Rev.${a.rev}` })
          if (!d.type) d.type = 'rev'
        }
        if (!d.type && d.changes.length) d.type = 'chg'
        if (d.type || d.changes.length) diffMap[code] = d
      })

      flatR.forEach(({ node: a }) => {
        const { code } = a
        if (mapB[code]) return
        const oldCode = Object.keys(REPLACE_MAP).find(
          (x) => REPLACE_MAP[x] === code && diffMap[x]?.type === 'del'
        )
        if (oldCode) {
          diffMap[oldCode] = { type: 'rep-old', newCode: code }
          diffMap[code] = { type: 'rep-new', oldCode }
        } else {
          diffMap[code] = { type: 'add' }
        }
      })

      const detailOf = (d, node) => {
        const rec = { code: node.code, name: node.name, status: 'pending' }
        const builders = {
          del: () => ({ tt: '删除', cls: 'del', detail: '基准存在，回传不存在' }),
          add: () => ({ tt: '新增', cls: 'add', detail: `回传新增挂接于 ${findParent(this.retTree, node.code)}` }),
          mov: () => ({ tt: '移动', cls: 'mov', detail: `父节点 ${d.from} → ${d.to}` }),
          'rep-old': () => ({
            tt: '替换(旧件)',
            cls: 'rep',
            detail: `已被 ${d.newCode} 代用`,
            name: findNode(this.baseTree, node.code)?.name || node.name
          }),
          'rep-new': () => ({
            tt: '替换(新件)',
            cls: 'rep',
            detail: `代用 ${d.oldCode}（映射依据：CN-2026-0088 整体石墨密封改进）`
          })
        }
        if (builders[d.type]) return { ...rec, ...builders[d.type]() }
        return {
          ...rec,
          tt: d.type === 'rev' ? '版本变更' : '数量/属性变更',
          cls: d.type === 'rev' ? 'rev' : 'chg',
          detail: (d.changes || []).map((c) => `${c.f}: ${c.o} → ${c.n}`).join('；'),
          changes: d.changes || []
        }
      }

      ;[...flatB, ...flatR].forEach(({ node }) => {
        const d = diffMap[node.code]
        if (!d || d.__listed) return
        d.__listed = true
        diffList.push(detailOf(d, node))
      })

      this.diffMap = diffMap
      this.diffList = diffList
      this.diffDone = true
      this.selCode = null
      this.linkedCode = null
      this.syncTreeExpand()
      this.toast(`对比完成：共 ${diffList.length} 项差异（基准：下发快照 SNAP-CN-2026-0091）`)
    },
    syncTreeExpand() {
      if (this.isFiltering) {
        this.expandedL = collectKeys(this.displayBaseTree, true)
        this.expandedR = collectKeys(this.displayRetTree, true)
        return
      }
      this.expandedL = keysToLevel(this.displayBaseTree, 2)
      this.expandedR = keysToLevel(this.displayRetTree, 2)
    },
    onTreeClick({ data: row } = {}, side) {
      if (!row) return
      this.selCode = row.code
      this.clickSide = side
      this.linkedCode = null
      const other = this.getTreeRef(side === 'L' ? 'R' : 'L')
      const d = this.diffMap[row.code]
      if (other?.hasNode(row.code)) {
        this.linkedCode = row.code
        other.scrollToKey(row.code)
      } else {
        const tree = side === 'L' ? this.baseTree : this.retTree
        const parentCode = findParent(tree, row.code)
        if (other && parentCode && other.hasNode(parentCode)) {
          this.linkedCode = parentCode
          other.scrollToKey(parentCode)
        }
        const hints = {
          add: '该节点为回传新增，基准快照中不存在（已定位其挂接父节点）',
          del: '该节点在回传版本中已删除（已定位原父节点位置）',
          'rep-old': `旧件已被 ${d?.newCode} 替换（另一侧请查找橙色新件行）`,
          'rep-new': `新件替换自 ${d?.oldCode}（另一侧请查找橙色旧件行）`
        }
        this.toast(hints[d?.type] || '另一侧无匹配节点（已定位其父节点）', true)
      }
      this.rowClsTick += 1
      if (d?.changes?.length) this.showMiniCard(d)
    },
    showMiniCard({ changes }) {
      const txt = changes
        .map((c) => `${c.f}: <span class="old">${c.o}</span> → <span class="new">${c.n}</span>`)
        .join('<br>')
      this.toast(txt, false, 4000)
    },
    onTreeScroll(side, params) {
      if (!this.syncScroll || this.scrollLock || params?.isY === false) return
      this.scrollLock = true
      const other = this.getTreeRef(side === 'L' ? 'R' : 'L')
      const el = other?.getScrollEl()
      if (el) {
        const max = el.scrollHeight - el.clientHeight || 1
        const p = params.scrollTop / (params.scrollHeight - params.bodyHeight || 1)
        other.scrollTo(p * max)
      }
      this.$nextTick(() => { this.scrollLock = false })
    },
    onSyncChange(val) {
      this.toast(val ? '同步滚动：开启（按百分比联动）' : '同步滚动：关闭（点击联动定位）')
    },
    acceptDiff(row) {
      this.$set(row, 'status', 'accepted')
      this.toast('差异已接受')
    },
    rejectDiff(row) {
      this.$set(row, 'status', 'rejected')
      this.logs.push({
        t: '2026-08-23 18:40',
        badge: 'b-warn',
        tag: '驳回',
        txt: '业务人员驳回 1 条差异（理由：见驳回单）'
      })
      this.toast('驳回需填写理由（演示）并已记入协同日志', true)
    },
    simSecondReturn() {
      this.secondReturnCount += 1
      this.logs.push({
        t: `2026-08-23 18:4${this.secondReturnCount}`,
        badge: 'b-none',
        tag: '二次回传',
        txt: `工艺系统二次回传（批次 RT2-2026-0823-0${this.secondReturnCount}），仅涉及 1 条 BOMLine（燃油喷嘴 装配位置号 P12→P14）→ 已登记操作日志，未触发差异对比任务`
      })
      this.activeTab = 'log'
      this.toast('二次回传已登记 · 未触发对比（差异基准仍为下发快照 SNAP-CN-2026-0091）', true, 5000)
    },
    exportReport() {
      const rows = this.diffList
        .map((r) => `<tr><td>${r.tt}</td><td>${r.code}</td><td>${r.name}</td><td>${r.detail || ''}</td></tr>`)
        .join('')
      const html = `<html><head><meta charset="utf-8"><title>PBOM 对比报告</title>
<style>body{font-family:"Microsoft YaHei";padding:30px;color:#1c2430}h1{font-size:18px;border-bottom:2px solid #1c2430;padding-bottom:6px}table{border-collapse:collapse;width:100%;font-size:12px;margin-top:14px}td,th{border:1px solid #999;padding:5px 8px;text-align:left}.meta{font-size:12px;color:#555;margin:10px 0}</style></head><body>
<h1>PBOM 差异对比报告</h1>
<div class="meta">基准：SNAP-CN-2026-0091（系统A下发快照，Rev.B，2026-08-10 14:32，不可变）<br>
对比：RT-2026-0820-01（工艺系统回传，2026-08-20）<br>对比人：zhang_gy · 生成时间：${new Date().toLocaleString()} · 差异合计：${this.diffList.length} 项</div>
<table><tr><th>类型</th><th>件号</th><th>名称</th><th>变更明细</th></tr>${rows}</table></body></html>`
      const a = document.createElement('a')
      a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
      a.download = 'PBOM对比报告_SNAP-0091_vs_RT-0820.html'
      a.click()
      this.toast('报告已导出（HTML，可打印归档）')
    },
    toast(msg, warn = false, dur = 2500) {
      this.toastWarn = warn
      this.toastHtml = warn ? `<span class="warn">⚠ ${msg}</span>` : msg
      this.toastVisible = true
      if (this.toastTimer) clearTimeout(this.toastTimer)
      this.toastTimer = setTimeout(() => {
        this.toastVisible = false
      }, dur)
    }
  }
}
</script>

<style scoped>
.pbom-page {
  --paper: #f7f5f0;
  --ink: #1c2430;
  --ink2: #5a6675;
  --line: #c9c2b4;
  --accent: #e85d04;
  --grid: rgba(28, 36, 48, 0.05);
  --c-add: #2e7d32;
  --bg-add: #e6f4e7;
  --c-del: #c62828;
  --bg-del: #fcebec;
  --c-mov: #7b1fa2;
  --bg-mov: #f4eaf8;
  --c-chg: #b28704;
  --bg-chg: #fdf6dd;
  --c-rev: #1565c0;
  --bg-rev: #e5f0fb;
  --c-rep: #ef6c00;
  --bg-rep: #fff1e3;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  background: var(--paper);
  background-image: linear-gradient(var(--grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 24px 24px;
  color: var(--ink);
  font-size: 13px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pbom-header {
  background: #fff;
  border-bottom: 2px solid var(--ink);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}
.logo {
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 1px;
  border: 2px solid var(--ink);
  padding: 2px 10px;
  background: var(--ink);
  color: #fff;
}
.snapshot-chip {
  background: var(--bg-rep);
  border: 1px solid var(--c-rep);
  color: #8a3d00;
  border-radius: 3px;
  padding: 3px 10px;
  font-size: 12px;
}
.snapshot-chip b { font-family: Consolas, monospace; }
.vsel {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink2);
}
.vsel .lock { color: var(--c-rep); font-size: 11px; }
.btn-primary {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  background: #fffdf8;
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
  flex-shrink: 0;
}
.legend { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.lg-title { font-weight: 700; font-size: 12px; }
.lg {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--ink2);
}
.lg i {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  display: inline-block;
  border: 1px solid rgba(0, 0, 0, 0.25);
}
.lg-add { background: var(--bg-add); border-color: var(--c-add) !important; }
.lg-del { background: var(--bg-del); border-color: var(--c-del) !important; }
.lg-mov { background: var(--bg-mov); border-color: var(--c-mov) !important; }
.lg-chg { background: var(--bg-chg); border-color: var(--c-chg) !important; }
.lg-rev { background: var(--bg-rev); border-color: var(--c-rev) !important; }
.lg-rep { background: var(--bg-rep); border-color: var(--c-rep) !important; }
.sep { width: 1px; height: 18px; background: var(--line); }
.type-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink2);
}
.hint { font-size: 11px; color: var(--ink2); margin-left: auto; }

.stats {
  display: flex;
  gap: 8px;
  padding: 6px 16px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.stat {
  background: #fff;
  border: 1.5px solid var(--ink);
  padding: 4px 12px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.stat .n { font-size: 18px; font-weight: 800; font-family: Consolas, monospace; }
.stat .t { font-size: 11px; color: var(--ink2); }
.stat.total { background: var(--ink); color: #fff; }
.stat.total .t { color: #cfd6e0; }

.pbom-main {
  flex: 1;
  display: flex;
  gap: 10px;
  min-height: 0;
  padding: 0 16px 8px;
}
.treecol {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 2px solid var(--ink);
  background: #fff;
}
.treehead {
  background: var(--ink);
  color: #fff;
  padding: 6px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.treehead .side { font-weight: 700; font-size: 13px; }
.treehead .rev { font-family: Consolas, monospace; font-size: 11px; color: #f5c9a0; }
.tree-body { flex: 1; min-height: 0; }

.bottom {
  height: 270px;
  flex-shrink: 0;
  border: 2px solid var(--ink);
  background: #fff;
  display: flex;
  flex-direction: column;
  margin: 0 16px 8px;
  overflow: hidden;
}
.btabs { height: 100%; display: flex; flex-direction: column; }
.btabs >>> .el-tabs__header {
  margin: 0;
  background: #fffdf8;
  border-bottom: 1.5px solid var(--ink);
}
.btabs >>> .el-tabs__nav-wrap::after { display: none; }
.btabs >>> .el-tabs__item {
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink2);
}
.btabs >>> .el-tabs__item.is-active { background: var(--ink); color: #fff; }
.btabs >>> .el-tabs__active-bar { display: none; }
.btabs >>> .el-tabs__content { flex: 1; overflow: auto; padding: 8px 12px; }
.btabs >>> .el-tab-pane { height: 100%; }

.name-cell { display: inline-flex; align-items: center; gap: 6px; min-width: 0; }
.name { overflow: hidden; text-overflow: ellipsis; }
.name-extra { font-size: 10px; }
.ex-rep { color: var(--c-rep); }
.ex-mov { color: var(--c-mov); }
.miss { color: #9aa3ad; }
.revtag {
  font-family: Consolas, monospace;
  font-size: 10px;
  border: 1px solid var(--line);
  border-radius: 2px;
  padding: 0 3px;
  color: var(--ink2);
}
.dtag {
  font-size: 10px;
  font-weight: 700;
  border-radius: 2px;
  padding: 0 5px;
  color: #fff;
}
.tag-add { background: var(--c-add); }
.tag-del { background: var(--c-del); }
.tag-mov { background: var(--c-mov); }
.tag-chg { background: var(--c-chg); }
.tag-rev { background: var(--c-rev); }
.tag-rep { background: var(--c-rep); }
.tt {
  font-weight: 700;
  font-size: 10px;
  color: #fff;
  border-radius: 2px;
  padding: 0 5px;
}
.old { color: var(--c-del); text-decoration: line-through; font-family: Consolas, monospace; }
.new { color: var(--c-add); font-weight: 700; font-family: Consolas, monospace; }
.mono { font-family: Consolas, monospace; }
.agroup { font-weight: 700; font-size: 11px; color: var(--ink2); letter-spacing: 1px; }
.st-ok { color: var(--c-add); font-size: 11px; font-weight: 700; }
.st-no { color: var(--c-del); font-size: 11px; font-weight: 700; }
.st-wait { font-size: 11px; color: var(--ink2); }

.log-wrap { padding: 0 4px; }
.logline {
  display: flex;
  gap: 10px;
  padding: 5px 8px;
  border-bottom: 1px dashed var(--line);
  font-size: 12px;
  align-items: flex-start;
}
.logline .lt { font-family: Consolas, monospace; color: var(--ink2); flex-shrink: 0; font-size: 11px; }
.badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  border-radius: 2px;
  padding: 1px 6px;
  color: #fff;
}
.b-ok { background: var(--c-add); }
.b-info { background: var(--c-rev); }
.b-warn { background: var(--accent); }
.b-none { background: #9aa3ad; }

.imp { display: flex; gap: 10px; flex-wrap: wrap; }
.impcard { border: 1.5px solid var(--ink); padding: 8px 14px; min-width: 180px; }
.impcard h4 {
  font-size: 11px;
  color: var(--ink2);
  margin: 0 0 6px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 3px;
}
.impcard ul { margin: 0; padding: 0; }
.impcard li { font-size: 12px; margin: 3px 0 3px 14px; }
.impcard .num { font-family: Consolas, monospace; font-weight: 800; color: var(--accent); font-size: 16px; }

#toast {
  position: fixed;
  top: 70px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--ink);
  color: #fff;
  padding: 8px 20px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 99;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
#toast >>> .warn { color: #ffd166; }
#toast >>> .old { color: #ff8a80; text-decoration: line-through; font-family: Consolas, monospace; }
#toast >>> .new { color: #69f0ae; font-weight: 700; font-family: Consolas, monospace; }

.pbom-page >>> .tree-row.d-add,
.pbom-page >>> .el-tree-node__content.d-add { background: var(--bg-add); border-left-color: var(--c-add); }
.pbom-page >>> .tree-row.d-del,
.pbom-page >>> .el-tree-node__content.d-del { background: var(--bg-del); border-left-color: var(--c-del); }
.pbom-page >>> .tree-row.d-del .name { text-decoration: line-through; }
.pbom-page >>> .tree-row.d-mov,
.pbom-page >>> .el-tree-node__content.d-mov { background: var(--bg-mov); border-left-color: var(--c-mov); }
.pbom-page >>> .tree-row.d-chg,
.pbom-page >>> .el-tree-node__content.d-chg { background: var(--bg-chg); border-left-color: var(--c-chg); }
.pbom-page >>> .tree-row.d-rev,
.pbom-page >>> .el-tree-node__content.d-rev { background: var(--bg-rev); border-left-color: var(--c-rev); }
.pbom-page >>> .tree-row.d-rep,
.pbom-page >>> .el-tree-node__content.d-rep { background: var(--bg-rep); border-left-color: var(--c-rep); }
.pbom-page >>> .tree-row.is-sel,
.pbom-page >>> .el-tree-node__content.is-sel {
  background: #fff7e6 !important;
  outline: 1.5px solid var(--accent);
}
.pbom-page >>> .tree-row.is-linked,
.pbom-page >>> .el-tree-node__content.is-linked {
  background: #eef7ff !important;
  outline: 1.5px solid var(--c-rev);
}

.pbom-page >>> .el-table th { background: #fffdf8; color: var(--ink2); font-size: 11px; }
.pbom-page >>> .el-table .agroup-row { background: #fffdf8; }
.pbom-page >>> .el-checkbox { color: var(--ink2); font-size: 12px; }
.pbom-page >>> .el-button--mini { padding: 4px 10px; font-weight: 600; }
</style>
