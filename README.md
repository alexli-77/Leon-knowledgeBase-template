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
│   └── 99_Meta/            ← 元数据
│       └── routing.md      ← /record 的路由规则
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

## License

MIT。随便用、改、分发。

## 改动建议流向

fork 后魔改到你的生活里才是正道。如果你觉得某条 routing 规则或某个 _MOC 写法值得共享，欢迎 PR。
