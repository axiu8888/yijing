# -*- coding: utf-8 -*-
"""将易经解读 Markdown 合成为 EPUB。"""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from bs4 import BeautifulSoup
from ebooklib import epub

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "易经六十四卦解读.epub"

NAMES = [
    "乾", "坤", "屯", "蒙", "需", "讼", "师", "比", "小畜", "履",
    "泰", "否", "同人", "大有", "谦", "豫", "随", "蛊", "临", "观",
    "噬嗑", "贲", "剥", "复", "无妄", "大畜", "颐", "大过", "坎", "离",
    "咸", "恒", "遯", "大壮", "晋", "明夷", "家人", "睽", "蹇", "解",
    "损", "益", "夬", "姤", "萃", "升", "困", "井", "革", "鼎",
    "震", "艮", "渐", "归妹", "丰", "旅", "巽", "兑", "涣", "节",
    "中孚", "小过", "既济", "未济",
]


def md_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
        output_format="html5",
    )


def rewrite_images(html: str, book: epub.EpubBook, added: set[str]) -> str:
    """把 ./images/XX.png 转成 EPUB 内嵌资源路径。"""
    soup = BeautifulSoup(html, "lxml")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        m = re.search(r"images/(\d{2})\.png", src.replace("\\", "/"))
        if not m:
            img.decompose()
            continue
        num = m.group(1)
        img_path = ROOT / "images" / f"{num}.png"
        if not img_path.exists():
            img.decompose()
            continue
        item_id = f"img_{num}"
        href = f"images/{num}.png"
        if item_id not in added:
            item = epub.EpubItem(
                uid=item_id,
                file_name=href,
                media_type="image/png",
                content=img_path.read_bytes(),
            )
            book.add_item(item)
            added.add(item_id)
        img["src"] = href
        # 限制宽度，方便阅读器
        img["style"] = "max-width:100%;height:auto;display:block;margin:1em auto;"
        if img.has_attr("width"):
            del img["width"]
    # lxml 会包 html/body，只取 body 内容
    body = soup.body
    if body:
        return "".join(str(x) for x in body.children)
    return str(soup)


def chapter_from_md(
    book: epub.EpubBook,
    md_path: Path,
    uid: str,
    title: str,
    added_images: set[str],
) -> epub.EpubHtml:
    raw = md_path.read_text(encoding="utf-8")
    # 去掉首行标题（EPUB 章节标题单独用）
    raw = re.sub(r"^# .+\n+", "", raw, count=1)
    html = md_to_html(raw)
    html = rewrite_images(html, book, added_images)
    # 去掉空的 align p，保留 img
    chapter = epub.EpubHtml(title=title, file_name=f"{uid}.xhtml", lang="zh")
    chapter.content = (
        f"<h1>{title}</h1>\n"
        f'<div class="content">\n{html}\n</div>'
    )
    return chapter


def main():
    book = epub.EpubBook()
    book.set_identifier("yijing-64gua-notes")
    book.set_title("易经六十四卦解读")
    book.set_language("zh")
    book.add_author("整理自周易卦爻辞解读")

    style = """
@namespace epub "http://www.idpf.org/2007/ops";
body { font-family: "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", serif;
       line-height: 1.7; margin: 5%; }
h1, h2, h3 { font-weight: bold; margin-top: 1.2em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.95em; }
th, td { border: 1px solid #999; padding: 0.35em 0.5em; }
blockquote { color: #333; border-left: 3px solid #bbb; margin-left: 0; padding-left: 1em; }
pre, code { font-family: Consolas, monospace; font-size: 0.9em; }
img { max-width: 100%; height: auto; }
.content p { text-align: justify; }
"""
    nav_css = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=style.encode("utf-8"),
    )
    book.add_item(nav_css)

    added_images: set[str] = set()
    spine = ["nav"]
    toc = []

    # 封面式前言：README
    readme = ROOT / "README.md"
    if readme.exists():
        ch = chapter_from_md(book, readme, "intro", "目录与说明", added_images)
        ch.add_item(nav_css)
        book.add_item(ch)
        spine.append(ch)
        toc.append(ch)

    # 八卦
    bagua = ROOT / "00-八卦简表.md"
    if bagua.exists():
        ch = chapter_from_md(book, bagua, "bagua", "八卦简表", added_images)
        ch.add_item(nav_css)
        book.add_item(ch)
        spine.append(ch)
        toc.append(ch)

    # 六十四卦
    for i, name in enumerate(NAMES, start=1):
        matches = list(ROOT.glob(f"{i:02d}-*.md"))
        if not matches:
            print(f"skip missing {i}")
            continue
        title = f"{i:02d} {name}"
        ch = chapter_from_md(
            book, matches[0], f"gua_{i:02d}", title, added_images
        )
        ch.add_item(nav_css)
        book.add_item(ch)
        spine.append(ch)
        toc.append(ch)
        print(f"add {title}")

    book.toc = tuple(toc)
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(str(OUT), book)
    print(f"\nWrote: {OUT}")
    print(f"Size: {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
