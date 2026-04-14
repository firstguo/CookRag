# recipes 数据格式

本项目的菜谱数据使用中文 Markdown 文件，导入脚本会读取 `recipes/*.md` 并写入 Neo4j。

## 文件约定

每个菜谱一个 `.md` 文件。

### 1) 推荐 frontmatter 字段

使用 YAML frontmatter（文件开头的 `--- ... ---`）：

- `id`：菜谱唯一 id（可选；缺失则使用文件名作为 id）
- `title`：中文标题（必填）
- `ingredients`：食材（建议为数组）
- `tags`：标签/菜系关键词（建议为数组，可选）
- `cook_time_minutes`：可选，烹饪时间（分钟）
- `steps`：步骤（建议为数组；导入脚本会原样写入并用于 embedding）

### 2) 正文（可选）

正文内容不会被强依赖，但推荐把步骤或补充说明写在正文中，便于人类阅读。

导入脚本会优先使用 `frontmatter.steps`；如果缺失，再尝试从正文解析 Markdown 列表作为 steps。

## 示例

参考 `sample.md`。

