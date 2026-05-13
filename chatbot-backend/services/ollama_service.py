import httpx
from config import settings
from typing import List, Dict

async def generate_response(model: str, messages: List[Dict[str, str]]):
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            # Transform to the expected format to match existing code
            return {"response": data.get("message", {}).get("content", "")}
        except httpx.TimeoutException:
            return {"error": "timeout"}
        except httpx.RequestError:
            return {"error": "unavailable"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": "not_found"}
            return {"error": "server_error"}
