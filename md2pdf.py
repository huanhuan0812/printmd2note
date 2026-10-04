import markdown
from weasyprint import HTML, CSS
import sys
import os

# ===== 默认参数 =====
DEFAULTS = {
    "PAGE_W":       182.0,   # 纸宽 mm (JIS B5)
    "PAGE_H":       257.0,   # 纸高 mm
    "MARGIN_TOP":   28.0,    # 上边距 mm
    "TOTAL_LINES":  27,      # 每页行数
    "LINE_MM":      8.05,    # 行高 mm
    "FONT_SIZE":    "13pt",  # 字号
    # 镜像边距（活页/双面装订）
    "MIRROR":        True,   # True=奇偶页左右互换
    "MARGIN_INNER":  12.0,   # 有孔侧（装订侧）
    "MARGIN_OUTER":  9.0,    # 无孔侧（外侧）
    "FIRST_HOLE":    "left", # 第 1 页孔的位置："left" 或 "right"
    # 非镜像模式时才用（MIRROR = false）
    "MARGIN_LEFT":   10.5,
    "MARGIN_RIGHT":  10.5,
}

CONFIG_FILE = "config.toml"


# ===== 配置文件读写 =====
def load_config(path):
    """读取 TOML 配置，文件不存在返回 {}"""
    if not os.path.exists(path):
        return {}
    try:
        import tomllib                      # Python 3.11+
    except ModuleNotFoundError:
        try:
            import tomli as tomllib         # 老版本：pip install tomli
        except ModuleNotFoundError:
            print("警告：无法读取 TOML（需 Python 3.11+ 或 pip install tomli），跳过配置")
            return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def save_config(cfg, path):
    """手写 TOML，零依赖"""
    lines = ["# md2pdf 配置文件\n"]
    for k, v in cfg.items():
        if isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        elif isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        else:
            lines.append(f"{k} = {v}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def apply_config(params, cfg):
    """用配置覆盖默认参数，只接受已知键"""
    for k, v in cfg.items():
        if k not in params:
            continue
        if isinstance(params[k], bool):
            params[k] = bool(v)
        elif isinstance(params[k], int) and not isinstance(params[k], bool):
            params[k] = int(v)
        elif isinstance(params[k], float):
            params[k] = float(v)
        else:
            params[k] = str(v)
    return params


# ===== 命令行解析 =====
def parse_args(argv):
    args = {"input": None, "output": None,
            "config": CONFIG_FILE, "export_config": None}
    rest = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--config" and i + 1 < len(argv):
            args["config"] = argv[i + 1]; i += 2
        elif a == "--export-config" and i + 1 < len(argv):
            args["export_config"] = argv[i + 1]; i += 2
        else:
            rest.append(a); i += 1
    if rest:
        args["input"] = rest[0]
    if len(rest) > 1:
        args["output"] = rest[1]
    return args


# ===== 生成 @page 边距规则 =====
def build_page_css(p):
    """根据镜像/非镜像模式、第一页孔位置生成 @page 规则"""
    top = p["MARGIN_TOP"]
    bottom = p["MARGIN_BOTTOM"]

    if not p["MIRROR"]:
        return f"""
        @page {{
            size: {p['PAGE_W']}mm {p['PAGE_H']}mm;
            margin: {top}mm {p['MARGIN_RIGHT']}mm {bottom}mm {p['MARGIN_LEFT']}mm;
        }}
        """

    inner = p["MARGIN_INNER"]
    outer = p["MARGIN_OUTER"]
    first_hole = p.get("FIRST_HOLE", "left").lower()
    assert first_hole in ("left", "right"), \
        f"FIRST_HOLE 必须是 'left' 或 'right'，当前：{first_hole}"

    if first_hole == "left":
        # 奇数页(:right) 孔在左
        right_page = f"margin-left: {inner}mm; margin-right: {outer}mm;"
        left_page  = f"margin-left: {outer}mm; margin-right: {inner}mm;"
    else:
        # 奇数页(:right) 孔在右（对调）
        right_page = f"margin-left: {outer}mm; margin-right: {inner}mm;"
        left_page  = f"margin-left: {inner}mm; margin-right: {outer}mm;"

    return f"""
    @page {{
        size: {p['PAGE_W']}mm {p['PAGE_H']}mm;
        margin-top: {top}mm;
        margin-bottom: {bottom}mm;
    }}
    @page :right {{
        {right_page}
    }}
    @page :left {{
        {left_page}
    }}
    """


# ===== 主流程 =====
def main():
    args = parse_args(sys.argv)

    # 加载配置
    params = dict(DEFAULTS)
    cfg = load_config(args["config"])
    if cfg:
        params = apply_config(params, cfg)
        print(f"已加载配置：{args['config']}")

    # 仅导出配置
    if args["export_config"]:
        save_config(params, args["export_config"])
        print(f"已导出配置到：{args['export_config']}")
        return

    # 必须有输入文件
    if not args["input"]:
        print("用法：python3 md2pdf.py <input.md> [output.pdf] "
              "[--config config.toml] [--export-config out.toml]")
        sys.exit(1)

    # 反推下边距
    bottom = params["PAGE_H"] - params["MARGIN_TOP"] - \
             params["TOTAL_LINES"] * params["LINE_MM"]
    assert bottom > 0, f"参数矛盾：内容超出纸高（下边距 {bottom:.2f}mm）"
    params["MARGIN_BOTTOM"] = bottom

    # 正文可用宽度
    if params["MIRROR"]:
        total_lr = params["MARGIN_INNER"] + params["MARGIN_OUTER"]
    else:
        total_lr = params["MARGIN_LEFT"] + params["MARGIN_RIGHT"]
    text_w = params["PAGE_W"] - total_lr

    # 读 Markdown
    with open(args["input"], encoding="utf-8") as f:
        md_text = f.read()
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    page_css = build_page_css(params)

    css = CSS(string=f"""
    {page_css}

    html, body {{ margin: 0; padding: 0; }}
    body {{
        font-family: "Songti SC", "Noto Serif CJK SC", "SimSun", serif;
        font-size: {params['FONT_SIZE']};
        line-height: {params['LINE_MM']}mm;
    }}

    /* 所有块级元素统一：固定行高，零内外边距 */
    h1, h2, h3, h4, h5, h6,
    p, li, td, th, blockquote, pre, div {{
        font-size: {params['FONT_SIZE']};
        line-height: {params['LINE_MM']}mm;
        margin: 0;
        padding: 0;
        font-weight: normal;
    }}

    /* 列表缩进 */
    ul, ol {{
        margin: 0;
        padding-left: 8mm;
        list-style-position: outside;
    }}
    ul ul, ol ol, ul ol, ol ul {{ padding-left: 8mm; }}
    li > p {{ margin: 0; padding: 0; }}

    /* 标题：锁死一行，仅靠加粗区分 */
    h1, h2, h3, h4, h5, h6 {{
        font-weight: bold;
        height: {params['LINE_MM']}mm;
        line-height: {params['LINE_MM']}mm;
        overflow: hidden;
    }}

    /* 加粗 → 红色 */
    strong, b {{
        color: red;
        font-weight: bold;
    }}
    """)

    html = f"<html><body>{body}</body></html>"
    out = args["output"] or "output.pdf"
    HTML(string=html).write_pdf(out, stylesheets=[css])

    mode = "镜像边距" if params["MIRROR"] else "固定边距"
    first = params.get("FIRST_HOLE", "left")
    print(f"纸张 {params['PAGE_W']}×{params['PAGE_H']}mm，"
          f"正文宽 {text_w:.2f}mm，下边距 {bottom:.2f}mm，"
          f"行高 {params['LINE_MM']}mm，{params['TOTAL_LINES']} 行/页，"
          f"{mode}，第1页孔在{('左' if first == 'left' else '右')} → {out}")


if __name__ == "__main__":
    main()