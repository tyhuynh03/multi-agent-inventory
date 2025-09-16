#!/usr/bin/env python3
"""
Initialize RAG System with ChromaDB
Builds semantic search index from examples.jsonl
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag.rag_agent import initialize_rag_system, get_rag_agent


def main():
    """Initialize RAG system with examples"""
    print("🚀 Initializing RAG System with ChromaDB...")
    
    # Check if examples file exists
    examples_path = "data/examples.jsonl"
    if not os.path.exists(examples_path):
        print(f"❌ Examples file not found: {examples_path}")
        print("Please ensure data/examples.jsonl exists with your SQL examples.")
        return False
    
    try:
        # Initialize RAG system
        result = initialize_rag_system(examples_path)
        
        if result["success"]:
            print(f"✅ RAG system initialized successfully!")
            print(f"📊 Indexed {result['indexed_count']} examples")
            print(f"🗄️ Collection: {result['collection_name']}")
            print(f"🤖 Model: {result['model_name']}")
            
            # Show collection stats
            rag_agent = get_rag_agent()
            stats = rag_agent.get_collection_stats()
            print(f"\n📈 Collection Statistics:")
            print(f"   Total examples: {stats['total_examples']}")
            print(f"   Persist directory: {stats['persist_directory']}")
            
            return True
        else:
            print(f"❌ Failed to initialize RAG system: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing RAG system: {str(e)}")
        return False


def test_semantic_search():
    """Test semantic search functionality"""
    print("\n🔍 Testing semantic search...")
    
    try:
        rag_agent = get_rag_agent()
        
        # Test queries
        test_queries = [
            "What are the top selling products?",
            "Show me low inventory items",
            "Which products have the highest price?",
            "List products by category"
        ]
        
        for query in test_queries:
            print(f"\n🔎 Query: '{query}'")
            examples = rag_agent.retrieve_similar_examples(query, top_k=2)
            
            if examples:
                for i, example in enumerate(examples, 1):
                    print(f"   {i}. Similarity: {example['similarity']:.3f}")
                    print(f"      Question: {example['question'][:80]}...")
                    print(f"      SQL: {example['sql'][:60]}...")
            else:
                print("   No similar examples found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing semantic search: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🤖 RAG System Initialization")
    print("=" * 60)
    
    # Initialize RAG system
    success = main()
    
    if success:
        # Test semantic search
        test_semantic_search()
        
        print("\n" + "=" * 60)
        print("✅ RAG system is ready!")
        print("You can now use semantic search in your SQL agent.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ RAG system initialization failed!")
        print("Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)
