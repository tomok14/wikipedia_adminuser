import admin

# user = "EmausBot"
# user = "Trgbot"
# user = "KiranBOT"
user = "OctraBot"
# result = admin.get_bot_operator_global(user, 1)
sleep_requests = 1
api_url = "https://ja.wiktionary.org/w/api.php"
wiki_key = "Wiktionary"
result = admin.get_bot_operator(user, sleep_requests, api_url, wiki_key)
print(result)
