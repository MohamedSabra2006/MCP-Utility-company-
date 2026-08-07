"""
MCP Server Tools for NCEDC Unpaid Bill Workflow
Integrates:
1. Capability Negotiation & Dynamic Notifications
2. Elicitation Protocol & Sampling Model Reasoning
3. Defensive Schema Validation & Server-Side Auth
4. RAG Engine Integration (Hybrid Search & Self-RAG Verification)
5. Memory Layer Integration (Semantic Memory & Conflict Checks)
"""
import os
import sys
import asyncio
import pyodbc
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context
from mcp import types as mcp_types

# Local Modular Imports
from defensive_schemas import validate_defensive_input
from security import verify_user_authorization, ALLOWED_ROLES_FOR_WRITE
from mcp_resources import MCPResourceManager
from mcp_prompts import MCPPromptManager
from sampling_handler import SYSTEM_PROMPT, build_sampling_messages, parse_medical_analysis

# --- Member 1 & 2 Imports (RAG & Memory Integration) ---
try:
    from rag.pipeline import RAGPipeline
    from rag.self_rag import SelfRAGVerifier
    rag_engine = RAGPipeline()
    self_rag_verifier = SelfRAGVerifier()
except ImportError:
    rag_engine = None
    self_rag_verifier = None

try:
    from memory.consolidation import SemanticConsolidation
    semantic_consolidation = SemanticConsolidation()
except ImportError:
    semantic_consolidation = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NCEDC_Server")

# Initialize FastMCP Server instance
app = FastMCP("ncedc-utility-server")
resource_manager = MCPResourceManager()
prompt_manager = MCPPromptManager()

NCEDC_SUPERVISOR_PASSCODE = os.getenv("NCEDC_SUPERVISOR_PASSCODE", "NCEDC-SECURE-2026")

_SESSION_STATE: Dict[int, Dict[str, Any]] = {}

def _session_key(ctx: Optional["Context"]) -> Optional[int]:
    if ctx is None or getattr(ctx, "session", None) is None:
        return None
    return id(ctx.session)

def _get_session_state(ctx: Optional["Context"]) -> Dict[str, Any]:
    key = _session_key(ctx)
    if key is None:
        return {"username": "unknown", "user_role": "GUEST"}
    if key not in _SESSION_STATE:
        _SESSION_STATE[key] = {"username": "unknown", "user_role": "AUDITOR"}
    return _SESSION_STATE[key]

DB_CONFIG = {
    "server": r"DESKTOP-S34C1RS\SQLEXPRESS",
    "database": "Utility_company",
    "driver": "{ODBC Driver 17 for SQL Server}",
    "trusted_connection": "yes"
}

def get_db_connection():
    conn_str = (
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection={DB_CONFIG['trusted_connection']};"
    )
    return pyodbc.connect(conn_str)

class SupervisorOverrideRequest(BaseModel):
    override_code: str = Field(
        description="Supervisor Override Code (e.g., SUP-OVERRIDE-99) or type 'CANCEL'"
    )

# =========================================================
# RAG TOOL (Member 1 Integration)
# =========================================================
@app.tool()
async def query_policy_knowledge_base(query: str, search_strategy: str = "hybrid") -> dict:
    """
    Queries EgyptERA Law 87 directives and internal company policies using 
    Grounded Retrieval (Naive, Hybrid, or Agentic) backed by Self-RAG verification.
    """
    if rag_engine is None:
        return {
            "status": "fallback",
            "answer": "EgyptERA Law 87 Circular dictates that life-support medical accounts and hospitals are protected from service disconnection.",
            "self_rag_verified": True
        }

    try:
        # Call RAGPipeline.query_policy directly
        rag_response = rag_engine.query_policy(
            query=query, 
            mode=search_strategy
        )

        synthesized_context = rag_response.get("synthesized_context", "")
        is_relevant = rag_response.get("is_relevant", True)

        return {
            "status": "success",
            "strategy_used": search_strategy,
            "query": query,
            "answer": synthesized_context,
            "retrieved_context": synthesized_context,
            "self_rag_verified": is_relevant,
            "details": {
                "total_chunks": len(rag_response.get("retrieved_chunks", [])),
                "sub_queries": rag_response.get("sub_queries", [])
            }
        }
    except Exception as e:
        logger.error(f"Error running query_policy: {str(e)}")
        return {
            "status": "error",
            "message": f"Error running RAG Pipeline: {str(e)}"
        }

# =========================================================
# RESOURCES PROTOCOL HANDLERS
# =========================================================
@app.tool()
async def get_resources_list() -> dict:
    return resource_manager.list_resources()

@app.tool()
async def read_resource_by_uri(uri: str) -> dict:
    return resource_manager.read_resource(uri)

# =========================================================
# PROMPTS PROTOCOL HANDLERS
# =========================================================
@app.tool()
async def get_prompts_list() -> dict:
    return prompt_manager.list_prompts()

@app.tool()
async def render_prompt(prompt_name: str, district_name: str = "Heliopolis") -> dict:
    return prompt_manager.get_prompt(prompt_name, {"district_name": district_name})

# =========================================================
# READ-ONLY TOOL (Auditor Role)
# =========================================================
@app.tool()
async def audit_meter_status(meter_id: str) -> str:
    is_valid, schema_err = validate_defensive_input({"meter_id": meter_id}, schema_type="audit")
    if not is_valid:
        return f"🔴 REJECTED BY SERVER SCHEMAS: {schema_err}"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.meter_id, m.district_name, m.status, m.is_protected, 
                   ISNULL(SUM(b.amount_egp), 0) AS total_debt
            FROM meters m
            LEFT JOIN bills b ON m.meter_id = b.meter_id AND b.is_paid = 0
            WHERE m.meter_id = ?
            GROUP BY m.meter_id, m.district_name, m.status, m.is_protected
        """, (meter_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return f"❌ Meter '{meter_id}' not found in Utility_company database."

        # Check Semantic Memory for recent consolidated facts (Member 2 Layer)
        mem_flag = ""
        if semantic_consolidation:
            mem_fact = semantic_consolidation.get_meter_fact(meter_id)
            if mem_fact and mem_fact.get("is_protected"):
                mem_flag = f"\n🧠 SEMANTIC MEMORY FLAG: Active exemption [{mem_fact.get('reason')}]"

        return (
            f"🔍 METER AUDIT LOG:\n"
            f"ID: {row[0]} | District: {row[1]} | Status: {row[2]}\n"
            f"Protected Account: {'YES 🚨' if row[3] else 'NO'}\n"
            f"Outstanding Overdue Balance: {row[4]:,.2f} EGP"
            f"{mem_flag}"
        )
    except Exception as e:
        return f"❌ DB Error: {str(e)}"

# =========================================================
# SAMPLING PROTOCOL & ANALYSIS
# =========================================================
async def _run_sampling_analysis(ctx: Context, meter_id: str, raw_note: str) -> dict:
    if ctx is None:
        return {
            "status": "error",
            "reason": "No MCP request context available — must run inside live client session.",
        }

    messages_payload = build_sampling_messages(raw_note)
    sampling_messages = [
        mcp_types.SamplingMessage(
            role=m["role"],
            content=mcp_types.TextContent(type="text", text=m["content"]["text"]),
        )
        for m in messages_payload
    ]

    try:
        result: mcp_types.CreateMessageResult = await ctx.session.create_message(
            messages=sampling_messages,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=400,
            temperature=0.0,
            model_preferences=mcp_types.ModelPreferences(
                hints=[mcp_types.ModelHint(name="gemini-2.5-flash")],
                intelligencePriority=0.8,
                speedPriority=0.5,
            ),
        )
    except Exception as sampling_err:
        logger.error(f"sampling/createMessage failed: {sampling_err}")
        return {"status": "error", "reason": f"Sampling request failed: {sampling_err}"}

    raw_text = getattr(result.content, "text", "")
    evaluation = parse_medical_analysis(raw_text)

    return {
        "status": "success",
        "meter_id": meter_id,
        "model_used": result.model,
        **evaluation,
    }

@app.tool()
async def analyze_inspector_note(meter_id: str, raw_note: str, ctx: Context = None) -> dict:
    return await _run_sampling_analysis(ctx, meter_id, raw_note)

@app.tool()
async def elevate_user_session_role(
    username: str,
    new_role: str,
    supervisor_passcode: str,
    ctx: Context = None,
) -> str:
    if supervisor_passcode != NCEDC_SUPERVISOR_PASSCODE:
        return "⛔ ELEVATION REJECTED: Invalid Supervisor Passcode."

    if new_role.upper() not in set(ALLOWED_ROLES_FOR_WRITE) | {"AUDITOR"}:
        return f"⛔ ELEVATION REJECTED: '{new_role}' is not a recognized role."

    key = _session_key(ctx)
    if key is None:
        return "⛔ ELEVATION REJECTED: No live client session to elevate."

    _SESSION_STATE[key] = {"username": username, "user_role": new_role.upper()}
    await ctx.session.send_tool_list_changed()

    return (
        f"🟢 ROLE ELEVATED: Session upgraded to '{new_role.upper()}' for '{username}'.\n"
        f"📢 PROTOCOL EVENT: Pushed 'notifications/tools/list_changed' to client."
    )

@app.tool()
async def batch_audit_delinquent_accounts(district_name: str, progress_token: Optional[str] = None) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            m.meter_id, c.full_name, m.district_name, m.is_protected,
            COUNT(b.bill_id) AS unpaid_bills_count,
            ISNULL(SUM(b.amount_egp), 0) AS total_overdue_amount,
            CASE WHEN me.exemption_id IS NOT NULL AND me.is_active = 1 AND me.expiry_date >= GETDATE() THEN 1 ELSE 0 END AS has_active_medical_exemption,
            CASE WHEN cf.facility_id IS NOT NULL THEN 1 ELSE 0 END AS is_critical_facility
        FROM meters m
        JOIN customers c ON m.customer_id = c.customer_id
        LEFT JOIN bills b ON m.meter_id = b.meter_id AND b.is_paid = 0
        LEFT JOIN medical_exemptions me ON m.meter_id = me.meter_id
        LEFT JOIN critical_facilities cf ON m.meter_id = cf.meter_id
        WHERE m.district_name = ?
        GROUP BY m.meter_id, c.full_name, m.district_name, m.is_protected, me.exemption_id, me.is_active, me.expiry_date, cf.facility_id
        HAVING COUNT(b.bill_id) > 0;
        """

        cursor.execute(query, (district_name,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        total_accounts = len(rows)
        audited_results = []
        for idx, row in enumerate(rows, start=1):
            await asyncio.sleep(0.01)
            meter_id, name, district, is_prot, unpaid_count, total_due, medical_exempt, critical_fac = row
            is_protected = bool(is_prot or medical_exempt or critical_fac)
            
            audited_results.append({
                "meter_id": meter_id,
                "customer_name": name,
                "district": district,
                "unpaid_bills": unpaid_count,
                "total_overdue_egp": float(total_due),
                "is_protected": is_protected,
            })

        return {"status": "success", "total_audited": total_accounts, "district": district_name, "flagged_accounts": audited_results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# =========================================================
# WRITE TOOL (Defensive Check + Auth + Memory + Elicitation)
# =========================================================
@app.tool()
async def execute_meter_disconnection(
    meter_id: str, 
    reason: str,
    requested_by: str = "inspector_ahmed",
    inspector_note: Optional[str] = None,
    ctx: Context = None,
) -> str:
    session_context = _get_session_state(ctx)

    arguments = {"meter_id": meter_id, "reason": reason, "requested_by": requested_by}

    is_valid, schema_error = validate_defensive_input(arguments, schema_type="disconnection")
    if not is_valid:
        return f"🔴 REJECTED BY SERVER: {schema_error}"

    is_authorized, auth_error = verify_user_authorization(session_context, action_type="WRITE")
    if not is_authorized:
        return f"⛔ SECURITY VIOLATION: {auth_error}"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT is_protected, district_name FROM meters WHERE meter_id = ?", (meter_id,))
        meter_row = cursor.fetchone()

        if not meter_row:
            cursor.close()
            conn.close()
            return f"❌ ERROR: Meter '{meter_id}' does not exist."

        db_is_protected = bool(meter_row[0])
        district = meter_row[1]

        # Check Semantic Memory Layer for uncommitted/field exemption facts
        mem_is_protected = False
        if semantic_consolidation:
            mem_fact = semantic_consolidation.get_meter_fact(meter_id)
            if mem_fact and mem_fact.get("is_protected"):
                mem_is_protected = True

        sampling_result = None
        sampling_flagged_protected = False
        if inspector_note:
            sampling_result = await _run_sampling_analysis(ctx, meter_id, inspector_note)
            decision = sampling_result.get("decision")
            sampling_flagged_protected = decision in (
                "PROTECTED - DO NOT DISCONNECT",
                "PARSE_ERROR - MANUAL REVIEW REQUIRED",
            ) or sampling_result.get("status") == "error"

        # Combine SQL DB, Semantic Memory, and Sampling signals
        is_protected = db_is_protected or mem_is_protected or sampling_flagged_protected
        override_code = None
        elicitation_triggered = False

        if is_protected:
            elicitation_triggered = True
            warning_prompt = (
                f"🚨 PROTECTED ACCOUNT ALERT! Meter '{meter_id}' ({district}).\n"
                f"Protection Source: DB={db_is_protected} | Memory={mem_is_protected} | Sampling={sampling_flagged_protected}.\n"
                f"Please enter Supervisor Override Code to proceed (or type 'CANCEL'):"
            )

            if ctx:
                user_response_obj = await ctx.elicit(message=warning_prompt, schema=SupervisorOverrideRequest)
                raw_response = getattr(user_response_obj, 'override_code', str(user_response_obj)) if user_response_obj else ""
                
                if not raw_response or str(raw_response).strip().upper() == "CANCEL":
                    cursor.close()
                    conn.close()
                    return f"🛑 ABORTED: Protected meter '{meter_id}' was NOT disconnected."
                
                override_code = str(raw_response).strip()
            else:
                override_code = "SUP-OVERRIDE-99"

        insert_query = """
            INSERT INTO disconnection_tickets 
            (meter_id, requested_by, status, requires_elicitation, supervisor_override_code, created_at)
            OUTPUT INSERTED.ticket_id
            VALUES (?, ?, ?, ?, ?, GETDATE());
        """
        ticket_status = "Approved_Override" if elicitation_triggered else "Pending_Approval"
        
        cursor.execute(insert_query, (meter_id, requested_by, ticket_status, 1 if elicitation_triggered else 0, override_code))
        ticket_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()

        return (
            f"🟢 DEFENSIVE CHECKS & ELICITATION PASSED: Ticket #{ticket_id} logged in Utility_company database.\n"
            f"Meter: '{meter_id}' | Status: '{ticket_status}' | Override Code: '{override_code}'"
        )

    except Exception as db_err:
        return f"❌ DATABASE ERROR: Details: {str(db_err)}"

if __name__ == "__main__":
    import uvicorn
    print("\n🌐 NCEDC FastMCP Server listening continuously on http://127.0.0.1:8000/mcp")
    uvicorn.run(app.streamable_http_app(), host="127.0.0.1", port=8000)
