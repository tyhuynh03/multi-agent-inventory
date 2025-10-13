"""
Intent Classification Agent - Phân loại ý định người dùng
Sử dụng LLM để phân loại câu hỏi thành 4 loại: query, visualize, report, alert
"""

from langchain_groq import ChatGroq
from langsmith.run_helpers import traceable
from configs.settings import GROQ_MODEL_NAME
import os


class IntentClassificationAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=GROQ_MODEL_NAME,
            temperature=0.1,  # Thấp để đảm bảo consistency
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
    
    @traceable(name="intent.classify")
    def classify_intent(self, user_question: str) -> dict:
        """
        Phân loại ý định của người dùng
        
        Args:
            user_question: Câu hỏi của người dùng
            
        Returns:
            dict: {
                "intent": "query|visualize|report|alert",
                "confidence": float,
                "reasoning": str
            }
        """
        prompt = f"""
You are an expert intent classifier for warehouse management systems. Analyze the user's question and classify it into the most appropriate category.

**Context**: This is a warehouse inventory management system with SQLite database containing inventory data.

**Classification Categories:**

1. **query**: Direct data retrieval questions, counting, filtering, or simple data requests
   - Examples: "How many products are in stock?", "What is the average price by category?", "Show products below 10 units", "List all categories"

2. **visualize**: Requests for charts, graphs, plots, or visual representations of data
   - Examples: "Show inventory trend chart", "Display sales chart over time", "Create a graph of inventory levels", "Plot demand vs supply", "Visualize data"

3. **schema**: Questions about database structure, tables, columns, or data organization
   - Examples: "What tables are in the database?", "Show database schema", "List all columns", "Describe table structure"

4. **inventory_analytics**: Stock cover days analysis - how many days of inventory remaining based on sales velocity
   - Examples: "Calculate stock cover days", "Show products with stock cover less than 30 days", "Top 10 products with lowest stock cover", "Show critical items", "Which products are running low", "Products with low coverage", "Stock cover analysis"

**Important Guidelines:**
- Focus on the user's INTENT, not just keywords
- Consider context and business purpose
- "Show" can mean different things: "Show data" = query, "Show chart" = visualize
- "Display" usually means visualize when referring to charts/graphs
- Questions about "stock cover", "days of stock", "coverage" are ALWAYS inventory_analytics (not query)
- Questions about "restock", "replenish", "critical", "warning" are inventory_analytics
- Simple filters like "products WHERE price > 100" = query
- Complex metrics like "stock cover < 30 days" = inventory_analytics

**Question to classify:** "{user_question}"

**Return result in JSON format:**
{{
    "intent": "query|visualize|schema|inventory_analytics",
    "confidence": 0.95,
    "reasoning": "Detailed explanation of why this classification was chosen"
}}
"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Parse JSON response
            import json
            import re
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                # Fallback: try to parse entire content
                result = json.loads(content)
            
            # Validate intent
            valid_intents = ["query", "visualize", "schema", "inventory_analytics"]
            if result.get("intent") not in valid_intents:
                result["intent"] = "query"  # Default fallback
                result["confidence"] = 0.5
                result["reasoning"] = "Unable to determine intent, defaulting to query"
            
            return result
            
        except Exception as e:
            # Fallback if LLM fails
            return {
                "intent": "query",
                "confidence": 0.3,
                "reasoning": f"Classification error: {str(e)}, defaulting to query"
            }
    
    def is_visualize_intent(self, user_question: str) -> bool:
        """
        Backward compatibility - check if it's a visualize intent
        """
        result = self.classify_intent(user_question)
        return result["intent"] == "visualize"
    
