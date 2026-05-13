"""Generate PDF from V2.md using Edge headless mode (Windows)."""
import markdown

SRC = "E:/xishi-bot/V2.md"
HTML_TMP = "C:/Users/86152/Desktop/西施Bot-V2版本说明书.html"
DST = "C:/Users/86152/Desktop/西施Bot-V2版本说明书.pdf"

with open(SRC, encoding="utf-8") as f:
    md = f.read()

html_body = markdown.markdown(
    md, extensions=["tables", "fenced_code", "codehilite", "toc"]
)

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; font-size: 14px; line-height: 1.8; color: #222; max-width: 900px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #c0392b; border-bottom: 2px solid #c0392b; padding-bottom: 8px; font-size: 24px; }}
h2 {{ color: #2c3e50; border-bottom: 1px solid #ddd; padding-bottom: 6px; font-size: 20px; margin-top: 30px; }}
h3 {{ color: #34495e; font-size: 17px; margin-top: 20px; }}
h4 {{ color: #555; font-size: 15px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #aaa; padding: 6px 10px; text-align: left; }}
th {{ background-color: #ecf0f1; }}
code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-size: 12px; }}
pre {{ background: #f8f8f8; border: 1px solid #ddd; padding: 12px; border-radius: 5px; font-size: 12px; overflow-x: auto; }}
blockquote {{ border-left: 4px solid #e8a0bf; margin: 12px 0; padding: 8px 16px; background: #fdf2f6; }}
hr {{ border: none; border-top: 1px solid #ddd; margin: 24px 0; }}
</style>
</head>
<body>{html_body}</body>
</html>"""

with open(HTML_TMP, "w", encoding="utf-8") as f:
    f.write(html)
print(f"HTML written to: {HTML_TMP}")
print(f"Now run: msedge --headless --print-to-pdf={DST} file:///{HTML_TMP}")
