from exa_py import AsyncExa
from exa_py.api import ResultWithText, SearchResponse

from app.core.config import settings

exa_client = AsyncExa(settings.exa_api_key)


async def web_search(
    query: str,
    num_results: int = 3,
) -> str:
    """Searches the web for up-to-date current events/news, unfamiliar topics/concepts, \
       source gathering, and fact-checking.

       Args:
           query: Specific search query.
           num_results: Number of results (default 3, e.g., 1-10). Use fewer (1-2) for quick facts, more (6-10) for in-depth research. Maximum is 10.

       Returns:
           A string contains concatenated search results. Each result includes URL, TITLE, DATE, CONTENT with a max length of 500 characters.
    )
    """
    response: list[SearchResponse[ResultWithText]] = await exa_client.search_and_contents(
        query, text=True, num_results=num_results, type="auto"
    )
    results: list[ResultWithText] = response.results

    docs = [
        f"URL: {r.url}\nTITLE: {r.title}\nDATE: {r.published_date}\nCONTENT:\n{(r.text)[:500].strip()}"
        for r in results
    ]
    return "\n---\n".join(docs)
