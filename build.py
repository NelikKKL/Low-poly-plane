#!/usr/bin/env python3
"""
build.py — сборщик Low Poly Plane в один self-contained HTML.

Использование:
    python build.py [--src plane.html] [--out plane_bundle.html] [--dir ./]

Все пути к ресурсам разрешаются относительно --dir (или папки --src).
"""

import argparse
import base64
import mimetypes
import os
import re
import sys


# ──────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────────────────────────────────────

def read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def to_data_uri(path: str, mime: str | None = None) -> str:
    """Кодирует файл в data URI (base64)."""
    if mime is None:
        mime, _ = mimetypes.guess_type(path)
        if mime is None:
            mime = "application/octet-stream"
    data = base64.b64encode(read_bytes(path)).decode("ascii")
    return f"data:{mime};base64,{data}"

def resolve(filename: str, base_dir: str) -> str | None:
    """Возвращает абсолютный путь, если файл существует, иначе None.
    Пробует альтернативные имена: three.min.js → three_min.js и наоборот."""
    candidate = os.path.join(base_dir, filename)
    if os.path.isfile(candidate):
        return candidate

    # Попробуем заменить точки на подчёркивания и обратно
    alt1 = filename.replace(".", "_")          # three.min.js → three_min_js
    alt2 = filename.replace(".", "_", 1)       # three.min.js → three_min.js  (первая точка)
    alt3 = filename.rsplit(".", 1)             # ['three.min', 'js']
    alt3 = alt3[0].replace(".", "_") + "." + alt3[1] if len(alt3) == 2 else None

    for alt in filter(None, [alt1, alt2, alt3]):
        c = os.path.join(base_dir, alt)
        if os.path.isfile(c):
            print(f"  [info] найдено как {alt}")
            return c

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Шаги инлайнинга
# ──────────────────────────────────────────────────────────────────────────────

def inline_favicon(html: str, base_dir: str) -> str:
    """<link rel="icon" href="favicon.png"> → data URI."""
    def replace(m):
        href = m.group(1)
        path = resolve(href, base_dir)
        if path is None:
            print(f"  [warn] favicon не найден: {href}")
            return m.group(0)
        uri = to_data_uri(path)
        print(f"  [ok]   favicon    {href}  ({os.path.getsize(path):,} bytes)")
        return f'<link rel="icon" href="{uri}" type="image/x-icon">'

    return re.sub(
        r'<link\s[^>]*rel=["\']icon["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
        replace,
        html,
        flags=re.IGNORECASE,
    )

def inline_font(html: str, base_dir: str) -> str:
    """url('Fredoka-Regular.ttf') → data URI внутри @font-face."""
    def replace(m):
        fname = m.group(1)
        path = resolve(fname, base_dir)
        if path is None:
            print(f"  [warn] шрифт не найден: {fname}")
            return m.group(0)
        uri = to_data_uri(path, "font/truetype")
        print(f"  [ok]   font       {fname}  ({os.path.getsize(path):,} bytes)")
        return f"url('{uri}') format('truetype')"

    return re.sub(
        r"url\(['\"]?([\w\-\.]+\.ttf)['\"]?\)\s*format\(['\"]truetype['\"]\)",
        replace,
        html,
        flags=re.IGNORECASE,
    )

def inline_audio(html: str, base_dir: str) -> str:
    """<audio src="menu.mp3"> → data URI."""
    def replace(m):
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        path = resolve(src, base_dir)
        if path is None:
            print(f"  [warn] аудио не найдено: {src}")
            return m.group(0)
        uri = to_data_uri(path, "audio/mpeg")
        print(f"  [ok]   audio      {src}  ({os.path.getsize(path):,} bytes)")
        return f"{prefix}{uri}{suffix}"

    return re.sub(
        r'(<audio\b[^>]*\bsrc=["\'])([^"\']+\.mp3)(["\'][^>]*>)',
        replace,
        html,
        flags=re.IGNORECASE,
    )

def inline_script(html: str, base_dir: str) -> str:
    """<script src="three.min.js"></script> → <script>…код…</script>."""
    def replace(m):
        src = m.group(1)
        path = resolve(src, base_dir)
        if path is None:
            print(f"  [warn] скрипт не найден: {src}")
            return m.group(0)
        code = read_text(path)
        print(f"  [ok]   script     {src}  ({os.path.getsize(path):,} bytes)")
        return f"<script>\n{code}\n</script>"

    return re.sub(
        r'<script\s+src=["\']([^"\']+\.js)["\']>\s*</script>',
        replace,
        html,
        flags=re.IGNORECASE,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Главная функция
# ──────────────────────────────────────────────────────────────────────────────

def build(src: str, out: str, base_dir: str) -> None:
    print(f"\n{'─'*56}")
    print(f"  Low Poly Plane — сборка в один HTML")
    print(f"{'─'*56}")
    print(f"  Источник : {src}")
    print(f"  Ресурсы  : {base_dir}")
    print(f"  Результат: {out}")
    print(f"{'─'*56}\n")

    html = read_text(src)
    original_size = len(html.encode("utf-8"))

    html = inline_favicon(html, base_dir)
    html = inline_font(html, base_dir)
    html = inline_audio(html, base_dir)
    html = inline_script(html, base_dir)

    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    final_size = os.path.getsize(out)
    print(f"\n{'─'*56}")
    print(f"  Исходный размер  : {original_size:>10,} bytes")
    print(f"  Итоговый размер  : {final_size:>10,} bytes")
    print(f"  Готово → {out}")
    print(f"{'─'*56}\n")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Собирает Low Poly Plane в один self-contained HTML.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--src", default="plane.html",
        help="Входной HTML-файл (default: plane.html)",
    )
    parser.add_argument(
        "--out", default="plane-single.html",
        help="Выходной файл (default: plane_bundle.html)",
    )
    parser.add_argument(
        "--dir", default=None,
        help="Папка с ресурсами (default: папка --src)",
    )
    args = parser.parse_args()

    src = os.path.abspath(args.src)
    if not os.path.isfile(src):
        print(f"Ошибка: файл не найден — {src}", file=sys.stderr)
        sys.exit(1)

    base_dir = os.path.abspath(args.dir) if args.dir else os.path.dirname(src)
    out = os.path.abspath(args.out)

    build(src, out, base_dir)


if __name__ == "__main__":
    main()
