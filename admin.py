#!/usr/bin/env python3

import time
import html
import requests
from datetime import datetime

API = "https://ja.wikipedia.org/w/api.php"


def get_admin_users(role):
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

        r = requests.get(API, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

        users.extend(u["name"] for u in data["query"]["allusers"])

        if "continue" not in data:
            break

        aufrom = data["continue"]["aufrom"]

    return users


def get_last_edit(user):
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": user,
        "uclimit": 1,
        "ucprop": "timestamp",
        "format": "json",
    }

    headers = {"User-Agent": "mybot/1.0"}

    r = requests.get(API, params=params, headers=headers)
    r.raise_for_status()
    data = r.json()

    contribs = data["query"]["usercontribs"]
    if not contribs:
        return None

    return contribs[0]["timestamp"]


def proc_role(role):
    users = get_admin_users(role)
    result = []

    for user in users:
        print(f"{role}: {user}")

        ts = get_last_edit(user)
        result.append((user, ts))

        print("sleep(30)")
        time.sleep(30)

    result.sort(key=lambda x: x[1] or "", reverse=True)

    return result


def write_html(all_result, filename="report.html"):
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
<h1>利用者最終編集一覧</h1>
""")

        for role, result in all_result.items():
            fp.write(f"<h2>{html.escape(role)}</h2>\n")
            fp.write("<table>\n")
            fp.write("<tr><th>利用者</th><th>最終編集日時</th></tr>\n")

            for user, ts in result:
                if ts:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                else:
                    ts_str = "編集なし"

                url = f"https://ja.wikipedia.org/wiki/利用者:{user}"

                fp.write(
                    "<tr>"
                    f"<td><a href='{url}'>{html.escape(user)}</a></td>"
                    f"<td>{html.escape(ts_str)}</td>"
                    "</tr>\n"
                )

            fp.write("</table>\n")

        fp.write("</body>\n</html>\n")


def main():
    # rolelist = ["rollbacker", "abusefilter"]
    rolelist = ["sysop", "bureaucrat", "suppress", "checkuser"]

    all_result = {}

    for role in rolelist:
        all_result[role] = proc_role(role)

        print("sleep(180)")
        time.sleep(180)

    write_html(all_result)
    print("report.html を出力しました")


if __name__ == "__main__":
    main()
