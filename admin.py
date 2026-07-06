#!/usr/bin/env python3
"""
Wikipedia管理者の活動状況を調べる
"""

import time
import re
import argparse
import requests
import mwparserfromhell
from zoneinfo import ZoneInfo
import html
from datetime import datetime

API = "https://ja.wikipedia.org/w/api.php"
ROLE_NAMES: dict[str, str] = {
    "sysop": "管理者",
    "bureaucrat": "ビューロクラット",
    "suppress": "オーバーサイト",
    "checkuser": "チェックユーザー",
    "bot": "BOT",
}


def mysleep(sec):
    print(f"sleep({sec})")
    time.sleep(sec)


#!/usr/bin/env python3


TITLE = "Wikipedia:Bot/ステータス"


def get_bot_operator_by_table(bot_name: str) -> str | None:
    """ボット名から運用者を取得する"""

    params = {
        "action": "query",
        "prop": "revisions",
        "titles": TITLE,
        "rvslots": "main",
        "rvprop": "content",
        "formatversion": "2",
        "format": "json",
    }
    headers = {"User-Agent": "mybot/1.0"}

    r = requests.get(API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()

    text = data["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]

    code = mwparserfromhell.parse(text)

    for template in code.filter_templates():
        if template.name.strip() != "BotL":
            continue

        try:
            name = template.get(1).value.strip_code().strip()
        except ValueError:
            continue

        if name != bot_name:
            continue

        try:
            operator = template.get(2).value.strip_code().strip()
            return operator
        except ValueError:
            return None

    return None


def get_bot_operator(user, sleep_requests):
    """Bot運用者を取得"""
    print(f"get_bot_operator() start! user={user}")
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": f"利用者:{user}",
        "rvprop": "content",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json",
    }

    headers = {"User-Agent": "mybot/1.0"}

    mysleep(sleep_requests)
    r = requests.get(API, params=params, headers=headers, timeout=10.0)
    r.raise_for_status()
    data = r.json()

    pages = data["query"]["pages"]
    if not pages:
        return None

    revisions = pages[0].get("revisions")
    if not revisions:
        return None

    text = revisions[0]["slots"]["main"]["content"]

    print(f"len(text)={len(text)}")

    # {{Bot|Akas1950}}から持ってくる
    # m = re.search(
    #     r"\{\{\s*Bot\s*\|\s*([^|}\n]+)",
    #     text,
    #     flags=re.IGNORECASE | re.DOTALL,
    # )
    m = re.search(
        r"\{\{\s*Bot\b(?:(?!\}\}).)*?\|\s*(?![^|}]*=)([^|}\n]+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        print(f"operator found. from {{{{BOT}}}}: {m.group(1).strip()}")
        return m.group(1).strip()

    # | 運用者        = [[user:Akas1950|Akas1950]]
    # ↑から持ってくる
    m = re.search(
        r"\|\s*運用者\s*=\s*\[\[(?:[Uu]ser:|利用者:)?([^|\]]+)",
        text,
    )

    if m:
        print(f"operator found. from 運用者: {m.group(1).strip()}")
        return m.group(1).strip()

    operator = get_bot_operator_by_table(user)
    if operator:
        return operator

    print(f"operator not found. {user}")
    return None


def get_admin_users(role, sleep_requests):
    """roleのユーザを取得する"""
    users = []
    aufrom = None

    while True:
        params = {
            "action": "query",
            "list": "allusers",
            "augroup": role,
            "aulimit": "max",
            "format": "json",
        }
        if aufrom:
            params["aufrom"] = aufrom

        headers = {"User-Agent": "mybot/1.0"}

        mysleep(sleep_requests)
        r = requests.get(API, params=params, headers=headers, timeout=10.0)
        r.raise_for_status()
        data = r.json()

        users.extend(u["name"] for u in data["query"]["allusers"])

        if "continue" not in data:
            break

        aufrom = data["continue"]["aufrom"]

    return users


def get_last_edit(user, sleep_requests):
    """最終編集日時取得"""
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": user,
        "uclimit": 1,
        "ucprop": "timestamp",
        "format": "json",
    }

    headers = {"User-Agent": "mybot/1.0"}

    mysleep(sleep_requests)
    r = requests.get(API, params=params, headers=headers, timeout=10.0)
    r.raise_for_status()
    data = r.json()

    contribs = data["query"]["usercontribs"]
    if not contribs:
        return None

    return contribs[0]["timestamp"]


def proc_role(role, sleep_requests, args):
    """role毎の処理"""
    users = get_admin_users(role, sleep_requests)
    result = []

    for i, user in enumerate(users):
        print(f"{i}, {role}: {user}")

        if args.t:
            if i > 2:
                break

        ts = get_last_edit(user, sleep_requests)

        operator = None
        operator_ts = None

        if role == "bot":
            operator = get_bot_operator(user, sleep_requests)

            if operator:
                operator_ts = get_last_edit(operator, sleep_requests)

        result.append((user, ts, operator, operator_ts))

        mysleep(sleep_requests)

    result.sort(key=lambda x: x[1] or "", reverse=True)

    return result


def format_ts(ts):
    if ts:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        age = datetime.now(dt.tzinfo) - dt
        style = ""
        if age.days >= 365:
            style = " style='background-color:#ffcccc'"
        return (
            dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
            style,
        )

    return ("編集なし", " style='background-color:#ffcccc'")


def write_html(all_result, filename="report.html"):
    """最終html生成"""
    with open(filename, "w", encoding="utf-8") as fp:
        fp.write("""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>利用者最終編集一覧</title>
<style>
body {
    font-family: sans-serif;
}
table {
    border-collapse: collapse;
    margin-bottom: 2em;
}
th, td {
    border: 1px solid #ccc;
    padding: 4px 8px;
}
th {
    background: #eee;
}
</style>
</head>
<body>
<h1>Wikipedia管理者最終編集一覧</h1>
""")

        # 更新日時
        jst = ZoneInfo("Asia/Tokyo")
        now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S %Z")
        fp.write(f"<p>更新日時: {html.escape(now)} </p>\n")

        for role, result in all_result.items():
            display_name = ROLE_NAMES.get(role) or role
            fp.write(f"<h2>{html.escape(display_name)}({role})</h2>\n")
            # fp.write(f"<h2>{html.escape(role)}</h2>\n")
            fp.write("<table>\n")

            if role == "bot":
                fp.write(
                    "<tr>"
                    "<th>利用者</th>"
                    "<th>最終編集日時</th>"
                    "<th>運用者</th>"
                    "<th>運用者最終編集</th>"
                    "</tr>\n"
                )
            else:
                fp.write("<tr><th>利用者</th><th>最終編集日時</th></tr>\n")

            for user, ts, operator, operator_ts in result:
                ts_str, old_style = format_ts(ts)
                op_ts_str, op_old_style = format_ts(operator_ts)

                url = f"https://ja.wikipedia.org/wiki/利用者:{user}"

                if operator:
                    op_url = f"https://ja.wikipedia.org/wiki/利用者:{operator}"
                    op_html = f"<a href='{op_url}'>{html.escape(operator)}</a>"
                else:
                    op_html = ""

                if role == "bot":
                    fp.write(
                        "<tr>"
                        f"<td><a href='{url}'>{html.escape(user)}</a></td>"
                        f"<td{old_style}>{html.escape(ts_str)}</td>"
                        f"<td>{op_html}</td>"
                        f"<td{op_old_style}>{html.escape(op_ts_str)}</td>"
                        "</tr>\n"
                    )
                else:
                    fp.write(
                        "<tr>"
                        f"<td><a href='{url}'>{html.escape(user)}</a></td>"
                        f"<td{old_style}>{html.escape(ts_str)}</td>"
                        "</tr>\n"
                    )

            fp.write("</table>\n")

        fp.write("</body>\n</html>\n")


def main():
    """main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", action="store_true", help="テストモード")
    args = parser.parse_args()

    if args.t:
        sleep_per_role = 30
        sleep_requests = 10
    else:
        sleep_per_role = 180
        sleep_requests = 10

    global ROLE_NAMES
    if args.t:
        ROLE_NAMES = {
            "suppress": "オーバーサイト",
            "bot": "BOT",
        }

    all_result = {}
    for role in ROLE_NAMES:
        all_result[role] = proc_role(role, sleep_requests, args)

        mysleep(sleep_per_role)

    write_html(all_result)
    print("report.html を出力しました")


if __name__ == "__main__":
    main()
