# 全方向调研 · 2026-09-24

本目录是 [`docs/PLAN.md`](../../PLAN.md) 的证据基础。计划里每一处改动都能在这里找到出处。

## 方法

- **Tavily 检索**：12 个方向，共 104 条 `search_depth=advanced` 查询，约 1,040 条结果。方向包括规范、厂商采用、竞品 registry、种子源、抓取、许可证、质量/去重、安全、Router、论文、GEO、运营。
- **Tavily Research（pro）**：3 个深度研究任务，分别是 registry 全景、生态安全、Skill 检索与路由。
- **逐方向核实**：6 个分析回合。每个回合都拿一手来源核对检索线索，包括：
  - 规范原文、厂商文档；
  - `vercel-labs/skills`、`cli/cli`、`openai/codex` 源码；
  - arXiv 全文；
  - 对各 registry 的 robots.txt / ToS / API 实测；
  - 36 个种子仓库的浅克隆。

  Tavily 自动生成的摘要有几处是错的，已在各文件中点名纠正。例如“2026 年规范新增字段”和“Agent Skills 属于 AAIF 项目”，两条都不成立。
- 只有二手来源、无法核实的说法，文件中标为 **UNVERIFIED**。凡是作者自己提出的阈值、目标，都注明“提议值”，需要用数据校准。

## 12 条核心结论

1. **“最大”这个位置已经有人占了。**
   - SkillsMP 首页自报 3,229,343 个 skill。
   - 学术数据集 GitSkills（2026-07，CC-BY-4.0）公开了 3,797,117 个 SKILL.md 文件，来自 282,200 个仓库；按内容去重后 1,877,981 个，约 50% 是逐字副本。
   - skills.sh API 自称收录 60 万以上。
   - 本仓当前 0 条。README 里“largest… on the internet”这句话现在就能被证伪。→ [registries-crawling.md](registries-crawling.md)
2. **可以守住的定位**是“开放、可验证、许可证感知、去重后的规范索引”，具体包括：
   - 数据开放，可以整体下载；
   - 许可证按 skill 解析；
   - 能追溯每个 skill 的原作与副本关系（lineage）；
   - 跨 registry 的 ID 映射；
   - 许可证已清的精选镜像。

   现有的 registry 没有一家同时做到这五点。
3. **规范（agentskills.io，main@69ef37e）**
   - 只有 `name` 和 `description` 必填。
   - **没有 `version` 字段**，参考校验器 skills-ref 会直接拒绝顶层 `version:`。
   - `license` 是自由文本。
   - 2026 年只有措辞上的澄清，没有新增字段。
   - `.agents/skills` 是事实上的共享路径，已有 46 个客户端支持。
   - 另有两份相邻规范：Cloudflare `/.well-known/agent-skills/index.json` RFC v0.2.0（`npx skills` 已在读取），以及 Agent Plugins 1.0（2026-08-06 发布）。
   - → [spec-adoption.md](spec-adoption.md)
4. **本仓骨架与规范冲突的地方：**
   - `version` 被设为必填；
   - `id` 用的是 name，而 name 并不全局唯一；
   - 只有 curated 层有 hash；
   - 许可证按仓库级处理；
   - `router/SKILL.md` 没有 YAML frontmatter，而且放在 CLI 不扫描的目录里，**现在无法被安装**。
5. **许可证**
   - 1.43M 个 skill 里只有 11.25% 声明了 license。
   - anthropics/skills 根目录没有 LICENSE；docx/pdf/pptx/xlsx 四个 skill 是“All rights reserved”。
   - 多个聚合仓把这些专有 skill 转载后标成 MIT/Apache。
   - Figma 的 skill 受其开发者条款约束，不能再分发。

   → 必须按 skill 逐个解析许可证，**永远不从副本收录**。详见 [seeds-licensing.md](seeds-licensing.md)，种子清单机器可读版在 [seed-batch-1.json](seed-batch-1.json)。
6. **安全**
   - 聚合型源索引本身就是攻击面：157 个确认恶意的 skill 是经聚合站传播的；AgentBaiting 行动在各 AI 目录里被列出 600 多次。
   - 扫描器只能做分诊：Cisco skill-scanner 在留出集上的召回率只有 7.75%；Trail of Bits 绕过了所有主流扫描器。
   - SkillJacking：925 个 skill 的依赖指向已删除或可被抢注的账号、域名。

   → 必须做到：commit 固定到 SHA、校验引用对象是否仍存在、curated 层双引擎扫描、文件类型白名单、人工审核。→ [security-quality.md](security-quality.md)
7. **去重**
   - 约 46–50% 是副本，而且以逐字拷贝为主。
   - 推荐 MinHash（5-gram）加编辑相似度复核。
   - 只用 name+description 做 embedding 分不清真重复。
8. **Router**
   - BM25 与小型 embedding 模型效果相当（SkillRet 基准 R@5：53 vs 55）。
   - **正文是关键信号**：隐藏正文会让准确率掉 37–44 个百分点。
   - 对 BM25 候选做 LLM 重排效果最好。
   - 库越大路由越差（对数衰减），所以要：返回小 top-k、支持拒答、结果去重、不按热度排序。→ [router-papers.md](router-papers.md)
9. **GEO**
   - “权威语气”没有显著效果；数据、引用、新鲜日期、第三方提及才有效。
   - llms.txt 基本不被抓取，但成本低。
   - AGENTS.md 只对在本仓里工作的 Agent 生效。“Primary Directive”这类写法与已公开的偏好操纵/间接注入模式一致，风险高、收益接近零。
   - 最有效的渠道是用户**自己**的 AGENTS.md / CLAUDE.md 里的 opt-in 片段：Vercel 的评测里，这种写法把触发率提到 95% 以上。→ [geo-ops.md](geo-ops.md)
10. **分发渠道都有门槛**
    - skills.sh 只能靠真实的 `npx skills add` 安装遥测上榜。
    - Claude Code marketplace 名 `agent-skills` 已被保留。
    - awesome 列表对仓库年龄、star 数有要求，且禁止 AI 提交 PR。
    - Show HN 要求有可以上手运行的东西。
11. **抓取**
    - 冷启动可以用 GitSkills（CC-BY-4.0）。
    - ClawHub 的文档明确允许目录复用它的数据。
    - SkillsMP 的 ToS 禁止批量下载；skills.sh 的 API 需要 Vercel OIDC token。
    - GitHub code search 限 10 次/分钟、每个查询最多 1,000 条结果，只能按文件大小切片来绕过。
    - 刷新方案：GH Archive + git trees + ETag。即使到 50 万个 skill，每天也少于约 2.5 万次调用。
    - 种子规模（几十个仓库）直接 `git ls-remote` + 浅克隆，不需要 API token。
12. **名称冲突**：arXiv 2609.13353 的论文就叫 “SkillAtlas”（一个攻击轨迹库）。

## 文件索引

| 文件 | 内容 |
|---|---|
| [spec-adoption.md](spec-adoption.md) | 规范字段与约束、skills-ref、治理情况、version 实践、各厂商发现路径、`.well-known`、marketplace |
| [registries-crawling.md](registries-crawling.md) | 竞品对比表（含 robots/ToS 实测）、全网规模估计、GitHub 抓取限制、发现与刷新架构和调用预算 |
| [seeds-licensing.md](seeds-licensing.md) | 种子第 1 批（36 个仓库）、许可证边界案例、解析算法、白名单、NOTICE/署名义务、优先级 |
| [seed-batch-1.json](seed-batch-1.json) | 上表的机器可读版，是 PLAN 任务 S1-2 的输入 |
| [security-quality.md](security-quality.md) | 安全事件时间线、实证研究、扫描器对比、分层门槛、去重算法、security/quality 字段草案 |
| [router-papers.md](router-papers.md) | 现有检索工具、检索研究数据、文献表、Router v1 设计、评测方案 |
| [geo-ops.md](geo-ops.md) | GEO 证据、现有措辞风险评估、分发渠道机制、运营约束、运营日历 |

> 各文件里的数字都是 2026-09-24 的快照，不要原样抄进 README。README 上的数字只能由 `index/stats.json` 生成（见 PLAN 的 S4-1）。
