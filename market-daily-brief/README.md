# 每日市场简报（A股板块ETF + 全球市场）

每天自动做三件事：拉当天财经资讯、拉观察池里各标的的涨跌（当日 / 近1周 / 近1月 / 近3月）、
把它们和沪深300（海外标的另外和本地基准）做对比，然后按公开规则给出**操作建议和理由**。

输出是一份 Markdown 报告：存档到 `reports/`，同时**写入语雀知识库并推送微信**
（企业微信 / 飞书 / Telegram / 邮箱也支持）。标题统一带日期和时间，如 `市场简报 2026-09-18 16:40`。
不依赖任何付费数据源，也不需要 API Key 就能跑；配了 LLM Key 会额外生成一段综述。

## 快速开始

```bash
cd market-daily-brief
pip install -r requirements.txt

# 生成今天的报告（写到 reports/，同时打印路径）
PYTHONPATH=src python -m mdbrief

# 只看行情、不抓资讯，直接打到终端
PYTHONPATH=src python -m mdbrief --no-news --no-save

# 同时产出结构化 JSON，并推送到已配置的渠道
PYTHONPATH=src python -m mdbrief --json --notify
```

常用参数：

| 参数 | 作用 |
| --- | --- |
| `--no-news` | 跳过资讯抓取，只算行情（最快，约 3 秒） |
| `--fresh-hours N` | 只保留最近 N 小时的资讯，默认 36（地区源自动放宽到 120） |
| `--llm` | 调用 LLM 生成综述，需要 `LLM_API_KEY` |
| `--notify` | 按环境变量推送到所有已配置渠道 |
| `--check` | 只自检推送渠道配置（会真的调一次语雀接口验证凭据），不生成报告 |
| `--json` | 额外输出 `reports/<日期>.json`，方便二次加工 |
| `--config DIR` | 使用自定义配置目录 |
| `--stdout` / `--no-save` | 打到标准输出 / 不写文件 |

## 报告里有什么

1. **今日速览**：沪深300 各周期涨跌与区间分位、市场温度、建议总仓位、观察池涨跌家数、超额领先与落后。
2. **A股板块ETF vs 沪深300**：按分组的表格，含今日 / 近1周 / 近1月 / 近3月涨跌、周超额、月超额、区间分位、趋势、建议。
3. **全球市场**：港股、美股、日韩台、东南亚（含泰国）、欧洲、大类资产，并给出「相对本地基准」和「相对沪深300」两个超额。
4. **资讯要点**：宏观与政策（高影响）、A股与国内消息、全球宏观、海外分区（港股/日本/韩国/泰国/东南亚/欧洲/美股）。
5. **操作建议与理由**：组合层面仓位建议 + 逐标的建议，每条都附带触发的数值、信号和相关新闻。
6. **AI 综述**（可选）与**数据抓取告警**。

## 数据源

全部是公开免费接口，任一源失败只记录告警、不影响整份报告。

| 类型 | 来源 | 说明 |
| --- | --- | --- |
| A股 / 港股实时 | 腾讯财经 `qt.gtimg.cn` | 批量快照，40 个代码一次请求 |
| A股日K | 腾讯 `web.ifzq.gtimg.cn`，新浪为备用 | 前复权日线 |
| 全球指数 / 个股 / 商品汇率 | Yahoo Finance `v8/finance/chart` | 港美日韩台、东南亚、欧洲、黄金原油铜、美元指数、美债10Y |
| 财经快讯（专业） | 财联社电报 | 带板块 / 主题 / 个股标签，签名接口，自动分页 |
| 财经快讯 | 同花顺快讯、华尔街见闻、新浪7x24、新浪财经要闻 | 中文快讯与要闻 |
| 海外资讯 | CNBC、Yahoo Finance、Investing.com RSS | 英文源 |
| 分地区资讯 | Google News RSS | 港股 / 日本 / 韩国 / 泰国 / 东南亚 / 欧洲，可自由增删关键词 |

关于数据源的两点实测经验：

- 东方财富（`push2.eastmoney.com`）从海外 IP 访问会被拒，所以行情走腾讯 + 新浪 + Yahoo。
  如果你在国内本机跑，这三家同样可用，不需要改配置。
- Yahoo 的 `chartPreviousClose` 是「区间起点之前」的收盘价，**不是昨收**。本项目取「最后一根早于当前交易日的
  K 线收盘」作为昨收，只有历史极度稀疏（如泰国 SET 指数）时才退回 `chartPreviousClose`。

## 配置

### `config/watchlist.yml`：观察什么

按分组维护，组内标的继承组上的 `market` / `provider` / `benchmark`：

```yaml
groups:
  - name: 科技成长
    market: A股
    provider: tencent        # tencent(A股/港股) 或 yahoo(全球)
    benchmark: cn            # 引用 benchmarks 里的键，用于算超额
    instruments:
      - { symbol: sz159995, name: 芯片ETF, keywords: [芯片, 半导体, 光刻机] }
```

- `keywords` 用于把资讯关联到该标的，并据此算消息面情绪分，建议写得具体一些。
- `history_symbol`：当主代码历史K线稀疏时用它算区间涨跌（如泰国 SET 用 `THD`、恒生科技用 `3033.HK`），
  报告会标注「区间涨跌用代理标的计算」。
- 裸代码会自动补交易所前缀（`510300` → `sh510300`），但**指数必须写全**（`sh000300`），否则无法和个股区分。

默认已内置 34 个 A股板块ETF（宽基 / 科技成长 / 高端制造 / 消费医药 / 金融周期 / 红利防守 / 跨境）
和 27 个全球标的。想加自己的持仓个股，直接往对应分组里加一行即可，`kind` 写 `股票`。

### `config/news.yml`：看哪些资讯

- `sources`：每个源可单独开关、设条数上限、设权重（`weight` 越高越容易进要闻）。
- `macro_keywords`：命中即视为高影响宏观/政策消息，会加权并影响仓位建议。
- `sentiment`：利好/利空词表，用于给板块算消息面情绪分。

新增一个地区只要加一条 `google_news`：

```yaml
- { id: google_news, name: 印度股市, enabled: true, limit: 10, region: 印度, weight: 2,
    query: 印度股市 Sensex, hl: zh-CN, gl: CN, ceid: "CN:zh-Hans" }
```

## 建议是怎么算出来的

规则全部写在 `src/mdbrief/advisor.py`，报告里会把触发的阈值和实际数值一起打印，方便自己复核或改参数。

打分项（加总后决定动作）：

| 维度 | 规则 |
| --- | --- |
| 相对基准 | 近1月超额 × 0.6（截断 ±10）、近1周超额 × 0.8（截断 ±6） |
| 趋势 | 价格 > MA20 > MA60 记 +3；价格 < MA20 < MA60 记 −3；仅站上 MA20 记 +1 |
| 过热 | 偏离 MA20 超过 10% 记 −2 |
| 区间位置 | 近半年分位 ≥95 记 −2，≥85 记 −1，≤20 且非空头记 +1.5 |
| 量能 | 放量（≥20日均量 1.8 倍）随当日涨跌 ±1 |
| 波动 | 年化波动率 ≥45% 记 −1.5 |
| 消息面 | 情绪分 × 0.5（截断 ±4） |

动作映射：`≥5` 加仓 / `2~5` 持有 / `−3~2` 观望 / `−6~−3` 减仓 / `≤−6` 规避；
若同时处于区间顶部或严重过热，加仓和持有都会降级为「持有但不追高，上移止盈」。

组合层面按沪深300 的周期涨跌、趋势、区间分位，加上观察池涨跌家数，给出 2–8 成的仓位区间。

## 推送与归档

`--notify` 会把所有已配置的渠道一起推掉，配了哪个就推哪个，没配的跳过、互不影响。
**语雀和邮件收完整 Markdown 报告，微信这类 IM 收精简摘要**（IM 有长度限制，塞全文会被截断）。

| 渠道 | 环境变量 | 收到的内容 |
| --- | --- | --- |
| 语雀 | `YUQUE_NAMESPACE` + `YUQUE_TOKEN` 或 `YUQUE_COOKIE` | 完整报告，存成知识库文档 |
| Server酱（微信） | `SERVERCHAN_SENDKEY` | 摘要 |
| PushPlus（微信） | `PUSHPLUS_TOKEN` | 摘要 |
| 企业微信机器人 | `WECOM_WEBHOOK` | 摘要 |
| 飞书机器人 | `FEISHU_WEBHOOK` | 摘要 |
| Telegram | `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` | 摘要 |
| 邮件 | `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`MAIL_TO`、`MAIL_FROM` | 完整报告 |

标题统一为 **`市场简报 2026-09-18 16:40`**（日期 + 时间），微信推送和语雀文档标题一致。

配完先自检一次，它会真的调一次语雀接口验证凭据，不用等到定时任务才发现配错：

```bash
PYTHONPATH=src python -m mdbrief --check
```

LLM 综述（可选，任何 OpenAI 兼容接口）：`LLM_API_KEY`、`LLM_BASE_URL`（默认 DeepSeek）、`LLM_MODEL`。

## 三个关键变量怎么获取

### `YUQUE_NAMESPACE`：语雀知识库地址

格式是 `login/repo-slug`，两段都能从 URL 里直接看出来：

- `login`：打开语雀，点右上角头像进个人主页，地址栏 `https://www.yuque.com/**abcd**` 里的 `abcd` 就是。
  注意它是**账号路径**，不是昵称，昵称可以是中文但 login 一定是英文。
- `repo-slug`：知识库地址 `https://www.yuque.com/abcd/**market-brief**` 的第二段。
  **这个知识库不用先建**——Token 模式下第一次运行会自动创建（名为「市场简报」，私密）。

所以填 `abcd/market-brief` 即可。团队知识库同理，第一段换成团队的 login（自动建库会落到团队下）。

### `YUQUE_TOKEN`：语雀访问令牌（⚠️ 需要超级会员）

1. 登录语雀 → 右上角头像 → **账户设置** → 左侧 **Token**（直达 <https://www.yuque.com/settings/tokens>）
2. 点新建，权限至少勾上知识库和文档的**读 + 写**，创建后**只显示一次**，立刻复制。
3. `export YUQUE_TOKEN=粘贴进来`

**注意**：语雀从 2022 年起把开放 API 的 Personal Access Token 划入**超级会员**权益，
免费账号打开那个页面建不出 Token。如果你没有超级会员，用下面的 Cookie 模式。

#### 没有超级会员：Cookie 模式（免费，实验性）

走的是语雀网页端自己在用的内部接口（`/api/docs` 等），**不是公开 API**：语雀改版可能失效，
而且 Cookie 大约两周过期，需要重新粘贴一次。适合先试用，长期无人值守还是建议 Token。

1. 浏览器登录语雀，随便打开一个知识库页面。
2. 按 F12 → **Network** 标签 → 刷新页面 → 点任意一个 `www.yuque.com` 的请求 →
   在 Request Headers 里找到 `Cookie:`，**复制整行的值**。
3. 确认里面同时包含 `_yuque_session=` 和 `yuque_ctoken=`（后者是写操作要用的 CSRF 令牌，缺了会被拦）。
4. `export YUQUE_COOKIE='粘贴整段cookie'`（用单引号，里面有分号和空格）

Cookie 模式**不会自动建知识库**，请先在语雀网页上手动建一个，slug 和 `YUQUE_NAMESPACE` 第二段对上。

### `SERVERCHAN_SENDKEY`：微信推送密钥

1. 打开 <https://sct.ftqq.com> ，用**微信扫码**登录（就是注册）。
2. 进「SendKey」页面，复制那串以 `SCT` 开头的密钥。
3. 同一页面按提示**关注公众号完成微信绑定**，否则发出去的消息没有落点。
4. `export SERVERCHAN_SENDKEY=SCTxxxxxx`

**免费额度每天 5 条**，本项目每天推 2 条（A股收盘 + 美股收盘），够用；但如果你手动触发调试
多跑几次就可能撞额度。另外免费版微信卡片**只显示标题不显示正文**，想看内容得点进去。

两个替代选择：

- **PushPlus**（`PUSHPLUS_TOKEN`）：<https://www.pushplus.plus> 微信扫码登录后复制 token，
  免费额度比 Server酱 宽松，配了就会一起推。
- **Server酱³**（key 以 `sctp` 开头，在 <https://sc3.ft07.com> 获取）：推到独立 App 而不是微信，
  本项目会按前缀自动识别并切换到对应接口，仍然填在 `SERVERCHAN_SENDKEY` 里。

### 语雀可选变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `YUQUE_PUBLIC` | `0` | 文档公开性，0 私密 / 1 公开 / 2 企业内公开 |
| `YUQUE_BASE_URL` | `https://www.yuque.com/api/v2` | 空间版/专业版换成自己的域名 |
| `YUQUE_CREATE_REPO` | `1` | 设为 `0` 则知识库不存在时直接报错，不自动建 |
| `--yuque-slug` | `brief-<日期>-<场次>` | 手动指定文档路径 |

关于文档数量：每天两个场次各一篇——A股收盘后那次是 `brief-2026-09-18-close`，
美股收盘后（次日清晨）那次是 `brief-2026-09-18-overnight`。
**同一场次重跑（比如失败重试、手动触发）会覆盖同一篇文档，不会刷出一堆重复文档。**
想每次都新建，用 `--yuque-slug` 传一个带时间的路径即可。

语雀 API 有个坑：通过 API 创建的文档默认不在知识库目录里，只能在「未归档」中看到。
本项目会自动再调一次目录接口把它挂到根节点；万一挂载失败，文档本身已经写入成功，
日志会提示去「未归档」找，不会因为这一步让整次推送失败。

## 每天自动跑

### 方式一：GitHub Actions（零成本，已配好）

`.github/workflows/market-daily-brief.yml` 已经定时在北京时间 16:20（A股收盘后）和次日 06:30
（美股收盘后）各跑一次，把报告提交回仓库、写进语雀并推送微信。
只需在仓库 Settings → Secrets and variables → Actions 里添加 `YUQUE_TOKEN`、`YUQUE_NAMESPACE`、
`SERVERCHAN_SENDKEY` 这三个（其余渠道按需），也可以在 Actions 页面手动触发。

注意：GitHub 的定时任务在高峰期会延迟几分钟到几十分钟，对日报场景无影响。

### 方式二：本机 cron

```bash
# 工作日 16:20 生成、写语雀、推微信，日志留一份
20 16 * * 1-5 cd /path/to/market-daily-brief && \
  YUQUE_TOKEN=xxx YUQUE_NAMESPACE=me/market-brief SERVERCHAN_SENDKEY=xxx \
  PYTHONPATH=src /usr/bin/python3 -m mdbrief --json --notify >> /tmp/mdbrief.log 2>&1
```

### 方式三：容器

```bash
docker run --rm -v "$PWD:/app" -w /app -e PYTHONPATH=src \
  -e SERVERCHAN_SENDKEY=xxx python:3.12-slim \
  sh -c "pip install -q -r requirements.txt && python -m mdbrief --notify"
```

## 开发

```bash
pip install pytest
python -m pytest        # 52 个用例，全部离线，不打网络
```

测试覆盖指标计算、Yahoo 昨收推导（含当日K线缺失、历史稀疏两种情况）、腾讯报文解析、
规则引擎的各档动作、资讯去重与国内外分类、报告表格结构、语雀发布（Token 模式的新建/覆盖/
个人与团队自动建库/目录挂载降级、Cookie 模式的先写草稿再发布）、Server酱 两条产品线的
端点识别，以及推送分发（微信收摘要、语雀收全文、单渠道失败不影响其他）。

## 已知局限

- 所有涨跌幅基于收盘价/最新价，ETF 不做分红除权还原，与券商App可能有零点几个百分点的差异。
- 规则引擎是趋势 + 相对强弱的机械打分，不理解基本面和估值，**不能替代自己的判断**。
  熊市里它会普遍偏防守，牛市里会普遍偏进攻，这是设计使然。
- 消息面情绪分只是关键词计数，不做语义理解；需要更准的判断请开 `--llm`。
- 泰国 SET、恒生科技等指数的历史K线依赖代理标的，区间涨跌有跟踪误差。

---

本项目只做数据整理与规则化提示，不构成投资建议。
