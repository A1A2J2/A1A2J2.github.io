import re
import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import asyncio

URL_REGEX = re.compile(r'(https?://[^\s]+)')

async def fetch_url_content(url: str) -> str:
    """Fetches text content from a URL."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract text, remove scripts and styles
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)
            # Truncate to avoid blowing up context window
            return text[:4000]
    except Exception as e:
        return f"[Failed to fetch {url}: {str(e)}]"

async def search_web(query: str) -> str:
    """Searches DuckDuckGo and returns a summary."""
    try:
        # DDGS is synchronous, so we run it in a thread
        def do_search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                return results
        
        results = await asyncio.to_thread(do_search)
        if not results:
            return ""
        
        context = "Web Search Results:\n"
        for i, res in enumerate(results):
            context += f"{i+1}. {res.get('title', '')} ({res.get('href', '')}): {res.get('body', '')}\n"
        return context
    except Exception as e:
        return f"[Web search failed: {str(e)}]"

async def enhance_with_internet(message: str) -> str:
    """Enhances a user message with internet context if URLs are present or searching is requested."""
    urls = URL_REGEX.findall(message)
    context = ""
    
    if urls:
        # Fetch all URLs found in the message
        tasks = [fetch_url_content(url) for url in urls[:3]] # limit to 3 URLs
        results = await asyncio.gather(*tasks)
        context += "Context from provided URLs:\n"
        for url, text in zip(urls[:3], results):
            context += f"--- Content from {url} ---\n{text}\n\n"
            
    # Simple heuristic: if message asks to "search" or "look up" or "latest", do a web search
    search_keywords = ["search the web", "look up", "latest news", "search for", "who is", "what is the current"]
    if any(kw in message.lower() for kw in search_keywords) and not urls:
        search_results = await search_web(message)
        context += search_results + "\n\n"

    if context:
        return f"{context}User Message: {message}"
    
    return message
