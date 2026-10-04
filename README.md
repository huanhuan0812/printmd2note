# md2pdf

把 Markdown 转换成**可直接打印**的 PDF，精确控制纸张、页边距、行高，支持活页打孔的镜像边距。

## 特点

- **精确网格排版**：固定行高（mm 为单位），每页固定行数，适合预印刷纸/活页纸
- **镜像边距**：双面打印时奇偶页左右边距自动互换，保证打孔侧始终留白一致
- **第一页孔位置可设**：孔在左或在右都支持
- **加粗变红**：Markdown 里的 `**加粗**` 转成红色加粗
- **统一字号**：标题和正文大小一致，仅靠加粗区分层级
- **配置文件**：参数写进 `config.toml`，不用改代码
- **流式分页**：内容按行高网格流动，一页排满自动翻页

## 环境要求

- Python 3.8+（读 TOML 配置建议 3.11+，否则需 `pip install tomli`）
- WeasyPrint
- 一款中文字体（默认用宋体类：`Songti SC` / `Noto Serif CJK SC` / `SimSun`）

## 安装

推荐用虚拟环境：

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install weasyprint markdown
```

### 系统依赖（WeasyPrint 需要）

- **macOS**：`brew install pango cairo libffi`
- **Ubuntu/Debian**：`sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libcairo2`
- **Windows**：一般 pip 装完即可，若报错需装 GTK 运行库

### 中文字体

```bash
# 检查是否已装
fc-list | grep -i "noto serif cjk"
```

- **macOS**：自带 `Songti SC`，无需额外装
- **Linux**：`sudo apt install fonts-noto-cjk`
- **Windows**：可下载 Noto Serif CJK，或把字体名改成 `SimSun`（宋体）

## 快速开始

### 1. 生成默认配置

```bash
python3 md2pdf.py --export-config config.toml
```

### 2. 编辑配置

用文本编辑器改 `config.toml` 里的数值（见下方"配置说明"）。

### 3. 转换

```bash
python3 md2pdf.py 输入.md 输出.pdf
```

程序会自动读取同目录的 `config.toml`。

## 用法

```
python3 md2pdf.py <input.md> [output.pdf] [选项]
```

| 参数 | 说明 |
|------|------|
| `<input.md>` | 输入的 Markdown 文件 |
| `[output.pdf]` | 输出 PDF，缺省为 `output.pdf` |
| `--config <file>` | 指定配置文件，缺省 `config.toml` |
| `--export-config <file>` | 把当前参数导出为配置文件，不做转换 |

### 示例

```bash
# 用默认配置转换
python3 md2pdf.py 文言字词.md out.pdf

# 用指定配置
python3 md2pdf.py 文言字词.md out.pdf --config my.toml

# 导出当前配置备份
python3 md2pdf.py --export-config backup.toml
```

## 配置说明

`config.toml` 各项含义：

```toml
# ===== 纸张 =====
PAGE_W = 182.0      # 纸宽 mm（JIS B5 = 182）
PAGE_H = 257.0      # 纸高 mm（JIS B5 = 257）

# ===== 纵向 =====
MARGIN_TOP = 28.0   # 上边距 mm
TOTAL_LINES = 27    # 每页行数
LINE_MM = 8.05      # 行高 mm
FONT_SIZE = "13pt"  # 字号
# 下边距由公式反推：PAGE_H - MARGIN_TOP - TOTAL_LINES × LINE_MM

# ===== 横向：镜像边距（活页/双面装订）=====
MIRROR = true       # true=奇偶页左右互换；false=固定边距
MARGIN_INNER = 12.0 # 有孔侧（装订侧）mm
MARGIN_OUTER = 9.0  # 无孔侧（外侧）mm
FIRST_HOLE = "left" # 第 1 页孔的位置："left" 或 "right"

# ===== 横向：非镜像模式时才用（MIRROR = false）=====
MARGIN_LEFT = 10.5
MARGIN_RIGHT = 10.5
```

### 关键约束

下边距是**自动反推**的：

```
MARGIN_BOTTOM = PAGE_H - MARGIN_TOP - TOTAL_LINES × LINE_MM
```

如果算出负数，程序会报错：

```
AssertionError: 参数矛盾：内容超出纸高（下边距 -3.20mm）
```

这时需要**减小行数、行高、或上边距**中的一项。

### 镜像边距行为

以 `MARGIN_INNER = 12`、`MARGIN_OUTER = 9`、`FIRST_HOLE = "left"` 为例：

| 页 | 左边距 | 右边距 | 孔侧 |
|----|--------|--------|------|
| 第 1 页（奇）| **12mm** | 9mm | 左 |
| 第 2 页（偶）| 9mm | **12mm** | 右 |
| 第 3 页（奇）| **12mm** | 9mm | 左 |

这样双面打印、长边翻转后，**每张纸的打孔侧都对齐在 12mm 处**。

若第 1 页的孔在右边，设 `FIRST_HOLE = "right"`，奇偶规则对调。

## Markdown 语法支持

| 语法 | 效果 |
|------|------|
| `**文字**` / `__文字__` | **红色加粗** |
| `# 标题` ~ `###### 标题` | 加粗，占一行（与正文同字号）|
| `- 列表` / `1. 列表` | 列表，缩进 8mm |
| 普通段落 | 一行，自动折行 |
| 表格、围栏代码块 | 支持（通过 markdown 扩展）|

## 打印设置（重要）

打印 PDF 时**必须**：

| 设置项 | 值 |
|--------|-----|
| 纸张尺寸 | **B5 (JIS)** 或自定义 182×257mm |
| 缩放 | **100% / 实际大小** |
| 边距 | **无 / None** |
| 双面 | **长边翻转**（书本式）|

> ⚠️ 大多数打印驱动默认会"适应页面"并附加自己的边距，**必须全部关闭**，否则 PDF 里设定的边距会被覆盖。

### 校准

第一张打印后，用尺子量：

- 第一条文字基线是否在 `MARGIN_TOP` 附近
- 最后一行底部是否在 `PAGE_H - MARGIN_BOTTOM` 附近

若整体偏移（打印机硬边距导致），微调 `MARGIN_TOP` 补偿。

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'markdown'` | 库没装到脚本用的 Python | `python3 -m pip install markdown weasyprint`，或用 venv |
| `pipx install markdown` 后仍报错 | pipx 是隔离的 CLI 环境，不暴露给脚本 | 改用 venv 安装 |
| 中文显示为方框 | 字体未装或名称不对 | 装 Noto CJK，或改 `font-family` |
| 加粗没变红 | 用了 `__文字__` 或 CSS 被覆盖 | 检查 Markdown 写法；确认 `strong, b` 规则存在 |
| 打印后边距不对 | 打印驱动加了边距/缩放 | 关闭"适应页面"，边距设"无" |
| 奇偶页边距没互换 | 文档只有一页，或打印未双面 | 用多页文档验证；打印选长边翻转 |
| 报错"参数矛盾：内容超出纸高" | 行数×行高超出可用高度 | 减小行数/行高/上边距 |
| 找不到 `tomli` | Python < 3.11 | `pip install tomli`，或升级 Python |

## 项目结构

```
md2pdf/
├── md2pdf.py       # 主程序
├── config.toml     # 配置文件
├── 输入.md          # 你的 Markdown
└── 输出.pdf         # 生成的 PDF
```

## 原理简述

1. Markdown → HTML（`markdown` 库）
2. HTML + CSS → PDF（WeasyPrint）
3. 通过 CSS 控制排版：
   - `@page` 设纸张尺寸与边距
   - `@page :left/:right` 实现镜像边距
   - `line-height: 8.05mm` 固定行高
   - 所有块级元素 `margin/padding: 0` 保证网格对齐
   - `strong, b { color: red }` 让加粗变红

## 许可

自用工具，随意修改使用。