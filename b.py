import re

text = """
*どうしてもメールを送りたい⇒[[#ほんとうにメールを送りますか？|利用者:{{PAGENAMEE}}にメールを送信]]
など、目的に応じて各ページへお進みください。（[[特別:会話ページ|自分の会話ページに戻る]]）}}
<center>This user account is a [[Wikipedia:Bot|bot]] operated by [[user:Triglav|Triglav]] ([[User talk:Triglav|talk]]).</center>
{{bot|Triglav|site=ja}}

<center>''雑用でないBot作業って何だろう・・・''</center>
"""
m = re.search(
    r"\{\{\s*Bot\s*\|\s*([^|}\n]+)",
    text,
    flags=re.IGNORECASE | re.DOTALL,
)
if m:
    print(m.group(1).strip())
