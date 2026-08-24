from typing import List, Dict, Any

def split_text_into_sliding_chunks(
    text: str, 
    chunk_size: int = 150, 
    overlap: int = 30
) -> List[Dict[str, Any]]:
    """
    Splits text into chunks of `chunk_size` words with a sliding window `overlap`.
    Returns list of dicts: [{'text': str, 'chunk_index': int}]
    """
    words = text.split()
    total_words = len(words)
    chunks = []
    
    if total_words == 0:
        return []
        
    step = chunk_size - overlap
    if step <= 0:
        step = chunk_size # Fallback if overlap is equal to or larger than chunk_size
        
    idx = 0
    chunk_count = 0
    while idx < total_words:
        chunk_words = words[idx : idx + chunk_size]
        chunk_text = " ".join(chunk_words)
        
        chunks.append({
            "content": chunk_text,
            "chunk_index": chunk_count
        })
        
        chunk_count += 1
        idx += step
        if idx + overlap >= total_words:
            # Avoid small trailing fragments if we've covered the rest
            break
            
    return chunks
