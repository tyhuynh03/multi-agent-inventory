"""
Orchestrator Agent - Điều phối workflow giữa các agent
Quyết định gọi agent nào dựa trên intent classification
"""

from agents.intent_agent import IntentClassificationAgent
from agents.sql_agent import generate_sql
from agents.viz_agent import render_auto_chart
from agents.report_agent import ReportAgent
from db.connection import get_db, run_sql
from langsmith.run_helpers import traceable
import pandas as pd


class OrchestratorAgent:
    def __init__(self):
        self.intent_agent = IntentClassificationAgent()
        self.report_agent = ReportAgent()
    
    @traceable(name="orchestrator.run_agent")
    def run_agent(self, user_question: str, db_path: str = "data/inventory.db", 
                  use_retriever: bool = True, examples_path: str = "data/examples.jsonl", top_k: int = 2) -> dict:
        """
        Điều phối workflow chính
        
        Args:
            user_question: Câu hỏi của người dùng
            use_retriever: Có sử dụng RAG không
            examples_path: Đường dẫn file examples
            top_k: Số lượng examples lấy từ RAG
            
        Returns:
            dict: Kết quả từ agent tương ứng
        """
        # Bước 1: Phân loại intent
        intent_result = self.intent_agent.classify_intent(user_question)
        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        reasoning = intent_result["reasoning"]
        
        print(f"🎯 Intent: {intent} (confidence: {confidence:.2f})")
        print(f"💭 Reasoning: {reasoning}")
        
        # Bước 2: Điều hướng đến agent phù hợp
        if intent == "query":
            return self._handle_query_intent(user_question, db_path, use_retriever, examples_path, top_k)
        
        elif intent == "visualize":
            return self._handle_visualize_intent(user_question, db_path, use_retriever, examples_path, top_k)
        
        elif intent == "report":
            return self._handle_report_intent(user_question, db_path, use_retriever, examples_path, top_k)
        
        elif intent == "alert":
            return self._handle_alert_intent(user_question, db_path, use_retriever, examples_path, top_k)
        
        else:
            # Fallback về query
            return self._handle_query_intent(user_question, db_path, use_retriever, examples_path, top_k)
    
    def _handle_query_intent(self, user_question: str, db_path: str, use_retriever: bool, 
                           examples_path: str, top_k: int) -> dict:
        """Xử lý query intent - SQL thông thường"""
        try:
            # Generate SQL
            db = get_db(db_path)
            result = generate_sql(
                question=user_question,
                db=db,
                model="openai/gpt-oss-20b",
                examples_path=examples_path,
                top_k=top_k
            )
            
            # Check if this is a schema response
            if isinstance(result, str) and "📋 **Database Schema Information**" in result:
                return {
                    "success": True,
                    "intent": "query",
                    "agent": "sql_agent",
                    "sql": "Schema Information",
                    "data": None,
                    "schema_info": result,
                    "message": "📋 Database schema information retrieved successfully!"
                }
            
            if not result:
                return {
                    "success": False,
                    "error": "Unable to generate SQL query",
                    "intent": "query",
                    "agent": "sql_agent"
                }
            
            # Execute SQL
            df, error = run_sql(db, result)
            if error:
                return {
                    "success": False,
                    "error": f"SQL execution error: {error}",
                    "intent": "query",
                    "agent": "sql_agent"
                }
            
            return {
                "success": True,
                "intent": "query",
                "agent": "sql_agent",
                "sql": result,
                "data": df,
                "message": f"✅ Query successful! Found {len(df)} records."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Query processing error: {str(e)}",
                "intent": "query",
                "agent": "sql_agent"
            }
    
    def _handle_visualize_intent(self, user_question: str, db_path: str, use_retriever: bool, 
                               examples_path: str, top_k: int) -> dict:
        """Xử lý visualize intent - SQL + Chart"""
        try:
            # Generate SQL
            db = get_db(db_path)
            sql = generate_sql(
                question=user_question,
                db=db,
                model="openai/gpt-oss-20b",
                examples_path=examples_path,
                top_k=top_k
            )
            
            if not sql:
                return {
                    "success": False,
                    "error": "Unable to generate SQL query",
                    "intent": "visualize",
                    "agent": "viz_agent"
                }
            
            # Execute SQL
            df, error = run_sql(db, sql)
            if error:
                return {
                    "success": False,
                    "error": f"SQL execution error: {error}",
                    "intent": "visualize",
                    "agent": "viz_agent"
                }
            
            if df.empty:
                return {
                    "success": False,
                    "error": "No data available for chart generation",
                    "intent": "visualize",
                    "agent": "viz_agent"
                }
            
            # Generate chart
            chart_result = render_auto_chart(df)
            
            return {
                "success": True,
                "intent": "visualize",
                "agent": "viz_agent",
                "sql": sql,
                "data": df,
                "chart": chart_result,
                "message": f"📊 Chart generated successfully from {len(df)} records!"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Chart generation error: {str(e)}",
                "intent": "visualize",
                "agent": "viz_agent"
            }
    
    def _handle_report_intent(self, user_question: str, db_path: str, use_retriever: bool, 
                            examples_path: str, top_k: int) -> dict:
        """Handle report intent - Generate reports"""
        try:
            # Parse report type from user question
            report_type = self._parse_report_type(user_question)
            params = self._parse_report_params(user_question)
            
            # Generate report
            result = self.report_agent.generate_report(
                report_type=report_type,
                db_path=db_path,
                params=params
            )
            
            if not result["success"]:
                return {
                    "success": False,
                    "error": result["error"],
                    "intent": "report",
                    "agent": "report_agent"
                }
            
            return {
                "success": True,
                "intent": "report",
                "agent": "report_agent",
                "report_type": result["report_type"],
                "title": result["title"],
                "description": result["description"],
                "data": result["data"],
                "summary": result["summary"],
                "parameters": result["parameters"],
                "message": result["message"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Report processing error: {str(e)}",
                "intent": "report",
                "agent": "report_agent"
            }
    
    def _parse_report_type(self, user_question: str) -> str:
        """Parse report type from user question"""
        question_lower = user_question.lower()
        
        if any(word in question_lower for word in ["low stock", "low inventory", "below threshold"]):
            return "low_stock"
        elif any(word in question_lower for word in ["top", "best", "selling", "performance"]):
            return "top_products"
        elif any(word in question_lower for word in ["category", "categories", "by category"]):
            return "category_summary"
        elif any(word in question_lower for word in ["value", "valuation", "worth", "total value"]):
            return "inventory_valuation"
        elif any(word in question_lower for word in ["overstock", "excess", "too much"]):
            return "overstock"
        else:
            # Default to low stock report
            return "low_stock"
    
    def _parse_report_params(self, user_question: str) -> dict:
        """Parse parameters from user question"""
        import re
        params = {}
        
        # Extract threshold for low stock/overstock
        threshold_match = re.search(r'(\d+)\s*(?:units?|items?)?', user_question.lower())
        if threshold_match:
            params["threshold"] = int(threshold_match.group(1))
        
        # Extract limit for top products
        limit_match = re.search(r'top\s*(\d+)', user_question.lower())
        if limit_match:
            params["limit"] = int(limit_match.group(1))
        
        return params
    
    def _handle_alert_intent(self, user_question: str, db_path: str, use_retriever: bool, 
                           examples_path: str, top_k: int) -> dict:
        """Xử lý alert intent - Cảnh báo"""
        # TODO: Implement Alert Agent
        return {
            "success": False,
            "error": "Alert Agent not yet implemented",
            "intent": "alert",
            "agent": "alert_agent"
        }
