import os
from openai import OpenAI
from .base import LLMProvider, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = os.environ.get("OPENAI_MODEL", "o3-mini").strip()
        # Explicit config: set OPENAI_SUPPORTS_TEMPERATURE=false for reasoning/codex models (o1, o3, codex, etc.)
        self.supports_temperature = os.environ.get("OPENAI_SUPPORTS_TEMPERATURE", "true").strip().lower() == "true"

    def generate_review(self, problem_statement: str, solution_code: str, language: str) -> str:
        system_prompt = SYSTEM_PROMPT
        user_prompt = USER_PROMPT_TEMPLATE.format(
            problem_statement=problem_statement,
            language=language,
            solution_code=solution_code
        )
        
        print(f"Sending request to OpenAI ({self.model_name})...")
        
        try:
            # Route models that specifically require the new responses endpoint (codex, pro, or any gpt-5 that isn't a standard chat model)
            if "codex" in self.model_name or "pro" in self.model_name or ("gpt-5" in self.model_name and "chat" not in self.model_name):
                prompt = f"INSTRUCTIONS:\n{system_prompt}\n\nINPUT:\n{user_prompt}"
                res = self.client.responses.create(
                    model=self.model_name,
                    input=prompt
                )
                
                final_text = ""
                for item in res.output:
                    if item.type == "message":
                        for content_part in item.content:
                            if content_part.type == "output_text":
                                final_text += content_part.text
                return final_text.strip()
            
            else:
                # Reasoning and standard models use chat completions
                kwargs = {}
                if self.supports_temperature:
                    kwargs["temperature"] = 0.2
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                else:
                    # o1-mini and similar models historically reject the 'system' role
                    messages = [
                        {"role": "user", "content": f"INSTRUCTIONS:\n{system_prompt}\n\nINPUT:\n{user_prompt}"}
                    ]
                    
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            raise e
