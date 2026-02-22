import os
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from .base import LLMProvider, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from typing import Tuple

class AnthropicProvider(LLMProvider):
    def __init__(self):
        if Anthropic is None:
            raise ImportError("The 'anthropic' package is required but not installed. Run `pip install anthropic`.")
            
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
            
        self.client = Anthropic(api_key=self.api_key)
        self.model_name = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest").strip()
        self.temperature = float(os.environ.get("ANTHROPIC_TEMPERATURE", "0.2"))

    def generate_review(self, problem_statement: str, solution_code: str, language: str) -> Tuple[str, int, int]:
        system_prompt = SYSTEM_PROMPT
        user_prompt = USER_PROMPT_TEMPLATE.format(
            problem_statement=problem_statement,
            language=language,
            solution_code=solution_code
        )
        
        print(f"Sending request to Anthropic ({self.model_name})...")
        
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        in_tokens = response.usage.input_tokens if response.usage else 0
        out_tokens = response.usage.output_tokens if response.usage else 0
        return response.content[0].text, in_tokens, out_tokens
