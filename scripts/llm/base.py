from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """
    Abstract Base Class defining the interface that all LLM providers (OpenAI, Anthropic, Gemini, etc.)
    must implement to be compatible with DSA Data Studio.
    """
    
    @abstractmethod
    def generate_review(self, problem_statement: str, solution_code: str, language: str) -> str:
        """
        Sends the problem and solution to the LLM and returns the Markdown code review.
        """
        pass
