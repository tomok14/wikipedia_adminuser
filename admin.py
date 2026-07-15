#!/usr/bin/env python3
"""
Wikipedia/Wiktionary管理者の活動状況を調べる
"""

import time
import re
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import html
import requests
import mwparserfromhell

WIKIS = {
    "wikipedia": {
        "name": "Wikipedia",
        "api": "https://ja.wikipedia.org/w/api.php",
        "user_url": "https://ja.wikipedia.org/wiki/利用者:{}",
        "roles": {
            "sysop": "管理者",
            "bureaucrat": "ビューロクラット",
            "suppress": "オーバーサイト",
            "checkuser": "チェックユーザー",
            "bot": "BOT",
        },
    },
    "wiktionary": {
        "name": "Wiktionary",
        "api": "https://ja.wiktionary.org/w/api.php",
        "user_url": "https://ja.wiktionary.org/wiki/利用者:{}",
        "roles": {
            "sysop": "管理者",
            "bureaucrat": "ビューロクラット",
            "bot": "BOT",
        },
    },
}


def mysleep(sec):
    """sleep"""
    print(f"sleep({sec})")
    time.sleep(sec)


#!/usr/bin/env python3


TITLE = "Wikipedia:Bot/ステータス"


def get_bot_operator_by_table(bot_name: str, api_url: str) -> str | None:
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

    r = requests.get(api_url, params=params, headers=headers, timeout=30)
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


def get_bot_operator_global(user, sleep_requests):
    """グローバル利用者ページ (meta) からBot運用者を取得する"""

    meta_api = "https://meta.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": f"User:{user}",
        "rvprop": "content",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json",
    }
    headers = {"User-Agent": "mybot/1.0"}

    mysleep(sleep_requests)
    r = requests.get(meta_api, params=params, headers=headers, timeout=10.0)
    r.raise_for_status()
    data = r.json()

    pages = data["query"]["pages"]
    if not pages:
        return None

    revisions = pages[0].get("revisions")
    if not revisions:
        return None

    text = revisions[0]["slots"]["main"]["content"]

    m = re.search(
        r"\{\{\s*Bot\b(?:(?!\}\}).)*?\|\s*(?![^|}]*=)([^|}\n]+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        print(f"operator found on meta. from {{{{BOT}}}}: {m.group(1).strip()}")
        return m.group(1).strip()

    m = re.search(
        r"\|\s*運用者\s*=\s*\[\[(?:[Uu]ser:|利用者:)?([^|\]]+)",
        text,
    )
    if m:
        print(f"operator found on meta. from 運用者: {m.group(1).strip()}")
        return m.group(1).strip()

    return None


def get_bot_operator(user, sleep_requests, api_url, wiki_key):
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
    r = requests.get(api_url, params=params, headers=headers, timeout=10.0)
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
    m = re.search(
        r"\{\{\s*Bot\b(?:(?!\}\}).)*?\|\s*(?![^|}]*=)([^|}\n]+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        print(f"operator found. from {{{{BOT}}}}: {m.group(1).strip()}")
        return m.group(1).strip()

    # Wiktionary用
    # {{User Bot|Akas1950}}から持ってくる
    m = re.search(
        r"\{\{\s*User Bot\b(?:(?!\}\}).)*?\|\s*(?![^|}]*=)([^|}\n]+)",
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

    operator = get_bot_operator_global(user, sleep_requests)
    if operator:
        return operator

    if wiki_key == "wikipedia":
        operator = get_bot_operator_by_table(user, api_url)
        if operator:
            return operator

    print(f"operator not found. {user}")
    return None


def get_admin_users(role, sleep_requests, api_url):
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
        r = requests.get(api_url, params=params, headers=headers, timeout=10.0)
        r.raise_for_status()
        data = r.json()

        users.extend(u["name"] for u in data["query"]["allusers"])

        if "continue" not in data:
            break

        aufrom = data["continue"]["aufrom"]

    return users


def get_last_edit(user, sleep_requests, api_url):
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
    r = requests.get(api_url, params=params, headers=headers, timeout=10.0)
    r.raise_for_status()
    data = r.json()

    contribs = data["query"]["usercontribs"]
    if not contribs:
        return None

    return contribs[0]["timestamp"]


def proc_role(role, sleep_requests, args, wiki_config, wiki_key):
    """role毎の処理"""
    api_url = wiki_config["api"]
    users = get_admin_users(role, sleep_requests, api_url)
    result = []

    for i, user in enumerate(users):
        print(f"{i}, {role}: {user}")

        if args.t:
            if i > 2:
                break

        ts = get_last_edit(user, sleep_requests, api_url)

        operator = None
        operator_ts = None

        if role == "bot":
            operator = get_bot_operator(user, sleep_requests, api_url, wiki_key)

            if operator:
                operator_ts = get_last_edit(operator, sleep_requests, api_url)

        result.append((user, ts, operator, operator_ts))

        mysleep(sleep_requests)

    result.sort(key=lambda x: x[1] or "", reverse=True)

    return result


def format_ts(ts):
    """日時のフォーマット"""
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


def write_html(all_result, wikis_config, filename="report.html"):
    """最終html生成"""
    with open(filename, "w", encoding="utf-8") as fp:
        fp.write("""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>利用者最終編集一覧</title>
<style>
body {
    font-family: sans-serif;
    margin: 0;
}
#wrapper {
    display: flex;
}
#sidebar {
    width: 220px;
    min-width: 220px;
    background: #f8f9fa;
    padding: 16px;
    border-right: 1px solid #ccc;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
    box-sizing: border-box;
}
#sidebar h2 {
    font-size: 16px;
    margin: 0 0 12px;
}
#sidebar ul {
    list-style: none;
    padding: 0;
    margin: 0;
}
#sidebar li {
    margin-bottom: 6px;
}
#sidebar a {
    text-decoration: none;
    color: #0645ad;
}
#sidebar a:hover {
    text-decoration: underline;
}
#content {
    flex: 1;
    padding: 16px 24px;
    min-width: 0;
}
table {
    border-collapse: collapse;
    margin-bottom: 2em;
}
th, td {
    border: 1px solid #ccc;
    padding: 4px 8px;
    white-space: nowrap;
}
th {
    background: #eee;
}
.table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
#menu-toggle {
    display: none;
    background: #f8f9fa;
    border: 1px solid #ccc;
    padding: 8px 16px;
    font-size: 16px;
    cursor: pointer;
    margin: 8px;
    border-radius: 4px;
}
@media (max-width: 768px) {
    #wrapper {
        flex-direction: column;
    }
    #sidebar {
        width: 100%;
        min-width: unset;
        height: auto;
        position: relative;
        border-right: none;
        border-bottom: 1px solid #ccc;
        display: none;
    }
    #sidebar.open {
        display: block;
    }
    #menu-toggle {
        display: inline-block;
    }
    #content {
        padding: 12px;
    }
    table {
        width: 100%;
    }
    th, td {
        padding: 4px 6px;
    }
}
</style>
</head>
<body>
<button id="menu-toggle" onclick="document.getElementById('sidebar').classList.toggle('open')">&#9776; 目次</button>
<div id="wrapper">
<nav id="sidebar">
<h2>目次</h2>
<ul>
""")

        for wiki_key, roles_result in all_result.items():
            wiki_name = wikis_config[wiki_key]["name"]
            fp.write(f"<li><strong>{html.escape(wiki_name)}</strong></li>\n")
            for role in roles_result:
                display_name = wikis_config[wiki_key]["roles"].get(role) or role
                fp.write(
                    f'<li style="margin-left:1em;">'
                    f'<a href="#{wiki_key}-{role}">{html.escape(display_name)}({role})</a></li>\n'
                )

        fp.write("""</ul>
</nav>
<div id="content">
<h1>管理者最終編集一覧</h1>
""")

        # 更新日時
        jst = ZoneInfo("Asia/Tokyo")
        now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S %Z")
        fp.write(f"<p>更新日時: {html.escape(now)} </p>\n")
        fp.write(
            '<p style="color:#c00;font-weight:bold">※赤色の背景は最終編集から1年以上経過していることを示します</p>\n'
        )

        for wiki_key, roles_result in all_result.items():
            wiki_name = wikis_config[wiki_key]["name"]
            user_url_template = wikis_config[wiki_key]["user_url"]
            roles = wikis_config[wiki_key]["roles"]

            fp.write(f'<h2 id="{wiki_key}">{html.escape(wiki_name)}</h2>\n')

            for role, result in roles_result.items():
                display_name = roles.get(role) or role
                fp.write(
                    f'<h3 id="{wiki_key}-{role}">{html.escape(display_name)}({role})</h3>\n'
                )
                fp.write('<div class="table-wrap">\n<table>\n')

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

                    url = user_url_template.format(user)

                    if operator:
                        op_url = user_url_template.format(operator)
                        op_html = f"<a href='{op_url}' target='_blank'>{html.escape(operator)}</a>"
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

                fp.write("</table>\n</div>\n")

        fp.write("</div>\n</div>\n</body>\n</html>\n")


def main():
    """main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", action="store_true", help="テストモード")
    parser.add_argument(
        "--wiki",
        choices=["wikipedia", "wiktionary", "all"],
        default="all",
        help="対象ウィキ (default: all)",
    )
    args = parser.parse_args()

    if args.t:
        sleep_per_role = 30
        sleep_requests = 10
    else:
        sleep_per_role = 180
        sleep_requests = 10

    # 対象ウィキを選択
    if args.wiki == "all":
        target_wikis = WIKIS
    else:
        target_wikis = {args.wiki: WIKIS[args.wiki]}

    all_result = {}
    for wiki_key, wiki_config in target_wikis.items():
        print(f"\n=== {wiki_config['name']} ===")
        all_result[wiki_key] = {}
        for role in wiki_config["roles"]:
            all_result[wiki_key][role] = proc_role(
                role, sleep_requests, args, wiki_config, wiki_key
            )
            mysleep(sleep_per_role)

    write_html(all_result, WIKIS)
    print("report.html を出力しました")


if __name__ == "__main__":
    main()
