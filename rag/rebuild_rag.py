#!/usr/bin/env python3
"""
Rebuild RAG Index Script
Force rebuild ChromaDB index from examples.jsonl
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag.rag_retriever import get_rag_retriever


def main():
    """Rebuild RAG index"""
    print("🔄 Rebuilding RAG Index...")
    
    examples_path = "data/examples.jsonl"
    
    if not os.path.exists(examples_path):
        print(f"❌ Examples file not found: {examples_path}")
        return False
    
    try:
        # Get RAG agent
        retriever = get_rag_retriever()
        
        # Force rebuild
        result = retriever.build_index_from_examples(examples_path, force_rebuild=True)
        
        if result["success"]:
            print(f"✅ RAG index rebuilt successfully!")
            print(f"📊 Indexed {result['indexed_count']} examples")
            print(f"🗄️ Collection: {result['collection_name']}")
            print(f"🤖 Model: {result['model_name']}")
            
            # Show collection stats
            stats = retriever.get_collection_stats()
            print(f"\n📈 Collection Statistics:")
            print(f"   Total examples: {stats['total_examples']}")
            print(f"   Persist directory: {stats['persist_directory']}")
            
            return True
        else:
            print(f"❌ Failed to rebuild RAG index: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error rebuilding RAG index: {str(e)}")
        return False


def show_current_stats():
    """Show current RAG statistics"""
    print("\n📊 Current RAG Statistics:")
    try:
        retriever = get_rag_retriever()
        stats = retriever.get_collection_stats()
        
        if "error" in stats:
            print(f"   ❌ {stats['error']}")
        else:
            print(f"   Collection: {stats['collection_name']}")
            print(f"   Total examples: {stats['total_examples']}")
            print(f"   Model: {stats['model_name']}")
            print(f"   Directory: {stats['persist_directory']}")
            
    except Exception as e:
        print(f"   ❌ Error getting stats: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 RAG Index Rebuild Tool")
    print("=" * 60)
    
    # Show current stats
    show_current_stats()
    
    # Rebuild index
    success = main()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ RAG index rebuild completed!")
        print("New examples are now available for semantic search.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ RAG index rebuild failed!")
        print("Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)
