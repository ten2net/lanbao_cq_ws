import json
import httpx
from typing import AsyncGenerator
from config import HERMES_API_KEY, HERMES_BASE_URL


class HermesService:
    def __init__(self):
        self.base_url = HERMES_BASE_URL.rstrip("/")
        self.api_key = HERMES_API_KEY

    async def stream_completion(self, prompt: str, model: str = "gemma-4-12b") -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True
                },
                timeout=300
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Hermes API error {response.status_code}: {error_text.decode()}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
