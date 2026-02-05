import os
from typing import Any, Dict, List, Optional

from utils.llm_client import LLMClient, LLMResponse


class BaseAgent:
    def __init__(self, role: str, model_name: str = "gpt-5.1", provider: Optional[str] = None):
        self.role = role
        self.model_name = model_name
        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        base_url = os.getenv("LLM_BASE_URL")
        self.llm_client = LLMClient(provider=provider, base_url=base_url)
        self.system_prompt: str = ""
        self.history: List[Dict[str, Any]] = []
        self.last_response: Optional[str] = None

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def reset_history(self) -> None:
        self.history = []

    def _build_messages(
        self, user_content: str, image_paths: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # Previous conversation history
        for item in self.history:
            if "user" in item:
                messages.append({"role": "user", "content": item["user"]})
            if "assistant" in item:
                messages.append({"role": "assistant", "content": item["assistant"]})

        if image_paths and self.llm_client.supports_vision():
            content: List[Dict[str, Any]] = [{"type": "text", "text": user_content}]
            for path in image_paths:
                content.append(self.llm_client.build_image_content(path))
            messages.append({"role": "user", "content": content})
        else:
            if image_paths:
                user_content = (
                    "Note: Image inputs are not supported by the current provider. "
                    "Please review based on the text content only.\n\n"
                    + user_content
                )
            messages.append({"role": "user", "content": user_content})

        return messages

    def chat(
        self, user_content: str, image_paths: Optional[List[str]] = None, json_mode: bool = False
    ) -> LLMResponse:
        messages = self._build_messages(user_content, image_paths=image_paths)
        response = self.llm_client.chat_completion(
            messages=messages, model=self.model_name, json_mode=json_mode
        )
        self.history.append({"user": user_content, "assistant": response.content})
        self.last_response = response.content
        self.last_response_usage = response.usage
        return response