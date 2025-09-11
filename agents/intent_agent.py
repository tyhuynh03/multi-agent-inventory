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
You are an expert intent classifier for warehouse management systems.

Classify the following question into one of 4 categories:

1. **query**: Regular questions that need data retrieval
   - Examples: "How many products are in stock?", "What is the average price by category?"
   
2. **visualize**: Requests to create charts, graphs, or visualizations
   - Examples: "Show inventory trend chart", "Display sales chart over time"
   
3. **report**: Generate reports or data summaries
   - Examples: "Generate low stock report", "Create business summary"
   
4. **alert**: Warnings or urgent notifications
   - Examples: "Alert about products running low", "Notify about unusual inventory levels"

Question to classify: "{user_question}"

Return result in JSON format:
{{
    "intent": "query|visualize|report|alert",
    "confidence": 0.95,
    "reasoning": "Classification reasoning"
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
            valid_intents = ["query", "visualize", "report", "alert"]
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
    
    def is_report_intent(self, user_question: str) -> bool:
        """
        Check if it's a report intent
        """
        result = self.classify_intent(user_question)
        return result["intent"] == "report"
    
    def is_alert_intent(self, user_question: str) -> bool:
        """
        Check if it's an alert intent
        """
        result = self.classify_intent(user_question)
        return result["intent"] == "alert"
