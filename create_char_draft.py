import sys
import os

# add QWen3TTS to path
sys.path.append("/Users/tang/PycharmProjects/pythonProject/QWen3TTS")

from utils.llm_client import LLMClient

def generate_chars():
    prompt_path = "/Users/tang/PycharmProjects/pythonProject/QWen3TTS/novel_data/大王饶命_仿写/character_profiles/character_bible_prompt.md"
    out_path = "/Users/tang/PycharmProjects/pythonProject/QWen3TTS/novel_data/大王饶命_仿写/character_profiles/character_bible_draft.md"
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
        
    client = LLMClient()
    print("Generating characters...")
    response = client.generate(prompt)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(response)
    print(f"Generated characters saved to {out_path}")

if __name__ == "__main__":
    generate_chars()
