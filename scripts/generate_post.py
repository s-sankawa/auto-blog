import os
import random
import requests
from datetime import datetime
from openai import OpenAI

# 環境変数からキーを取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# トピックファイルからランダムに1つ選ぶ
with open("topics.txt", "r", encoding="utf-8") as f:
    topics = [line.strip() for line in f if line.strip()]
topic = random.choice(topics)

# --- Step 1: Serper でニュース検索（上位1件のみ） ---
print(f"Searching news for topic: {topic}")

search_url = "https://google.serper.dev/news"
headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
payload = {"q": topic, "num": 1}  # 上位1件

res = requests.post(search_url, headers=headers, json=payload)
res.raise_for_status()
results = res.json()

# ニュース記事を整形
if "news" in results and results["news"]:
    item = results["news"][0]
    news_content = f"- {item.get('title', '')}\n  {item.get('snippet', '')}\n  Source: {item.get('link', '')}"
else:
    news_content = "ニュースは見つかりませんでした。"

# --- Step 2: OpenAI に記事生成を依頼 ---
prompt = f"""
以下のトピックに関する最新ニュースをもとに、読みやすいブログ記事を作成してください。
トピック: {topic}

ニュース内容:
{news_content}

条件:
- 記事は日本語
- 1件のニュースを中心に構成
- 最新商品の紹介や特徴を含める
- Markdown形式で見出し(h2,h3)を使う
- ファンに役立つ豆知識やポイントを加える
- 最後にまとめを記載
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
)

article = response.choices[0].message.content

# --- Step 3: Markdownファイルとして保存 ---
date_str = datetime.now().strftime("%Y-%m-%d")
file_name = f"_posts/{date_str}-{topic.replace(' ', '-')}.md"

os.makedirs("_posts", exist_ok=True)
with open(file_name, "w", encoding="utf-8") as f:
    f.write(f"---\n")
    f.write(f"title: \"{topic} 最新ニュースまとめ\"\n")
    f.write(f"date: {date_str}\n")
    f.write(f"layout: post\n")
    f.write(f"---\n\n")
    f.write(article)

print(f"Generated post saved to {file_name}")
