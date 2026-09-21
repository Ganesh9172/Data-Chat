import random
import requests
import json
from typing import List, Optional
from ai_tests.config import AI_EVALUATOR_ENABLED, OLLAMA_BASE_URL, AI_EVALUATOR_MODEL

def generate_variations_rule_based(base_question: str, count: int = 5) -> List[str]:
    """
    Generates realistic natural language variations (slang, word order, lowercase, missing words, typos)
    deterministically without requiring external API access.
    """
    variations = set()
    cleaned = base_question.strip().rstrip("?").strip()

    if "0.5 bar" in cleaned or "0.5" in cleaned:
        templates = [
            "Is 0.5 bar okay?",
            "Is half a bar okay?",
            "0.5 bar is fine right?",
            "My pressure is 0.5 bar, is that okay?",
            "0.5 bar well in limit?",
            "Is 0.5 bar within the limit?",
            "my boiler pressure is only 0.5",
            "pressure showing 0.5 bar",
            "0.5 bar normal?",
            "half bar pressure okay?",
            "Is 0.5 bar too low?",
            "is 0.5bar enough?",
            "got 0.5 bar on gauge is it ok"
        ]
        for t in templates:
            variations.add(t)
            if len(variations) >= count:
                break
        return list(variations)[:count]

    # Generic variation patterns
    patterns = [
        f"{cleaned.lower()}",
        f"{cleaned.lower()}?",
        f"hey, {cleaned.lower()}",
        f"can you tell me {cleaned.lower()}?",
        f"quick question: {cleaned.lower()}",
        f"{cleaned.replace('What is', 'whats').replace('what is', 'whats')}",
        f"{cleaned} please",
        f"{cleaned.rstrip('.')} please explain"
    ]
    for p in patterns:
        variations.add(p)
        if len(variations) >= count:
            break

    return list(variations)[:count]

def generate_variations_with_ai(base_question: str, count: int = 5) -> List[str]:
    """
    Uses local Ollama if configured to generate natural human phrasing variations.
    """
    model = AI_EVALUATOR_MODEL or "llama3.2"
    prompt = f"""Generate {count} distinct human natural language variations of the following question.
Include conversational phrasing, informal slang, incomplete sentences, or slight typos.

Question: "{base_question}"

Return ONLY a JSON array of strings, for example:
["variation 1", "variation 2", "variation 3"]
"""
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            raw_text = data.get("response", "").strip()
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed][:count]
            if isinstance(parsed, dict) and "variations" in parsed:
                return [str(v).strip() for v in parsed["variations"]][:count]
    except Exception as e:
        print(f"[AI Generator Warning] Ollama unavailable, using rule-based generator: {e}")

    return generate_variations_rule_based(base_question, count)

def generate_variations(base_question: str, count: int = 5, use_ai: bool = False) -> List[str]:
    """
    Main generator interface.
    """
    if use_ai and AI_EVALUATOR_ENABLED:
        return generate_variations_with_ai(base_question, count)
    return generate_variations_rule_based(base_question, count)

if __name__ == "__main__":
    import sys
    base_q = sys.argv[1] if len(sys.argv) > 1 else "Is 0.5 bar okay?"
    vars_list = generate_variations(base_q, count=8)
    print(f"\n[Generated Variations for: '{base_q}']")
    for i, v in enumerate(vars_list, 1):
        print(f"  {i}. {v}")
    print()
