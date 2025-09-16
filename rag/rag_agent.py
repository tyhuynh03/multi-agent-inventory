"""
RAG Agent - Advanced Retrieval-Augmented Generation with ChromaDB
Provides semantic search capabilities for better example retrieval
"""

import os
import json
import chromadb
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
from pathlib import Path
from utils.logger import traceable
import numpy as np


class RAGAgent:
    """
    Advanced RAG system using ChromaDB for semantic similarity search
    """
    
    def __init__(self, 
                 collection_name: str = "sql_examples",
                 model_name: str = "all-MiniLM-L6-v2",
                 persist_directory: str = "data/chroma_db"):
        """
        Initialize RAG Agent with ChromaDB
        
        Args:
            collection_name: Name of ChromaDB collection
            model_name: Sentence transformer model for embeddings
            persist_directory: Directory to persist ChromaDB data
        """
        self.collection_name = collection_name
        self.model_name = model_name
        self.persist_directory = persist_directory
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(model_name)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"✅ Loaded existing ChromaDB collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "SQL examples for RAG"}
            )
            print(f"🆕 Created new ChromaDB collection: {collection_name}")
    
    @traceable(name="rag.build_index")
    def build_index_from_examples(self, examples_path: str, force_rebuild: bool = False) -> Dict:
        """
        Build ChromaDB index from examples.jsonl file
        
        Args:
            examples_path: Path to examples.jsonl file
            force_rebuild: Force rebuild even if collection exists
            
        Returns:
            Dict with indexing results
        """
        if not os.path.exists(examples_path):
            return {
                "success": False,
                "error": f"Examples file not found: {examples_path}",
                "indexed_count": 0
            }
        
        try:
            # Check if we need to rebuild
            if not force_rebuild:
                try:
                    existing_collection = self.client.get_collection(name=self.collection_name)
                    existing_count = existing_collection.count()
                    
                    # Count examples in file
                    file_count = self._count_examples_in_file(examples_path)
                    
                    if existing_count == file_count and existing_count > 0:
                        print(f"✅ ChromaDB collection is up to date ({existing_count} examples)")
                        return {
                            "success": True,
                            "indexed_count": existing_count,
                            "collection_name": self.collection_name,
                            "model_name": self.model_name,
                            "message": "Collection already up to date"
                        }
                except Exception:
                    pass  # Collection doesn't exist, proceed with build
            
            print(f"🔄 Building ChromaDB index from {examples_path}...")
            
            # Clear existing collection
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "SQL examples for RAG"}
                )
            except Exception:
                pass
            
            examples = []
            questions = []
            sqls = []
            ids = []
            
            # Load examples from JSONL
            with open(examples_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        obj = json.loads(line)
                        if "question" in obj and "sql" in obj:
                            examples.append(obj)
                            questions.append(obj["question"])
                            sqls.append(obj["sql"])
                            ids.append(f"example_{idx}")
                    except json.JSONDecodeError:
                        continue
            
            if not examples:
                return {
                    "success": False,
                    "error": "No valid examples found in file",
                    "indexed_count": 0
                }
            
            # Generate embeddings for questions
            print(f"🔄 Generating embeddings for {len(questions)} examples...")
            embeddings = self.embedding_model.encode(questions).tolist()
            
            # Add to ChromaDB collection
            self.collection.add(
                embeddings=embeddings,
                documents=questions,
                metadatas=[
                    {
                        "sql": sql,
                        "question": question,
                        "example_id": example_id
                    }
                    for sql, question, example_id in zip(sqls, questions, ids)
                ],
                ids=ids
            )
            
            print(f"✅ Successfully indexed {len(examples)} examples in ChromaDB")
            
            return {
                "success": True,
                "indexed_count": len(examples),
                "collection_name": self.collection_name,
                "model_name": self.model_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to build index: {str(e)}",
                "indexed_count": 0
            }
    
    def _count_examples_in_file(self, examples_path: str) -> int:
        """Count valid examples in JSONL file"""
        count = 0
        try:
            with open(examples_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if "question" in obj and "sql" in obj:
                            count += 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return count
    
    @traceable(name="rag.retrieve")
    def retrieve_similar_examples(self, 
                                 query: str, 
                                 top_k: int = 3,
                                 similarity_threshold: float = 0.3) -> List[Dict]:
        """
        Retrieve similar examples using semantic search
        
        Args:
            query: User question to find similar examples for
            top_k: Number of similar examples to retrieve
            similarity_threshold: Minimum similarity score threshold
            
        Returns:
            List of similar examples with metadata
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode([query]).tolist()
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            similar_examples = []
            
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    # Convert distance to similarity score (ChromaDB uses cosine distance)
                    similarity = 1 - distance
                    
                    if similarity >= similarity_threshold:
                        similar_examples.append({
                            "question": doc,
                            "sql": metadata["sql"],
                            "similarity": similarity,
                            "rank": i + 1
                        })
            
            return similar_examples
            
        except Exception as e:
            print(f"❌ Error retrieving examples: {str(e)}")
            return []
    
    @traceable(name="rag.build_fewshot_prompt")
    def build_fewshot_prompt(self, 
                           query: str, 
                           top_k: int = 3,
                           similarity_threshold: float = 0.3) -> Tuple[str, Dict]:
        """
        Build few-shot prompt with semantically similar examples
        
        Args:
            query: User question
            top_k: Number of examples to retrieve
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            Tuple of (fewshot_text, metadata)
        """
        # Retrieve similar examples
        similar_examples = self.retrieve_similar_examples(
            query, top_k, similarity_threshold
        )
        
        if not similar_examples:
            return "", {"selected_examples": [], "similarity_scores": []}
        
        # Build few-shot prompt
        fewshot_parts = []
        for example in similar_examples:
            fewshot_parts.append(
                f"Question: {example['question']}\n```sql\n{example['sql']}\n```"
            )
        
        fewshot_text = "\n\n".join(fewshot_parts)
        
        metadata = {
            "selected_examples": [ex["question"] for ex in similar_examples],
            "similarity_scores": [ex["similarity"] for ex in similar_examples],
            "retrieval_method": "semantic_search",
            "model_name": self.model_name
        }
        
        return fewshot_text, metadata
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the ChromaDB collection"""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_examples": count,
                "model_name": self.model_name,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            return {
                "error": f"Failed to get collection stats: {str(e)}"
            }
    
    def clear_collection(self) -> bool:
        """Clear all examples from the collection"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "SQL examples for RAG"}
            )
            print(f"🗑️ Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to clear collection: {str(e)}")
            return False


# Global RAG agent instance
_rag_agent = None

def get_rag_agent() -> RAGAgent:
    """Get or create global RAG agent instance"""
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent

def initialize_rag_system(examples_path: str = "data/examples.jsonl") -> Dict:
    """
    Initialize RAG system with examples
    
    Args:
        examples_path: Path to examples.jsonl file
        
    Returns:
        Initialization results
    """
    rag_agent = get_rag_agent()
    return rag_agent.build_index_from_examples(examples_path)
