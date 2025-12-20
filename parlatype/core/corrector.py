import os
from openai import OpenAI
from .config import PROMPTS_DIR, SYSTEM_PROMPTS_DIR

class LLMCorrector:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.history = []
        self.system_prompt = self.load_prompt("default.txt")
        self.enabled = False

    def load_prompt(self, filename):
        # Try user dir first
        user_path = os.path.join(PROMPTS_DIR, filename)
        if os.path.exists(user_path):
            try:
                with open(user_path, 'r') as f:
                    return f.read()
            except Exception as e:
                print(f"Error loading user prompt {filename}: {e}")
        
        # Try system dir
        system_path = os.path.join(SYSTEM_PROMPTS_DIR, filename)
        try:
            with open(system_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading system prompt {filename}: {e}")
            return "Sei un assistente che corregge trascrizioni."

    def save_prompt(self, filename, content):
        try:
            with open(os.path.join(PROMPTS_DIR, filename), 'w') as f:
                f.write(content)
            self.system_prompt = content
            return True
        except Exception as e:
            print(f"Error saving prompt {filename}: {e}")
            return False

    def correct(self, text):
        if not self.enabled or not text.strip():
            self.history.append(text)
            if len(self.history) > 10:
                self.history.pop(0)
            return text

        context = "\n".join(self.history)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nPhrase to correct:\n{text}"}
        ]

        try:
            # Attempt with max_completion_tokens (for reasoning models)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=150
            )
            corrected_text = response.choices[0].message.content.strip()
            self.history.append(corrected_text)
            if len(self.history) > 10:
                self.history.pop(0)
            return corrected_text
        except Exception as e:
            print(f"LLM Error (max_completion_tokens): {e}")
            # Fallback to max_tokens (for standard models)
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=150
                )
                corrected_text = response.choices[0].message.content.strip()
                self.history.append(corrected_text)
                if len(self.history) > 10:
                    self.history.pop(0)
                return corrected_text
            except Exception as e2:
                print(f"LLM Error (max_tokens): {e2}")
                return text
