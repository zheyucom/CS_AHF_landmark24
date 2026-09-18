#!/usr/bin/env python3
"""Generate a read-only Zotero/Obsidian weekly literature intake report."""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return [x.strip().strip('"\'') for x in value[1:-1].split(",") if x.strip()]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---\n"):
        return {}
    block = text.split("---", 2)[1]
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(block) or {}
        return data if isinstance(data, dict) else {}
    except ImportError:
        out: dict[str, Any] = {}
        for line in block.splitlines():
            if not line or line[0].isspace() or ":" not in line:
                continue
            key, value = line.split(":", 1)
            out[key.strip()] = scalar(value)
        return out


def parse_day(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def sqlite_path(config: Path) -> Path:
    match = re.search(r'^\s*sqlite_path:\s*["\']?([^"\'\n]+)', config.read_text(), re.M)
    if not match:
        raise SystemExit(f"sqlite_path not found in {config}")
    return Path(match.group(1).strip()).expanduser()


def zotero_snapshot(source: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temp = tempfile.TemporaryDirectory(prefix="zotero_weekly_")
    target = Path(temp.name) / "zotero.sqlite"
    shutil.copy2(source, target)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(source) + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, Path(str(target) + suffix))
    return temp, target


def recent_zotero(source: Path, start: date, end: date) -> list[dict[str, str]]:
    temp, snapshot = zotero_snapshot(source)
    try:
        con = sqlite3.connect(snapshot)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            select i.itemID, i.key, i.dateAdded, i.dateModified
            from items i
            join itemTypes it on it.itemTypeID = i.itemTypeID
            where it.typeName not in ('attachment', 'note', 'annotation')
              and not exists (select 1 from deletedItems d where d.itemID=i.itemID)
              and (date(i.dateAdded) between date(?) and date(?)
                   or date(i.dateModified) between date(?) and date(?))
            order by i.dateModified desc
            """,
            (start.isoformat(), end.isoformat(), start.isoformat(), end.isoformat()),
        ).fetchall()
        ids = [row["itemID"] for row in rows]
        fields: dict[int, dict[str, str]] = {item_id: {} for item_id in ids}
        if ids:
            marks = ",".join("?" for _ in ids)
            for row in con.execute(
                f"""
                select d.itemID, f.fieldName, v.value
                from itemData d
                join fields f on f.fieldID=d.fieldID
                join itemDataValues v on v.valueID=d.valueID
                where d.itemID in ({marks}) and f.fieldName in ('title','DOI','date','publicationTitle')
                """,
                ids,
            ):
                fields[row["itemID"]][row["fieldName"]] = row["value"]
        return [
            {
                "key": row["key"],
                "added": row["dateAdded"],
                "modified": row["dateModified"],
                **fields[row["itemID"]],
            }
            for row in rows
        ]
    finally:
        temp.cleanup()


def collection_item_ids(source: Path, collection_key: str) -> set[int]:
    temp, snapshot = zotero_snapshot(source)
    try:
        con = sqlite3.connect(snapshot)
        row = con.execute("select collectionID from collections where key=?", (collection_key,)).fetchone()
        if not row:
            raise SystemExit(f"Zotero collection not found: {collection_key}")
        rows = con.execute(
            "select itemID from collectionItems where collectionID=?", (row[0],)
        ).fetchall()
        return {int(item[0]) for item in rows}
    finally:
        temp.cleanup()


def recent_zotero_in_collection(
    source: Path, collection_key: str, start: date, end: date
) -> list[dict[str, str]]:
    temp, snapshot = zotero_snapshot(source)
    try:
        con = sqlite3.connect(snapshot)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            select i.itemID, i.key, i.dateAdded, i.dateModified
            from items i
            join collectionItems ci on ci.itemID=i.itemID
            join collections c on c.collectionID=ci.collectionID
            join itemTypes it on it.itemTypeID=i.itemTypeID
            where c.key=? and it.typeName not in ('attachment', 'note', 'annotation')
              and not exists (select 1 from deletedItems d where d.itemID=i.itemID)
              and (date(i.dateAdded) between date(?) and date(?)
                   or date(i.dateModified) between date(?) and date(?))
            order by i.dateModified desc
            """,
            (collection_key, start.isoformat(), end.isoformat(), start.isoformat(), end.isoformat()),
        ).fetchall()
        ids = [row["itemID"] for row in rows]
        fields: dict[int, dict[str, str]] = {item_id: {} for item_id in ids}
        if ids:
            marks = ",".join("?" for _ in ids)
            for row in con.execute(
                f"""
                select d.itemID, f.fieldName, v.value
                from itemData d
                join fields f on f.fieldID=d.fieldID
                join itemDataValues v on v.valueID=d.valueID
                where d.itemID in ({marks}) and f.fieldName in ('title','DOI','date','publicationTitle')
                """, ids
            ):
                fields[row["itemID"]][row["fieldName"]] = row["value"]
        return [
            {"key": row["key"], "added": row["dateAdded"], "modified": row["dateModified"], **fields[row["itemID"]]}
            for row in rows
        ]
    finally:
        temp.cleanup()


def managed_highlights(source: Path) -> tuple[int, int]:
    temp, snapshot = zotero_snapshot(source)
    try:
        con = sqlite3.connect(snapshot)
        row = con.execute(
            """
            select count(*) as highlights, count(distinct parentItemID) as pdfs
            from itemAnnotations
            where comment like '[codex-highlight:%'
            """
        ).fetchone()
        return int(row[0]), int(row[1])
    finally:
        temp.cleanup()


def note_link(path: Path, root: Path) -> str:
    relative = path.relative_to(root / "notes" / "literature").with_suffix("")
    return f"[[{relative.as_posix()}]]"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path.cwd())
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--collection-key", default="A63I4DT4")
    parser.add_argument("--all-zotero", action="store_true", help="Include all Zotero collections instead of the configured collection.")
    args = parser.parse_args()

    vault = args.vault.expanduser().resolve()
    end = args.as_of
    start = end - timedelta(days=max(args.days, 1) - 1)
    note_root = vault / "notes" / "literature"
    notes: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(note_root.glob("R*.md")):
        data = frontmatter(path)
        if "literature-note" in (data.get("tags") or []):
            notes.append((path, data))

    changed = []
    for path, data in notes:
        changed_day = parse_day(data.get("updated")) or parse_day(data.get("created"))
        if changed_day and start <= changed_day <= end:
            changed.append((path, data))

    source_db = sqlite_path(vault / "config" / "local.yaml")
    zotero = (
        recent_zotero(source_db, start, end)
        if args.all_zotero
        else recent_zotero_in_collection(source_db, args.collection_key, start, end)
    )
    note_dois = {str(data.get("doi", "")).lower() for _, data in notes if data.get("doi")}
    unmatched_zotero = [item for item in zotero if item.get("DOI", "").lower() not in note_dois]
    missing_zotero = [(path, data) for path, data in notes if not data.get("zotero_item_key")]
    pending_fulltext = []
    for path, data in notes:
        status = str(data.get("reading_status", ""))
        if not data.get("source_acquired") or "awaiting-fulltext" in status or "awaiting-local-fulltext" in status:
            pending_fulltext.append((path, data))
    lines = [
        f"# 文献周报：{start.isoformat()} 至 {end.isoformat()}",
        "",
        (
            f"> **一眼速览**：知识库 {len(notes)} 篇；本期新增/更新 {len(changed)} 篇；"
            f"Zotero 变化 {len(zotero)} 篇；待建卡 {len(unmatched_zotero)} 篇；"
            f"待补全文 {len(pending_fulltext)} 篇。"
        ),
        "",
        "## 本期新增/更新",
        "",
    ]
    for path, data in changed:
        summary = data.get("key_finding") or data.get("theme") or data.get("reading_status") or "已更新"
        lines.append(f"- {note_link(path, vault)}：{summary}")
    if not changed:
        lines.append("- 本期没有新增或更新卡片。")

    if unmatched_zotero or missing_zotero or pending_fulltext:
        lines.extend(["", "## 需要处理", ""])
        for item in unmatched_zotero:
            title = item.get("title") or "<无标题>"
            doi = item.get("DOI") or "无 DOI"
            lines.append(f"- **待筛选/建卡**：{title} | `{doi}` | Zotero `{item['key']}`")
        for path, data in missing_zotero:
            lines.append(f"- **未关联 Zotero**：{note_link(path, vault)} | `{data.get('doi', '')}`")
        for path, data in pending_fulltext:
            lines.append(f"- **待补全文**：{note_link(path, vault)}：{data.get('reading_status', '')}")

    lines.append("")

    output = args.output or note_root / "周报" / f"{end.isoformat()}.md"
    if not output.is_absolute():
        output = vault / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
