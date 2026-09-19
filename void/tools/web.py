import requests
from ..config import Config


class WebSearch:

    MAX_RESULTS = 5
    MAX_CONTENT_PER_RESULT = 1600
    MAX_TOTAL_CONTENT = 8000

    def __init__(self):
        self.api_key = Config.JINA_API_KEY

    def search(self, query):

        if not self.api_key:
            raise RuntimeError(
                "JINA_API_KEY is not set"
            )

        response = requests.get(
            Config.JINA_URL,
            params={"q": query},
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            },
            timeout=(15, 60)
        )

        response.raise_for_status()

        data = response.json()

        results = []
        total_content = 0

        for item in data.get("data", []):

            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("content", "")

            if not isinstance(content, str):
                content = str(content)

            remaining = (
                self.MAX_TOTAL_CONTENT
                - total_content
            )

            if remaining <= 0:
                break

            limit = min(
                self.MAX_CONTENT_PER_RESULT,
                remaining
            )

            content = content[:limit].strip()

            if len(content) == limit:
                content += "..."

            total_content += len(content)

            results.append({
                "title": title,
                "url": url,
                "content": content
            })

            if len(results) >= self.MAX_RESULTS:
                break

        return results
