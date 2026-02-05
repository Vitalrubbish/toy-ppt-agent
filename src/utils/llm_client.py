import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError, APIStatusError

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
    


    @staticmethod
    def _convert_messages_for_responses(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            text_type = "output_text" if role == "assistant" else "input_text"
            if isinstance(content, list):
                parts: List[Dict[str, Any]] = []
                for part in content:
                    if not isinstance(part, dict):
                        parts.append({"type": text_type, "text": str(part)})
                        continue
                    part_type = part.get("type")
                    if part_type == "text":
                        parts.append({"type": text_type, "text": part.get("text", "")})
                        continue
                    if part_type == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        if image_url:
                            parts.append({"type": "input_image", "image_url": image_url})
                        continue
                    if part_type in {"input_text", "input_image", "output_text"}:
                        parts.append(part)
                        continue
                    parts.append({"type": text_type, "text": json.dumps(part, ensure_ascii=False)})
                converted.append({"role": role, "content": parts})
            else:
                converted.append(
                    {"role": role, "content": [{"type": text_type, "text": str(content)}]}
                )
        return converted


    def supports_vision(self) -> bool:
        env_flag = os.getenv("LLM_SUPPORTS_VISION")
        if env_flag is not None:
            return env_flag.strip().lower() in {"1", "true", "yes", "on"}
        return self.provider in {"openai"}
    
    

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.3,
        json_mode: bool = False,
        reasoning_effort: Optional[str] = None,
        max_retries: int = 5,
        retry_delay: float = 2,
    ) -> LLMResponse:
        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                response_format = {"type": "json_object"} if json_mode else None
                if not reasoning_effort:
                    reasoning_effort = "low"

                use_reasoning = (
                    reasoning_effort
                    and self.provider == "openai"
                    and model.startswith("gpt-5")
                    and hasattr(self.client, "responses")
                )

                # Reasoning
                if use_reasoning:
                    print(f"{model}: Deep Reasoning...")
                    start_dr = time.time()
                    input_payload = self._convert_messages_for_responses(messages)
                    response = self.client.responses.create(
                        model=model,
                        input=input_payload,
                        reasoning={"effort": reasoning_effort},
                    )

                    content = getattr(response, "output_text", None) or ""
                    if not content:
                        try:
                            for item in response.output[0].content:
                                text = getattr(item, "text", None)
                                if text:
                                    content = text
                                    break
                        except Exception:
                            content = ""

                    usage = response.usage.model_dump() if response.usage else None

                    print(f"Deep Reasoning Time: {time.time() - start_dr:.2f}s")
                    return LLMResponse(content=content, usage=usage)

                # Normal Chat Completion
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
    def calculate_context_cost(input_tokens: int = 0, output_tokens: int = 0) -> float:
        return input_tokens * 0.00000125 + output_tokens * 0.00001

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
