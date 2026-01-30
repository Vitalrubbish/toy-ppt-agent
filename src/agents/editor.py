import json
import os
from typing import Dict, List

from src.agents.base_agent import BaseAgent


EDITOR_SYSTEM_PROMPT = """
You are an expert Slidev Developer and Presentation Designer.
Transform raw text into beautiful, structured Slidev markdown slides.

Follow Slidev syntax strictly and output valid Slidev markdown only.

Requirements:
1) Always start with a dedicated title slide that explicitly shows title, subtitle, author/affiliation, and date.
2) Do NOT assume frontmatter automatically renders a title page; add an explicit title slide after the frontmatter.
3) Always end with a Thank You or Q&A slide.
4) Keep a unified visual style across all middle content slides.
5) Use appropriate font sizes; avoid tiny text.
6) Limit text on each slide to 50 words maximum.
7) Use Slidev layouts correctly: `layout` belongs in a slide frontmatter block immediately after `---`.
8) When using slidev layouts, there isn't any empty lines between `---` and the layout declaration, and you must have an extra '---' block right after the layout declaration.
9) Do not declare multiple layouts in one slide; create a new slide instead.
10) For two-column layouts, use `layout: two-cols` and `::right::` blocks correctly.
11) You are encouraged to use two-cols layout to enhance visual appeal whenever suitable.
12) You are encouraged to insert a properly sized Mermaid flowchart or a data form to improve clarity whenever helpful.
13) Make the presentation sufficiently detailed; prefer adding slides over sparse content.
""".strip()


class EditorAgent(BaseAgent):
    def __init__(self, model_name: str = "gpt-4o", provider: str | None = None):
        provider = provider or os.getenv("EDITOR_LLM_PROVIDER") or "deepseek"
        super().__init__(role="Editor", model_name=model_name, provider=provider)
        self.set_system_prompt(EDITOR_SYSTEM_PROMPT)

    def generate_outline(self, raw_content: str) -> str:
        prompt = (
            "Create a detailed presentation outline in Markdown. "
            "Include slide order, slide titles, key points (2-4 bullets each), "
            "suggested layout, and any recommended Mermaid diagrams. "
            "Return the outline only.\n\n"
            f"Content:\n{raw_content}\n"
        )
        response = self.chat(prompt)
        return response.content.strip()

    def generate_draft(self, raw_content: str, outline: str | None = None) -> str:
        prompt = (
            "Please convert the following content into Slidev markdown slides. "
            "Ensure the deck is sufficiently detailed by using more slides rather than sparse text. "
            "Return the full slides.md content only.\n\n"
        )
        if outline:
            prompt += f"Outline:\n{outline}\n\n"
        prompt += f"Content:\n{raw_content}\n"
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

    def fix_slides(self, current_code: str, render_error: str) -> str:
        prompt = (
            "The Slidev render failed. Fix the Slidev markdown so it renders successfully. "
            "Only correct syntax, layout, or component usage errors and keep the content intact. "
            "Return the full corrected slides.md content only.\n\n"
            f"Render Error:\n{render_error}\n\n"
            f"Current Slides:\n{current_code}\n"
        )
        response = self.chat(prompt)
        return response.content.strip()
