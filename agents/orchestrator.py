"""
Orchestrator Agent - Điều phối workflow giữa các agent
Quyết định gọi agent nào dựa trên intent classification
"""

from agents.intent_agent import IntentClassificationAgent
from agents.sql_agent import generate_sql
from agents.viz_agent import VisualizationAgent
from agents.response_agent import ResponseAgent
from agents.analytics_agent import AnalyticsAgent
from db.connection import get_db, run_sql_unified
from langsmith.run_helpers import traceable
import pandas as pd
import time
import re


class OrchestratorAgent:
    def __init__(self, db_type: str = "postgresql"):
        self.intent_agent = IntentClassificationAgent()
        self.response_agent = ResponseAgent()
        self.viz_agent = VisualizationAgent()
        self.analytics_agent = AnalyticsAgent(db_type=db_type)
    
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
        
        
        elif intent == "schema":
            return self._handle_schema_intent(user_question, db_type)
        
        elif intent == "inventory_analytics":
            return self._handle_inventory_analytics_intent(
                user_question, db_type,
                debug_base={"intent_result": intent_result, "t_intent_ms": (t1 - t0)*1000, "steps": steps}
            )
        
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
            result, gen_debug = generate_sql(
                question=user_question,
                db=db,
                model="openai/gpt-oss-20b",
                examples_path=examples_path,
                top_k=top_k,
                use_semantic_search=use_retriever,
                return_debug=True,
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
                    "message": "📋 Database schema information retrieved successfully!",
                    "debug": {**(debug_base or {}), "sql_generate": gen_debug},
                }
            
            if not result:
                return {
                    "success": False,
                    "error": "Unable to generate SQL query",
                    "intent": "query",
                    "agent": "sql_agent",
                    "debug": {**(debug_base or {}), "sql_generate": gen_debug},
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
                    "agent": "sql_agent",
                    "sql": result,
                    "debug": {**(debug_base or {}), "sql_generate": gen_debug},
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
                    "sql_generate": gen_debug,
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
            sql, gen_debug = generate_sql(
                question=user_question,
                db=db,
                model="openai/gpt-oss-20b",
                examples_path=examples_path,
                top_k=top_k,
                use_semantic_search=use_retriever,
                return_debug=True,
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
                    "agent": "viz_agent",
                    "debug": {**(debug_base or {}), "sql_generate": gen_debug},
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
                    "agent": "viz_agent",
                    "sql": sql,
                    "debug": {**(debug_base or {}), "sql_generate": gen_debug},
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
                    "sql_generate": gen_debug,
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Chart generation error: {str(e)}",
                "intent": "visualize",
                "agent": "viz_agent"
            }
    
    
    
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
    
    def _extract_top_n(self, question: str) -> int:
        """Extract 'top N' from question, default to 20"""
        # Tìm pattern "top 10", "top 20", etc.
        match = re.search(r'\btop\s+(\d+)\b', question.lower())
        if match:
            return int(match.group(1))
        
        # Nếu có từ "critical" or "urgent" or "warning" -> chỉ show critical/warning
        if any(word in question.lower() for word in ['critical', 'urgent', 'cảnh báo', 'khẩn cấp']):
            return 10  # Default 10 for critical
        
        # Default: top 20
        return 20
    
    def _handle_inventory_analytics_intent(self, user_question: str, db_type: str, debug_base: dict | None = None) -> dict:
        """Handle inventory analytics intent - FOCUS: Stock Cover Days only"""
        try:
            question_lower = user_question.lower()
            
            # Extract top N from question
            limit = self._extract_top_n(user_question)
            
            # Calculate stock cover days
            df = self.analytics_agent.calculate_stock_cover_days()
            
            if df.empty:
                return {
                    "success": False,
                    "error": "No stock cover data available",
                    "intent": "inventory_analytics",
                    "agent": "analytics_agent"
                }
            
            # Extract threshold from question (e.g., "less than 30 days", "under 45 days")
            threshold = None
            threshold_patterns = [
                r'(?:less than|under|below|dưới|nhỏ hơn)\s+(\d+)\s*day',
                r'(?:greater than|above|over|trên|lớn hơn)\s+(\d+)\s*day',
            ]
            
            for pattern in threshold_patterns:
                match = re.search(pattern, question_lower)
                if match:
                    threshold = int(match.group(1))
                    is_less_than = any(word in pattern for word in ['less', 'under', 'below', 'dưới', 'nhỏ'])
                    break
            
            # Filter based on question intent
            if threshold is not None:
                # Filter by specific threshold
                if is_less_than:
                    df = df[(df['stock_cover_days'].notna()) & (df['stock_cover_days'] < threshold)]
                else:
                    df = df[(df['stock_cover_days'].notna()) & (df['stock_cover_days'] > threshold)]
            elif 'critical' in question_lower and 'warning' not in question_lower:
                # CHỈ critical items (< 15 days)
                df = df[df['stock_status'] == 'Critical']
            elif 'warning' in question_lower or 'cảnh báo' in question_lower:
                # Warning + Critical (< 30 days)
                df = df[df['stock_status'].isin(['Critical', 'Warning'])]
            elif 'low' in question_lower or 'lowest' in question_lower or 'sắp hết' in question_lower:
                # Top N lowest stock cover (exclude No Sales)
                df = df[df['stock_status'] != 'No Sales']
            else:
                # Default: exclude "No Sales" items
                df = df[df['stock_status'] != 'No Sales']
            
            # Apply limit AFTER filtering
            df = df.head(limit)
            
            analytics_type = "stock_cover_days"
            
            if df.empty:
                return {
                    "success": False,
                    "error": "No data available for this analytics request",
                    "intent": "inventory_analytics",
                    "agent": "analytics_agent"
                }
            
            # Generate natural language summary
            nl_summary = self.analytics_agent.generate_analytics_report(user_question, df)
            
            # Add context note
            if limit < 100:
                nl_summary += f"\n\n*💡 Hiển thị top {len(df)} items (filtered). Hỏi 'top 50' hoặc 'all' để xem nhiều hơn.*"
            
            # Generate table markdown
            table_md = None
            try:
                df_for_md = df.copy()
                for col in df_for_md.select_dtypes(include=["number"]).columns:
                    df_for_md[col] = df_for_md[col].round(2)
                table_md = df_for_md.to_markdown(index=False)
            except Exception:
                table_md = None
            
            return {
                "success": True,
                "intent": "inventory_analytics",
                "agent": "analytics_agent",
                "analytics_type": analytics_type,
                "sql": None,
                "data": df,
                "response": nl_summary,
                "response_table_md": table_md,
                "message": f"📊 Analytics completed! Generated {len(df)} insights.",
                "debug": debug_base
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"Analytics processing error: {str(e)}\n{traceback.format_exc()}",
                "intent": "inventory_analytics",
                "agent": "analytics_agent"
            }
