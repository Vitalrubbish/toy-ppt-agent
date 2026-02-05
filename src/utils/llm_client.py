import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError, APIStatusError
from openai.types.chat import ChatCompletionMessageParam

@dataclass
class LLMResponse:
    content: str
    usage: Optional[Dict[str, Any]] = None


class LLMClient:
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = provider
        if provider == "openai":
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            base_url = base_url or os.getenv("OPENAI_BASE_URL")
        elif provider == "moonshot":
            api_key = api_key or os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = base_url or os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
        elif provider == "deepseek":
            api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        if not api_key:
            raise EnvironmentError("API key is not set for provider")

        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

    def supports_vision(self) -> bool:
        env_flag = os.getenv("LLM_SUPPORTS_VISION")
        if env_flag is not None:
            return env_flag.strip().lower() in {"1", "true", "yes", "on"}
        return self.provider in {"openai"}

    def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float = 0.7,
        json_mode: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.5,
    ) -> LLMResponse:
        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                response_format = {"type": "json_object"} if json_mode else None
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                )
                content = response.choices[0].message.content or ""
                usage = response.usage.model_dump() if response.usage else None
                return LLMResponse(content=content, usage=usage)
            except (RateLimitError, APIConnectionError, APITimeoutError, APIStatusError) as err:
                last_err = err
                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)
                    continue
                raise
        if last_err:
            raise last_err
        raise RuntimeError("Unknown error in chat_completion")
    
    # Context Cost Calculation
    @staticmethod
    def calculate_context_cost(usage: Dict[str, Any]) -> float:
        """Calculate context cost based on token usage."""
        if not usage:
            return 0.0
        input_cost = usage.get("prompt_tokens", 0) * 0.0000025
        output_cost = usage.get("completion_tokens", 0) * 0.00001
        return input_cost + output_cost

    @staticmethod
    def encode_image(image_path: str) -> str:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")

    @staticmethod
    def build_image_content(image_path: str) -> Dict[str, Any]:
        b64 = LLMClient.encode_image(image_path)
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        }

    @staticmethod
    def safe_json_loads(text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
