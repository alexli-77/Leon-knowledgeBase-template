---
name: record
description: >
  将用户口述的任意内容按规则归档到 Obsidian 私人知识库
  (Private-Vault/)。仅在用户显式使用 `/record <内容>` 时触发，
  不要主动推断调用。核心职责：读路由表 → 定位目标文件 →
  带时间戳追加/新建 → 回执路径。
license: MIT
metadata:
  author: Leon (template)
  version: 1.0.0
keywords:
  - record
  - knowledge-base
  - obsidian
  - vault
  - capture
---

# /record — 知识库归档

## 触发

**仅** 当用户消息以 `/record` 开头（或在本轮对话中显式请求"用 /record 记录"）时执行。
普通的"帮我记一下"等自然语言**不触发**——除非用户另行说明。

## 单一信息源

所有路由规则来自 Private-Vault 里的 routing.md。路径参考模板里的默认位置：

```
<VAULT_ROOT>/Private-Vault/99_Meta/routing.md
```

`<VAULT_ROOT>` 就是你部署 vault 的目录（例如 `~/ObsidianVault`）。
第一次使用前请在 routing.md 顶部填好根路径。

**执行前必须 Read 这份 routing.md**。规则只在那里，SKILL.md 里不重复。

## 执行流程

1. **读 routing.md**（每次都读，保证拿到最新规则）
2. **匹配规则**：按表格从上到下匹配第一条命中的
3. **歧义检查**：如果命中 ≥2 条规则，或缺少必要参数，**先问用户**再继续
4. **解析目标路径**：
   - 替换 `YYYY-MM-DD` 为今天日期
   - 替换 `HH:MM` 为当前时分（24h）
   - 生成 slug
5. **准备目录**：目录不存在用 `mkdir -p` 自动建，不问
6. **写入**：
   - 文件不存在 → 新建（daily 文件按 routing.md 的骨架模板）
   - 文件存在、规则标"追加" → 在文件末尾追加
   - 文件存在、规则标"新建" → 在文件名后加 `-2`、`-3` 递增
7. **回执**：一句话告诉用户 `已记录到 <相对 vault 根路径>`

## 默认行为约束

- **不追问**：除歧义/缺参数外，直接写
- **不额外写 Daily**：除非用户在指令里明确说"也记到 daily"
- **不改 Public-Vault**
- **不合并历史内容**：只追加新条目
- **不静默失败**：写入异常必须告诉用户

## 示例

### 例 1：爱好训练

输入：
```
/record 今天正手高远球 30 个
```

执行：命中爱好训练规则 → 写到 `60_Hobby/Training-Logs/training-YYYY-MM-DD.md`

### 例 2：选题灵感

输入：
```
/record 想做个视频：K8s 老兵看 LLM 部署
```

执行：命中 Ideas 规则 → 新建 `50_Content/Ideas/idea-{slug}.md`

### 例 3：显式记 daily

输入：
```
/record 也记到 daily：今天想明白了测试覆盖率其实测的不是代码
```

执行：写到 `10_Daily/YYYY-MM-DD.md` 对应 section

### 例 4：歧义

输入：
```
/record 跟导师聊了 LLM 测试方向
```

执行：同时命中 Advisor-Meetings 和 Research-Logs → 先问用户

## 什么不归这个 skill 管

- Public-Vault 的任何写入
- 修改 routing.md 本身（让用户自己改）
- 知识库搜索/查询
- 内容润色、总结——只做原样归档
