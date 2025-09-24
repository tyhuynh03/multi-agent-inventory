"""
Orchestrator Agent - Điều phối workflow giữa các agent
Quyết định gọi agent nào dựa trên intent classification
"""

from agents.intent_agent import IntentClassificationAgent
from agents.sql_agent import generate_sql
from agents.viz_agent import VisualizationAgent
from agents.report_agent import ReportAgent
from agents.response_agent import ResponseAgent
from db.connection import get_db, run_sql_unified
from langsmith.run_helpers import traceable
import pandas as pd
import time


class OrchestratorAgent:
    def __init__(self):
        self.intent_agent = IntentClassificationAgent()
        self.report_agent = ReportAgent()
        self.response_agent = ResponseAgent()
        self.viz_agent = VisualizationAgent()
    
    @traceable(name="orchestrator.run_agent")
    def run_agent(self, user_question: str, db_type: str = "postgresql", 
                  use_retriever: bool = True, examples_path: str = "data/examples.jsonl", top_k: int = 2) -> dict:
        """
        Điều phối workflow chính
        
        Args:
            user_question: Câu hỏi của người dùng
            db_type: Loại database ("postgresql" hoặc "sqlite")
            use_retriever: Có sử dụng RAG không
            examples_path: Đường dẫn file examples
            top_k: Số lượng examples lấy từ RAG
            
        Returns:
            dict: Kết quả từ agent tương ứng
        """
        # Bước 1: Phân loại intent
        steps = []
        t0 = time.perf_counter()
        intent_result = self.intent_agent.classify_intent(user_question)
        t1 = time.perf_counter()
        steps.append({
            "step": "intent_classification",
            "duration_ms": (t1 - t0) * 1000,
            "detail": intent_result,
        })
        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        reasoning = intent_result["reasoning"]
        
        print(f"🎯 Intent: {intent} (confidence: {confidence:.2f})")
        print(f"💭 Reasoning: {reasoning}")
        
        # Bước 2: Điều hướng đến agent phù hợp
        if intent == "query":
            return self._handle_query_intent(
                user_question, db_type, use_retriever, examples_path, top_k,
                debug_base={"intent_result": intent_result, "t_intent_ms": (t1 - t0)*1000, "steps": steps, "context": {"db_type": db_type, "examples_path": examples_path, "top_k": top_k}}
            )
        
        elif intent == "visualize":
            return self._handle_visualize_intent(
                user_question, db_type, use_retriever, examples_path, top_k,
                debug_base={"intent_result": intent_result, "t_intent_ms": (t1 - t0)*1000, "steps": steps, "context": {"db_type": db_type, "examples_path": examples_path, "top_k": top_k}}
            )
        
        elif intent == "report":
            return self._handle_report_intent(
                user_question, db_type, use_retriever, examples_path, top_k,
                debug_base={"intent_result": intent_result, "t_intent_ms": (t1 - t0)*1000, "steps": steps, "context": {"db_type": db_type, "examples_path": examples_path, "top_k": top_k}}
            )
        
        elif intent == "schema":
            return self._handle_schema_intent(user_question, db_type)
        
        else:
            # Fallback về query
            return self._handle_query_intent(user_question, db_type, use_retriever, examples_path, top_k)
    
    def _handle_query_intent(self, user_question: str, db_type: str, use_retriever: bool, 
                           examples_path: str, top_k: int, debug_base: dict | None = None) -> dict:
        """Xử lý query intent - SQL thông thường"""
        try:
            # Generate SQL
            if db_type == "postgresql":
                db = get_db("postgresql://inventory_user:inventory_pass@localhost:5432/inventory_db", "postgresql")
            else:
                db = get_db("data/inventory.db", "sqlite")
            t_sql0 = time.perf_counter()
            result = generate_sql(
                question=user_question,
                db=db,
                model="openai/gpt-oss-20b",
                examples_path=examples_path,
                top_k=top_k,
                use_semantic_search=use_retriever
            )
            t_sql1 = time.perf_counter()
            (debug_base or {}).get("steps", []).append({
                "step": "sql_generate",
                "duration_ms": (t_sql1 - t_sql0) * 1000,
                "detail": {"model": "openai/gpt-oss-20b"}
            })
            
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
            t_exec0 = time.perf_counter()
            df, error = run_sql_unified(result, db_type)
            t_exec1 = time.perf_counter()
            (debug_base or {}).get("steps", []).append({
                "step": "sql_execute",
                "duration_ms": (t_exec1 - t_exec0) * 1000,
                "detail": {"rows": 0 if error else len(df), "error": error}
            })
            if error:
                return {
                    "success": False,
                    "error": f"SQL execution error: {error}",
                    "intent": "query",
                    "agent": "sql_agent"
                }
            
            nl = self.response_agent.generate_response(user_question, df, result)
            return {
                "success": True,
                "intent": "query",
                "agent": "sql_agent",
                "sql": result,
                "data": df,
                "message": f"✅ Query successful! Found {len(df)} records.",
                "response": nl.get("text"),
                "response_table_md": nl.get("table_md"),
                "debug": {
                    **(debug_base or {}),
                    "t_sql_generate_ms": (t_sql1 - t_sql0)*1000,
                    "t_sql_execute_ms": (t_exec1 - t_exec0)*1000,
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Query processing error: {str(e)}",
                "intent": "query",
                "agent": "sql_agent"
            }
    
    def _handle_visualize_intent(self, user_question: str, db_type: str, use_retriever: bool, 
                               examples_path: str, top_k: int, debug_base: dict | None = None) -> dict:
        """Xử lý visualize intent - SQL + Chart"""
        try:
            # Generate SQL
            if db_type == "postgresql":
                db = get_db("postgresql://inventory_user:inventory_pass@localhost:5432/inventory_db", "postgresql")
            else:
                db = get_db("data/inventory.db", "sqlite")
            t_sql0 = time.perf_counter()
            sql = generate_sql(
                question=user_question,
                db=db,
                model="openai/gpt-oss-20b",
                examples_path=examples_path,
                top_k=top_k,
                use_semantic_search=use_retriever
            )
            t_sql1 = time.perf_counter()
            (debug_base or {}).get("steps", []).append({
                "step": "sql_generate",
                "duration_ms": (t_sql1 - t_sql0) * 1000,
                "detail": {"model": "openai/gpt-oss-20b"}
            })
            
            if not sql:
                return {
                    "success": False,
                    "error": "Unable to generate SQL query",
                    "intent": "visualize",
                    "agent": "viz_agent"
                }
            
            # Execute SQL
            t_exec0 = time.perf_counter()
            df, error = run_sql_unified(sql, db_type)
            t_exec1 = time.perf_counter()
            (debug_base or {}).get("steps", []).append({
                "step": "sql_execute",
                "duration_ms": (t_exec1 - t_exec0) * 1000,
                "detail": {"rows": 0 if error else len(df), "error": error}
            })
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
            
            # Plan + Render chart via agent (không tạo summary cho visualize)
            t_viz0 = time.perf_counter()
            viz = self.viz_agent.plan_and_render(user_question, df)
            t_viz1 = time.perf_counter()
            (debug_base or {}).get("steps", []).append({
                "step": "viz_plan_render",
                "duration_ms": (t_viz1 - t_viz0) * 1000,
                "detail": viz.get("spec")
            })
            chart_result = viz.get("figure")
            
            return {
                "success": True,
                "intent": "visualize",
                "agent": "viz_agent",
                "sql": sql,
                "data": df,
                "chart": chart_result,
                "viz_spec": viz.get("spec"),
                "message": f"📊 Chart generated successfully from {len(df)} records!",
                "debug": {
                    **(debug_base or {}),
                    "t_sql_generate_ms": (t_sql1 - t_sql0)*1000,
                    "t_sql_execute_ms": (t_exec1 - t_exec0)*1000,
                    "t_viz_ms": (t_viz1 - t_viz0)*1000,
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Chart generation error: {str(e)}",
                "intent": "visualize",
                "agent": "viz_agent"
            }
    
    def _handle_report_intent(self, user_question: str, db_type: str, use_retriever: bool, 
                            examples_path: str, top_k: int) -> dict:
        """Handle report intent - Generate reports"""
        try:
            # Parse report type from user question
            report_type = self._parse_report_type(user_question)
            params = self._parse_report_params(user_question)
            
            # Generate report
            result = self.report_agent.generate_report(
                report_type=report_type,
                db_type=db_type,
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
    
    def _handle_schema_intent(self, user_question: str, db_type: str) -> dict:
        """Handle schema intent - Database structure information"""
        try:
            from agents.sql_agent import get_schema_info
            
            if db_type == "postgresql":
                db = get_db("postgresql://inventory_user:inventory_pass@localhost:5432/inventory_db", "postgresql")
            else:
                db = get_db("data/inventory.db", "sqlite")
            schema_info = get_schema_info(db)
            
            return {
                "success": True,
                "intent": "schema",
                "agent": "schema_agent",
                "sql": "Schema Information",
                "data": None,
                "schema_info": schema_info,
                "message": "📋 Database schema information retrieved successfully!"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Schema processing error: {str(e)}",
                "intent": "schema",
                "agent": "schema_agent"
            }
