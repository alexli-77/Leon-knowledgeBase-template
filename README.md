# Leon Knowledge Base Template

一个基于 **Obsidian + Claude Code** 的个人知识库模板。
PARA 变体 + 数字前缀 + MOC 文件 + 路由规则 + `/record` skill，让"把东西记下来"变成一句指令。

## 这个 repo 给谁用

适合：
- 用 Obsidian 管理长期知识的人
- 用 Claude Code 当工作台的人
- 想让"记录"零摩擦的人（一句话 `/record xxx`，自动归到正确文件夹）

不适合：
- 只想要笔记模板、不想折腾 Claude Code 的人（可以只用 `templates/Private-Vault` 部分）

## 架构一览

```
你的 Vault/
├── Private-Vault/          ← 个人区，不 push
│   ├── 00_Inbox/           ← 收集箱
│   ├── 10_Daily/           ← 每日记录
│   ├── 20_PhD/             ← 博士相关（或替换成你的主业）
│   ├── 30_Work/            ← 工作/业务
│   ├── 40_Apps/            ← 副业应用
│   ├── 50_Content/         ← 自媒体内容工坊
│   ├── 60_Hobby/           ← 爱好（运动/游戏/音乐等）
│   ├── 70_Areas/           ← 长期关注的领域
│   ├── 80_People/          ← 人际 CRM
│   ├── 90_Resources/       ← 可复用资源
│   ├── 95_Archive/         ← 归档
│   └── 99_Meta/            ← 元数据 + 管理工具
│       ├── routing.md      ← /record 的路由规则
│       ├── watch-list.md   ← 待跟进事项总览（status 字段聚合视图）
│       ├── todos.md        ← 小颗粒待办（OKR 之外的小事）
│       ├── done.md         ← 已完成事项归档（按月分段）
│       └── subscriptions.md ← 订阅追踪（付费服务、到期日）
└── Public-Vault/           ← 公开区（博客、论文笔记）
```

核心联动：

1. **`99_Meta/routing.md`** — 把"关键词/内容特征"映射到"该写到哪个文件"
2. **`~/.claude/skills/record/SKILL.md`** — Claude Code 全局 skill，收到 `/record <内容>` 时读 routing.md 再决定写入位置
3. **调整规则只改 routing.md**，skill 每次都现读，无需修改代码

## 快速开始

```bash
# 1. clone
git clone <this-repo> && cd leon-knowledgeBase-template

# 2. 部署到你的位置（默认 ~/ObsidianVault）
./setup.sh ~/ObsidianVault

# 3. 安装 /record skill（需要 Claude Code）
./setup.sh --install-skill

# 4. 用 Obsidian 打开两个 Vault
# 5. 在 Claude Code 里试一条
/record 今天学会了 X
```

## 关于原作者

这个模板是 Leon（加拿大蒙特利尔大学 CS PhD 在读）从自己 vault 提炼出的骨架。原 vault 中一些子目录带有个人色彩：

- `20_PhD` — 作者是博士，保留了 Research-Logs / Advisor-Meetings / Drafts / Defense。非学术用户可以改成 `20_Main`（主业）或删除
- `30_Work` — 原 vault 叫 `30_Injunction-Practice`（作者的法律业务），模板里改成通用的 `30_Work`
- `60_Hobby` — 原 vault 叫 `60_Badminton`（作者打羽毛球）。改成你的爱好即可
- `50_Content` — 自媒体工坊，如不做内容创作可直接删

**模板保留了这些目录是因为骨架（_MOC.md + 路由规则思路）可以迁移。** 直接用还是魔改，看你。

## 设计原则

- `folder = where it is`（目录就是分类，别发明复杂的 tag 系统）
- `_MOC.md = 每个目录的说明书`（未来的你打开目录第一眼看它）
- `routing.md = 唯一真源`（规则变了只改一处）
- `/record 是显式触发`（不猜测、不打扰）
- **Inbox 兜底**（匹配不上就扔 Inbox，周日整理）
- **状态作为正交维度**（按内容分目录，按 `status` frontmatter 聚合到 `watch-list.md`）

## 处理"需要定期跟进"的事情

知识库目录是按**内容性质**分（PhD / Content / Hobby ...），但有些笔记需要的是**按状态**管理：
等条件触发的项目想法、还没决定要不要做的副业、watching 的开源项目 ...

这套模板用 frontmatter 解决：

```yaml
---
status: watching | considering | active | done | abandoned
priority: low | medium | high
next-review: YYYY-MM-DD
review-cadence: weekly | biweekly | monthly | quarterly
trigger-condition: "什么条件满足后启动"
created: YYYY-MM-DD
---
```

笔记照旧按内容写到对应目录（如 `70_Areas/{领域}/` 或 `50_Content/Ideas/`），
然后把 link 同步到 `99_Meta/watch-list.md` 的对应栏目。

每次 weekly review 时扫一遍 watch-list，决定状态变化。
完整规范见 `templates/Private-Vault/99_Meta/routing.md.template` 的"项目 / Idea 的状态标记规范"章节。

## 配套 skill 推荐

这个模板可以独立使用——只要你想要一个"按 PARA 组织 + `/record` 一键归档"的 Obsidian 知识库就够了。

如果你也用 Claude Code 做 OKR / 周计划复盘，下面这个 skill 直接配套：

> **[life-review-os](https://github.com/alexli-77/life-review-os)** — Life Review OS
>
> 把"周计划 / 双周复盘 / 季末方向校准"做成自动化流程的 Claude Skill。
> 读取你的飞书 Weekly 文档，对比计划与执行，生成下周计划，自动写回飞书。
>
> 启用 vault 联动后，会把以下两类信息存到本模板的 `99_Meta/` 下：
> - **watch-list 决策**（每次 review 时基于 frontmatter 状态自动扫描）
> - **OKR metadata**（deadline / phantom 状态等结构化补全，自动写入 `99_Meta/okr-metadata.yaml`）
>
> 不绑定本模板——任何 markdown 笔记目录都能作为 vault。这里只是"已经有完整 PARA 结构 + watch-list dataview 视图"的开箱即用选择。

## 可选：Vault Gate 门禁

如果你的 vault 由一台服务器统一写入，其它设备通过 API / Hermes / Discord 发起写入请求，可以启用可选组件：

```text
optional/vault-gate/
```

它提供一个无第三方依赖的参考实现：

- 新内容只追加到 `00_Inbox/Capture`
- 修改、移动、删除、重写等请求进入 `00_Inbox/Pending-Review`
- 每次决策写入 `99_Meta/automation-log`
- 可选开启 git auto-commit
- 示例配置只使用占位符，真实 token 和本地路径必须放在仓库外

详见 `optional/vault-gate/README.md`。

## License

MIT。随便用、改、分发。

## 改动建议流向

fork 后魔改到你的生活里才是正道。如果你觉得某条 routing 规则或某个 _MOC 写法值得共享，欢迎 PR。
