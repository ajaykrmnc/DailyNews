"""Shared navigation and indexes for dated RSS notes."""

import os

from today_news_md import note_days, read, write_if_changed

NAV_MARK = "%%nav%%"


def update_index(out_dir, title, instructions):
    days = note_days(out_dir)
    # Qualify links because other news folders use the same date filenames.
    folder = os.path.basename(os.path.normpath(out_dir))
    for i, day in enumerate(days):
        links = []
        if i:
            links.append(f"[[{folder}/{days[i - 1]}|← {days[i - 1]}]]")
        links.append(f"[[{folder}/{title}|All days]]")
        if i + 1 < len(days):
            links.append(f"[[{folder}/{days[i + 1]}|{days[i + 1]} →]]")
        target = os.path.join(out_dir, f"{day}.md")
        lines = read(target).split("\n")
        lines = [NAV_MARK + " " + " · ".join(links) if line.startswith(NAV_MARK) else line for line in lines]
        write_if_changed(target, "\n".join(lines))
    lines = [f"# {title}", "", instructions, ""]
    lines += [f"- [[{folder}/{day}|{day}]]" for day in reversed(days)]
    write_if_changed(os.path.join(out_dir, f"{title}.md"), "\n".join(lines) + "\n")
