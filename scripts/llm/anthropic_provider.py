import os
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from .base import LLMProvider

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

    def generate_review(self, problem_statement: str, solution_code: str, language: str) -> str:
        system_prompt = \"\"\"
        You are an expert Data Structures and Algorithms software engineer conducting a code review.
        Your goal is to provide concise, direct feedback on the provided solution to a coding problem.
        Focus on:
        1. Time and Space Complexity Analysis (O-notation).
        2. Any bugs, edge cases not handled, or performance bottlenecks.
        3. The optimal approach (if this solution isn't already optimal) and how to improve it.
        4. Provide the code for the optimal approach if applicable.
        
        Format your output strictly in Markdown. Keep it structured and easy to read.
        \"\"\"
        
        user_prompt = f\"\"\"
        Here is the problem statement:
        {problem_statement}
        
        Here is my solution ({language}):
        ```{language}
        {solution_code}
        ```
        
        Please review it.
        \"\"\"
        
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
        return response.content[0].text
