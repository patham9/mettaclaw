from collections import deque
import re
import json
import sqlite3
import uuid
import os
from datetime import datetime

LLM_COMMANDS = {
    "pin",
    "remember",
    "query",
    "episodes",
    "search",
    "send",
    "promote",
    "demote",
    "metta",
    "shell",
    "read-file",
    "write-file",
    "append-file",
}

def quote_arg(x):
    return json.dumps(x, ensure_ascii=False)

def starts_command_line(line):
    s = line.lstrip()
    if not s:
        return False
    # allow "(send ...)" as command start too
    if s.startswith("("):
        s = s[1:].lstrip()
    if not s:
        return False
    first = s.split(maxsplit=1)[0].rstrip(")")
    return first in LLM_COMMANDS


def split_command_blocks(s):
    blocks = []
    cur = []
    for raw in s.splitlines():
        if not raw.strip():
            if cur:
                cur.append(raw)
            continue
        if starts_command_line(raw) and cur:
            blocks.append("\n".join(cur).strip())
            cur = [raw]
        else:
            cur.append(raw)
    if cur:
        blocks.append("\n".join(cur).strip())
    return blocks

TS_RE = re.compile(r'^\("(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"')

def extract_timestamp(line):
    m = TS_RE.search(line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def around_time(needle_time_str, k):
    needle_time_str = needle_time_str.replace(r'\"', '').replace('"', '').strip()
    filename = "repos/mettaclaw/memory/history.metta"
    target = datetime.strptime(needle_time_str, "%Y-%m-%d %H:%M:%S")
    best_lineno = None
    best_line = None
    best_diff = None
    buffer = []
    best_idx = None
    with open(filename, "r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            buffer.append((lineno, line))
            ts = extract_timestamp(line)
            if ts is None:
                continue
            diff = abs((ts - target).total_seconds())
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_lineno = lineno
                best_line = line
                best_idx = len(buffer) - 1
    if best_lineno is None:
        return
    start = max(0, best_idx - k)
    end = min(len(buffer), best_idx + k + 1)
    ret = ""
    for lineno, line in buffer[start:end]:
        ret += f"{lineno}:{line}"
    return ret

def balance_parentheses(s):
    s = s.replace("_quote_", '"').replace("_newline_", "\n")
    sexprs = []
    special_two_arg_cmds = {"write-file", "append-file"}
    for line in split_command_blocks(s):
        line = line.strip()
        if not line:
            continue
        if line.startswith("(-"):
            line = "(pin -" + line[2:]
        elif line.startswith("-"):
            line = "pin " + line
        # remove one outer (...) if present
        if line.startswith("(") and line.endswith(")"):
            line = line[1:-1].strip()
        elif line.startswith("("):
            line = line[1:].strip()
        parts = line.split(maxsplit=1)
        if not parts:
            continue
        cmd = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
        if cmd in special_two_arg_cmds:
            if not rest:
                sexprs.append(f"({cmd})")
                continue
            # filename is first token unless already quoted
            if rest.startswith('"'):
                end = 1
                escaped = False
                while end < len(rest):
                    ch = rest[end]
                    if ch == '"' and not escaped:
                        break
                    escaped = (ch == '\\' and not escaped)
                    if ch != '\\':
                        escaped = False
                    end += 1
                if end < len(rest) and rest[end] == '"':
                    filename = rest[:end+1]
                    content = rest[end+1:].strip()
                else:
                    filename = quote_arg(rest[1:])
                    content = ""
            else:
                split_rest = rest.split(maxsplit=1)
                filename = quote_arg(split_rest[0])
                content = split_rest[1].strip() if len(split_rest) > 1 else ""
            if content:
                if content.startswith('"') and content.endswith('"') and "\n" not in content:
                    sexprs.append(f"({cmd} {filename} {content})")
                else:
                    sexprs.append(f"({cmd} {filename} {quote_arg(content)})")
            else:
                sexprs.append(f"({cmd} {filename})")
            continue
        if rest:
            if rest.startswith('"') and rest.endswith('"') and "\n" not in rest:
                sexprs.append(f"({cmd} {rest})")
            else:
                sexprs.append(f"({cmd} {quote_arg(rest)})")
        else:
            sexprs.append(f"({cmd})")
    ret = " ".join(sexprs)
    return "(" + ret + ")"

def normalize_string(x):
    try:
        if isinstance(x, bytes):
            return x.decode("utf-8", errors="ignore")
        return str(x).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        return str(x)

def test_balance_parenthesis():
    assert balance_parentheses('(write-file test.txt hello world)') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('(append-file test.txt hello world)') == '((append-file "test.txt" "hello world"))'
    assert balance_parentheses('(write-file "test.txt" hello world)') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('(write-file "test.txt" "hello world")') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('(write-file test.txt "hello world")') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('(send test.xt hello world)') == '((send "test.xt hello world"))'
    assert balance_parentheses('write-file test.txt hello world') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('append-file test.txt hello world') == '((append-file "test.txt" "hello world"))'
    assert balance_parentheses('write-file "test.txt" hello world') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('write-file "test.txt" "hello world"') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('write-file test.txt "hello world"') == '((write-file "test.txt" "hello world"))'
    assert balance_parentheses('send test.xt hello world') == '((send "test.xt hello world"))'

_PROMOTION_CONN = None

def promotion_open_map(path="repos/mettaclaw/memory/promotions.db"):
    global _PROMOTION_CONN
    _PROMOTION_CONN = sqlite3.connect(path)
    _PROMOTION_CONN.execute("PRAGMA journal_mode=WAL")
    _PROMOTION_CONN.execute("PRAGMA synchronous=NORMAL")
    _PROMOTION_CONN.execute("""
        CREATE TABLE IF NOT EXISTS kv (
            key BLOB PRIMARY KEY,
            value REAL NOT NULL,
            lasttime REAL
        )
    """)
    _PROMOTION_CONN.commit()

def promotion_key(k):
    if isinstance(k, uuid.UUID):
        return k.bytes
    if isinstance(k, str):
        return uuid.UUID(k).bytes
    if isinstance(k, bytes) and len(k) == 16:
        return k
    raise TypeError("key must be uuid.UUID, UUID string, or 16-byte UUID")

def promotion_set_value(k, v):
    _PROMOTION_CONN.execute(
        """
        INSERT INTO kv(key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (promotion_key(k), float(v))
    )

def promotion_get_value(k, default=None):
    row = _PROMOTION_CONN.execute(
        "SELECT value FROM kv WHERE key = ?",
        (promotion_key(k),)
    ).fetchone()
    return row[0] if row else default

def promotion_get_all_keys():
    rows = _PROMOTION_CONN.execute(
        "SELECT key FROM kv"
    ).fetchall()
    return [str(uuid.UUID(bytes=row[0])) for row in rows]

def promotion_set_lasttime(k, t):
    _PROMOTION_CONN.execute(
        """
        INSERT INTO kv(key, value, lasttime)
        VALUES (?, 0.0, ?)
        ON CONFLICT(key) DO UPDATE SET lasttime = excluded.lasttime
        """,
        (promotion_key(k), float(t))
    )

def promotion_get_lasttime(k, default=None):
    row = _PROMOTION_CONN.execute(
        "SELECT lasttime FROM kv WHERE key = ?",
        (promotion_key(k),)
    ).fetchone()
    return row[0] if row and row[0] is not None else default

def promotion_has_key(k):
    row = _PROMOTION_CONN.execute(
        "SELECT 1 FROM kv WHERE key = ?",
        (promotion_key(k),)
    ).fetchone()
    return row is not None

def promotion_delete_key(k):
    _PROMOTION_CONN.execute(
        "DELETE FROM kv WHERE key = ?",
        (promotion_key(k),)
    )

def promotion_commit():
    _PROMOTION_CONN.commit()

def promotion_close_map():
    global _PROMOTION_CONN
    if _PROMOTION_CONN is not None:
        _PROMOTION_CONN.commit()
        _PROMOTION_CONN.close()
        _PROMOTION_CONN = None

if __name__ == "__main__":
    test_balance_parenthesis()
    path = "test.db"
    if os.path.exists(path):
        os.remove(path)
    promotion_open_map(path)
    k = "b7e55f3a-376f-493f-a5cb-9a9e01e7f062"
    promotion_set_value(k, 0.73)
    assert promotion_get_value(k) == 0.73
    assert promotion_has_key(k) is True
    promotion_set_lasttime(k, 123.45)
    assert promotion_get_lasttime(k) == 123.45
    assert promotion_get_value(k) == 0.73
    promotion_delete_key(k)
    assert promotion_has_key(k) is False
    assert promotion_get_value(k) is None
    assert promotion_get_lasttime(k) is None
    promotion_close_map()
    os.remove(path)
    print("promotion hashmap tests passed")

