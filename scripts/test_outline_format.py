import sys
import os
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from storage import StorageManager
from workflow.generation_loop import GenerationLoop

def test_single_chapter_generation():
    novel_title = "万族之劫_仿写"
    
    storage_dir = os.path.join(Config.STORAGE_DIR, novel_title)
    
    # Needs a complete generation loop
    from models import StoryBible
    bible = StoryBible(story_title=novel_title)
    storage = StorageManager(storage_dir=storage_dir)
    
    loop = GenerationLoop(storage)
    
    print("Testing generate chapter 1...")
    
    # Just use loop.weaver directly
    weaver = loop.weaver
    
    # We will just print the prompt and see if it looks correct
    context = "Test Context"
    
    # Actually just call generate_chapter_outline
    outline = weaver.generate_chapter_outline(
        bible=bible,
        chapter_number=1,
        arc_goal="Test Volume 1 Outline...",
        character_states={},
        structure_template={"structure_name": "Test"},
        character_decisions={},
        loops_to_resolve=[],
        loops_to_plant=[]
    )
    
    print("\n-------------------- \n")
    print(f"Outline Output: \n{outline.detailed_outline}\n")
    print("-------------------- \n")

if __name__ == "__main__":
    test_single_chapter_generation()
