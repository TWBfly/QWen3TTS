import os
import sys
import re
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mechanisms.rag_manager import RAGManager
from config import Config

def import_novel_to_rag(markdown_path: str, novel_name: str):
    print(f"Importing {markdown_path} into RAG database for {novel_name}...")
    
    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content by volume headers (## 第X卷：标题)
    # Using regex to find all volume sections
    # re.split will return [pre-match, match1, text1, match2, text2...] if capturing grouped.
    # We'll use re.split with a capture group for the volume header
    parts = re.split(r'(?=\n## 第\d+卷：)', content)
    
    storage_dir = os.path.join(Config.STORAGE_DIR, novel_name)
    os.makedirs(storage_dir, exist_ok=True)
    
    rag_manager = RAGManager(storage_path=storage_dir)
    
    texts = []
    metadata = []
    
    # Add the first part (pre-volume text, if any, often the global synopsis)
    if parts[0].strip():
        texts.append(parts[0].strip())
        metadata.append({"source": novel_name, "section": "总纲/楔子", "type": "overview"})
    
    # Add the remaining volume parts
    for i in range(1, len(parts)):
        part_text = parts[i].strip()
        if not part_text:
            continue
            
        # Extract the volume title for metadata
        match = re.match(r'## (第\d+卷：[^\n]+)', part_text)
        volume_title = match.group(1) if match else f"Volume Part {i}"
        
        texts.append(part_text)
        metadata.append({"source": novel_name, "section": volume_title, "type": "volume_outline"})
    
    print(f"Found {len(texts)} sections to index.")
    
    # Batch add to vector store
    rag_manager.add_batch_to_vector_store(texts, metadata)
    
    print(f"Successfully imported and indexed content into {storage_dir}")
    print(f"Vector Index Path: {rag_manager._index_path}")

if __name__ == "__main__":
    markdown_file = "/Users/tang/PycharmProjects/pythonProject/dagang/万族之劫_仿写.md"
    novel_title = "万族之劫_仿写"
    
    import_novel_to_rag(markdown_file, novel_title)
