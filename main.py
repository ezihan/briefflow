from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

# 既存のモジュール（news_analyzer.py）から関数とモデルを読み込む
from news_analyzer import fetch_nhk_news, analyze_news_with_ai, NewsEvaluation

load_dotenv()

app = FastAPI(
    title="BriefFlow API",
    description="AIパーソナライズド・ニュースアプリのバックエンドAPI",
    version="0.1.0"
)

# フロントエンド（Next.js等）からのアクセスを許可するCORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIが返す1記事あたりのデータ構造
class ArticleResponse(BaseModel):
    title: str
    link: str
    published: str
    evaluation: NewsEvaluation

@app.get("/api/news", response_model=list[ArticleResponse])
def get_personalized_news(limit: int = 3):
    """最新ニュースを取得し、AIによる要約と重要度ランクを付与して返すエンドポイント"""
    client = genai.Client()
    user_profile = "日本のIT業界への就職を目指している学生。AI技術、Web開発、経済動向に関心がある。"

    raw_articles = fetch_nhk_news(limit=limit)
    results = []

    for article in raw_articles:
        eval_result = analyze_news_with_ai(client, article, user_profile)
        results.append(
            ArticleResponse(
                title=article["title"],
                link=article["link"],
                published=article["published"],
                evaluation=eval_result
            )
        )
    return results
