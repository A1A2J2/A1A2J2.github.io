import httpx
from config import settings

async def generate_response(model: str, prompt: str):
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"error": "timeout"}
        except httpx.RequestError:
            return {"error": "unavailable"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": "not_found"}
            return {"error": "server_error"}
