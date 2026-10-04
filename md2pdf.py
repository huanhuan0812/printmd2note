import markdown
from weasyprint import HTML, CSS
import sys
import os

# ===== 默认参数 =====
DEFAULTS = {
    "PAGE_W":       182.0,
    "PAGE_H":       257.0,
    "MARGIN_TOP":   28.0,
    "TOTAL_LINES":  27,
    "LINE_MM":      8.05,
    "FONT_SIZE":    "13pt",
    # 镜像边距模式
    "MIRROR":        True,   # True=奇偶页左右互换；False=普通固定边距
    "MARGIN_INNER":  14.0,   # 装订侧（打孔侧）
    "MARGIN_OUTER":  8.0,   # 外侧
    # 非镜像模式使用（MIRROR=False 时生效）
    "MARGIN_LEFT":   11.0,
    "MARGIN_RIGHT":  11.0,
}

CONFIG_FILE = "config.toml"


# ===== 配置文件读写 =====
def load_config(path):
    if not os.path.exists(path):
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib
        except ModuleNotFoundError:
            print("警告：无法读取 TOML，跳过配置")
            return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def save_config(cfg, path):
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
    args = {"input": None, "output": None, "config": CONFIG_FILE,
            "export_config": None}
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


def build_page_css(p):
    """根据镜像/非镜像模式生成 @page 与 body 的边距规则"""
    top = p["MARGIN_TOP"]
    bottom = p["MARGIN_BOTTOM"]        # 由 main 反推后塞进来

    if p["MIRROR"]:
        inner = p["MARGIN_INNER"]
        outer = p["MARGIN_OUTER"]
        # :right = 奇数页（装订边在左），:left = 偶数页（装订边在右）
        return f"""
        @page {{
            size: {p['PAGE_W']}mm {p['PAGE_H']}mm;
            margin-top: {top}mm;
            margin-bottom: {bottom}mm;
        }}
        /* 奇数页：装订侧(inner)在左 */
        @page :right {{
            margin-left: {inner}mm;
            margin-right: {outer}mm;
        }}
        /* 偶数页：装订侧(inner)在右 */
        @page :left {{
            margin-left: {outer}mm;
            margin-right: {inner}mm;
        }}
        """
    else:
        return f"""
        @page {{
            size: {p['PAGE_W']}mm {p['PAGE_H']}mm;
            margin: {top}mm {p['MARGIN_RIGHT']}mm {bottom}mm {p['MARGIN_LEFT']}mm;
        }}
        """


def main():
    args = parse_args(sys.argv)

    params = dict(DEFAULTS)
    cfg = load_config(args["config"])
    if cfg:
        params = apply_config(params, cfg)
        print(f"已加载配置：{args['config']}")

    # 导出配置
    if args["export_config"]:
        save_config(params, args["export_config"])
        print(f"已导出配置到：{args['export_config']}")
        return

    if not args["input"]:
        print("用法：python3 md2pdf.py <input.md> [output.pdf] "
              "[--config config.toml] [--export-config out.toml]")
        sys.exit(1)

    # 反推下边距
    bottom = params["PAGE_H"] - params["MARGIN_TOP"] - \
             params["TOTAL_LINES"] * params["LINE_MM"]
    assert bottom > 0, f"参数矛盾：内容超出纸高（下边距 {bottom:.2f}mm）"
    params["MARGIN_BOTTOM"] = bottom

    # 校验正文宽度是否一致（镜像 vs 非镜像）
    if params["MIRROR"]:
        total_lr = params["MARGIN_INNER"] + params["MARGIN_OUTER"]
    else:
        total_lr = params["MARGIN_LEFT"] + params["MARGIN_RIGHT"]
    # 正文可用宽度
    text_w = params["PAGE_W"] - total_lr
    print(f"正文可用宽度：{text_w:.2f}mm")

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
    h1, h2, h3, h4, h5, h6,
    p, li, td, th, blockquote, pre, div {{
        font-size: {params['FONT_SIZE']};
        line-height: {params['LINE_MM']}mm;
        margin: 0;
        padding: 0;
        font-weight: normal;
    }}
    ul, ol {{
        margin: 0;
        padding-left: 8mm;
        list-style-position: outside;
    }}
    ul ul, ol ol, ul ol, ol ul {{ padding-left: 8mm; }}
    li > p {{ margin: 0; padding: 0; }}
    h1, h2, h3, h4, h5, h6 {{
        font-weight: bold;
        height: {params['LINE_MM']}mm;
        line-height: {params['LINE_MM']}mm;
        overflow: hidden;
    }}
    strong, b {{
        color: red;
        font-weight: bold;
    }}
    """)

    html = f"<html><body>{body}</body></html>"
    out = args["output"] or "output.pdf"
    HTML(string=html).write_pdf(out, stylesheets=[css])

    mode = "镜像边距" if params["MIRROR"] else "固定边距"
    print(f"纸张 {params['PAGE_W']}×{params['PAGE_H']}mm，"
          f"下边距 {bottom:.2f}mm，行高 {params['LINE_MM']}mm，"
          f"{params['TOTAL_LINES']} 行/页，{mode} → {out}")


if __name__ == "__main__":
    main()