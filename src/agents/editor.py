import json
import os
from typing import Dict, List

from src.agents.base_agent import BaseAgent


EDITOR_SYSTEM_PROMPT = """
You are an expert Slidev Developer and Presentation Designer.
Transform raw text into beautiful, structured Slidev markdown slides.

Follow Slidev syntax strictly and output valid Slidev markdown only.
""".strip()


class EditorAgent(BaseAgent):
    def __init__(self, model_name: str = "gpt-4o", provider: str | None = None):
        provider = provider or os.getenv("EDITOR_LLM_PROVIDER") or "deepseek"
        super().__init__(role="Editor", model_name=model_name, provider=provider)
        self.set_system_prompt(EDITOR_SYSTEM_PROMPT)

    def generate_draft(self, raw_content: str) -> str:
        prompt = (
            "Please convert the following content into Slidev markdown slides. "
            "Return the full slides.md content only.\n\n"
            f"Content:\n{raw_content}\n"
        )
        response = self.chat(prompt)
        return response.content.strip()

    def refine_slides(self, current_code: str, feedback: List[Dict]) -> str:
        feedback_text = json.dumps(feedback, ensure_ascii=False, indent=2)
        prompt = (
            "Please refine the Slidev markdown according to the feedback. "
            "Return the full revised slides.md content only.\n\n"
            f"Current Slides:\n{current_code}\n\n"
            f"Feedback (JSON):\n{feedback_text}\n"
        )
        response = self.chat(prompt)
        return response.content.strip()
