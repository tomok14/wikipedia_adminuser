import pywikibot

site = pywikibot.Site()
print("site=", site)
page = pywikibot.Page(site, "利用者:Leaderbot")
print("page=", page)
text = page.text
print("text=", text)
page.text = text + "test"
