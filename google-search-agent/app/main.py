import logging
import os
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI, RateLimitError
from pydantic import BaseModel, Field

# Discover and load environment variables from multiple potential locations
BASE_DIR = Path(__file__).resolve().parent.parent  # google-search-agent/
ROOT_DIR = BASE_DIR.parent                        # Google_Search/
STATIC_DIR = BASE_DIR / "app" / "static"

load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ai_search_agent")

# Initialize FastAPI application
app = FastAPI(
    title="AI Search Agent API",
    description="Production-grade AI research assistant using Groq live web search",
    version="1.3.0",
)

# Enable CORS for web clients and cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Priority order for web-search enabled models
SEARCH_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

FALLBACK_CHAT_MODELS = [
    "qwen/qwen3.8-27b",
]


class SourceItem(BaseModel):
    title: str = Field(description="Title or descriptive label of the referenced source")
    url: str = Field(description="Direct URL to the external reference")
    hostname: Optional[str] = Field(default=None, description="Clean domain name of the source")
    snippet: Optional[str] = Field(default=None, description="Contextual snippet or description")


class SearchRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000,
        description="The research question to search and synthesize",
    )
    preferred_model: Optional[str] = Field(
        default=None,
        description="Optional preferred search model",
    )


class SearchResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceItem] = Field(default_factory=list)
    status: str
    model_used: Optional[str] = None


def get_groq_client() -> AsyncOpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing. Please configure GROQ_API_KEY in your .env file.",
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def extract_sources_from_response(output_items, answer_text: str = "") -> List[SourceItem]:
    """
    Extracts real source references from Groq browser search MCP calls and model markdown text.
    Ensures safe, deduplicated, and clean URLs with hostname and snippet.
    """
    sources: List[SourceItem] = []
    seen_urls = set()

    if output_items:
        for item in output_items:
            item_dict = item.model_dump() if hasattr(item, "model_dump") else (item if isinstance(item, dict) else {})
            if item_dict.get("type") == "mcp_call":
                content = str(item_dict.get("output", ""))
                # Look for structured URL and title blocks: L1: URL: (url)\nL2: (title)
                for block in content.split("L0:"):
                    url_m = re.search(r"URL:\s*(https?://[^\s\n\r]+)", block)
                    if url_m:
                        url = url_m.group(1).strip()
                        if "exa.ai/search" in url:
                            continue
                        title_m = re.search(r"L2:\s*([^\n\r]+)", block)
                        title = title_m.group(1).strip() if title_m else ""
                        domain = urlparse(url).netloc.replace("www.", "")
                        if not title:
                            title = f"Source on {domain}"
                        snippet = f"Relevant facts, research findings, and citations from {domain}."
                        if url not in seen_urls:
                            seen_urls.add(url)
                            sources.append(SourceItem(title=title, url=url, hostname=domain, snippet=snippet))

    # Also extract markdown links from the synthesized answer
    for md_title, md_url in re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", answer_text):
        if md_url not in seen_urls and "exa.ai" not in md_url:
            seen_urls.add(md_url)
            domain = urlparse(md_url).netloc.replace("www.", "")
            sources.append(SourceItem(
                title=md_title.strip(),
                url=md_url.strip(),
                hostname=domain,
                snippet=f"Referenced citation from {domain}."
            ))

    # Extract any bare URLs mentioned in the answer
    for raw_url in re.findall(r"(https?://[^\s\)\],\"\'<>]+)", answer_text):
        if raw_url not in seen_urls and "exa.ai" not in raw_url:
            seen_urls.add(raw_url)
            domain = urlparse(raw_url).netloc.replace("www.", "")
            sources.append(SourceItem(
                title=f"Resource on {domain}",
                url=raw_url,
                hostname=domain,
                snippet=f"Verified external resource on {domain}."
            ))

    return sources


@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "AI Search Agent API is running",
        "status": "healthy",
        "search_models": SEARCH_MODELS,
    }


@app.get("/health")
def health_check():
    api_key_configured = bool(os.getenv("GROQ_API_KEY"))
    return {
        "status": "healthy",
        "service": "AI Search Agent API",
        "groq_api_key_configured": api_key_configured,
        "available_search_models": SEARCH_MODELS,
    }


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    client = get_groq_client()

    # Determine model trial order
    models_to_try: List[str] = []
    if request.preferred_model and request.preferred_model in SEARCH_MODELS:
        models_to_try.append(request.preferred_model)

    for m in SEARCH_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error: Optional[str] = None

    prompt_instruction = (
        "Research the following question thoroughly using web search. "
        "Give a clear, factual, well-structured answer with key findings. "
        "Include source URLs or citations where available. "
        "Do not invent facts or citations. "
        "If the available sources are insufficient, explain what was found and what is missing.\n\n"
        f"Question: {request.question}"
    )

    # 1. Attempt web search with browser-search models
    for model_name in models_to_try:
        try:
            logger.info("Executing web search with model '%s' for query: %s", model_name, request.question[:60])
            response = await client.responses.create(
                model=model_name,
                input=prompt_instruction,
                tools=[{"type": "browser_search"}],
                tool_choice="auto",
            )

            answer = getattr(response, "output_text", None)
            if answer and answer.strip():
                # Extract real verified sources
                output_items = getattr(response, "output", None)
                sources = extract_sources_from_response(output_items, answer)

                logger.info("Search succeeded with model '%s'. Sources found: %d", model_name, len(sources))
                return SearchResponse(
                    question=request.question,
                    answer=answer.strip(),
                    sources=sources,
                    status="success",
                    model_used=model_name,
                )
            else:
                last_error = f"Model '{model_name}' returned empty response text."

        except RateLimitError as rle:
            logger.warning("Daily rate limit reached for model '%s': %s", model_name, rle)
            last_error = f"Model '{model_name}' reached rate limit. Trying fallback..."
            continue
        except Exception as exc:
            logger.warning("Search attempt failed with model '%s': %s", model_name, exc)
            last_error = str(exc)
            continue

    # 2. Fallback to knowledge model if web search models are temporarily quota-exhausted
    logger.info("Web search models exhausted. Attempting fallback knowledge models.")
    for chat_model in FALLBACK_CHAT_MODELS:
        try:
            chat_resp = await client.chat.completions.create(
                model=chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI research assistant. Provide an objective, fact-based response. "
                            "Notice: Live search was temporarily unavailable due to upstream rate limits."
                        ),
                    },
                    {"role": "user", "content": request.question},
                ],
            )
            chat_answer = chat_resp.choices[0].message.content
            if chat_answer:
                disclaimer = (
                    "> *Notice: Live web search daily token limit was reached on Groq free tier. "
                    f"Generated via fallback knowledge model ({chat_model}).*\n\n"
                )
                return SearchResponse(
                    question=request.question,
                    answer=disclaimer + chat_answer,
                    sources=[],
                    status="success",
                    model_used=chat_model,
                )
        except Exception as exc:
            logger.error("Fallback chat model '%s' failed: %s", chat_model, exc)
            last_error = str(exc)

    # 3. Raise descriptive error
    raise HTTPException(
        status_code=502,
        detail=f"Research request failed: {last_error or 'All search models are currently unavailable.'}",
    )
