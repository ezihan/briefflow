from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

from news_analyzer import fetch_nhk_news, analyze_news_with_ai, NewsEvaluation
# 👇 新增：引入刚刚写好的 SQL 数据库操作函数
from database import init_db, get_cached_evaluation, save_evaluation_to_db

load_dotenv()

# サーバー起動時にSQLiteデータベースとテーブルを自動作成
init_db()

app = FastAPI(
    title="BriefFlow API",
    description="AIパーソナライズド・ニュースアプリのバックエンドAPI（SQLキャッシュ対応）",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ArticleResponse(BaseModel):
    title: str
    link: str
    published: str
    evaluation: NewsEvaluation

@app.get("/api/news", response_model=list[ArticleResponse])
def get_personalized_news(limit: int = 3):
    client = genai.Client()
    user_profile = "日本のIT業界への就職を目指している学生。AI技術、Web開発、経済動向に関心がある。"

    raw_articles = fetch_nhk_news(limit=limit)
    results = []

    for article in raw_articles:
        # 1. まずSQLデータベースにキャッシュがあるか確認（SELECT）
        cached_eval = get_cached_evaluation(article["link"])

        if cached_eval:
            print(f"⚡ [SQL Cache Hit] DBから高速取得: {article['title'][:20]}...")
            eval_result = cached_eval
        else:
            # 2. DBに無い新しいニュースだけAIを呼び出し（コストと時間の節約！）
            print(f"🆕 [New Article] AIで新規分析中: {article['title'][:20]}...")
            eval_result = analyze_news_with_ai(client, article, user_profile)
            # 3. 分析結果をSQLデータベースに保存（INSERT）
            save_evaluation_to_db(article, eval_result)

        results.append(
            ArticleResponse(
                title=article["title"],
                link=article["link"],
                published=article["published"],
                evaluation=eval_result
            )
        )
    return results
