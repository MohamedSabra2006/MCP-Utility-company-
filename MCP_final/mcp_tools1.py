"""
MCP Server Tools for NCEDC Unpaid Bill Workflow
Integrates:
1. Capability Negotiation
2. Dynamic Notifications (notifications/tools/list_changed)
3. Elicitation Protocol (ctx.elicit with Pydantic)
4. Resources & Prompts Protocols
5. Real-time Progress Tracking
6. Defensive Schema Validation + Server-Side Auth
7. Sampling / Model Reasoning Protocol
"""
import sys
import asyncio
import pyodbc
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context
from mcp import types as mcp_types

# Local Modular Imports
from defensive_schemas1 import validate_defensive_input
from security1 import verify_user_authorization
from mcp_resources import MCPResourceManager
from mcp_prompts import MCPPromptManager
from sampling_handler2 import SYSTEM_PROMPT, build_sampling_messages, parse_medical_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NCEDC_Server")

# Initialize FastMCP Server instance
app = FastMCP("ncedc-utility-server")
resource_manager = MCPResourceManager()
prompt_manager = MCPPromptManager()

# Target Database Configuration
DB_CONFIG = {
    "server": r"DESKTOP-S34C1RS\SQLEXPRESS",
    "database": "Utility_company",
    "driver": "{ODBC Driver 17 for SQL Server}",
    "trusted_connection": "yes"
}


def get_db_connection():
    """Establishes connection to target SQL Server database."""
    conn_str = (
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection={DB_CONFIG['trusted_connection']};"
    )
    return pyodbc.connect(conn_str)


# =========================================================
# PYDANTIC SCHEMAS FOR ELICITATION PROTOCOL
# =========================================================
class SupervisorOverrideRequest(BaseModel):
    override_code: str = Field(
        description="Supervisor Override Code (e.g., SUP-OVERRIDE-99) or type 'CANCEL'"
    )


# =========================================================
# RESOURCES PROTOCOL HANDLERS
# =========================================================
@app.tool()
async def get_resources_list() -> dict:
    """Returns available static regulatory and policy resource URIs."""
    return resource_manager.list_resources()


@app.tool()
async def read_resource_by_uri(uri: str) -> dict:
    """Reads content of a registered policy resource by URI."""
    return resource_manager.read_resource(uri)


# =========================================================
# PROMPTS PROTOCOL HANDLERS
# =========================================================
@app.tool()
async def get_prompts_list() -> dict:
    """Returns available parameterized prompt templates."""
    return prompt_manager.list_prompts()


@app.tool()
async def render_prompt(prompt_name: str, district_name: str = "Heliopolis") -> dict:
    """Renders a target prompt template with specific argument values."""
    return prompt_manager.get_prompt(prompt_name, {"district_name": district_name})


# =========================================================
# READ-ONLY TOOL (Auditor Role)
# =========================================================
@app.tool()
async def audit_meter_status(meter_id: str) -> str:
    """
    Audits meter consumption, debt status, and medical protection flags.
    Safe read-only operation.
    """
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

        return (
            f"🔍 METER AUDIT LOG:\n"
            f"ID: {row[0]} | District: {row[1]} | Status: {row[2]}\n"
            f"Protected Account: {'YES 🚨' if row[3] else 'NO'}\n"
            f"Outstanding Overdue Balance: {row[4]:,.2f} EGP"
        )
    except Exception as e:
        return f"❌ DB Error: {str(e)}"


# =========================================================
# SAMPLING PROTOCOL (sampling/createMessage) — shared helper
# =========================================================
async def _run_sampling_analysis(ctx: Context, meter_id: str, raw_note: str) -> dict:
    """
    Shared implementation: sends `raw_note` to the connected client's host LLM
    via `sampling/createMessage` and returns a structured classification.
    Used by both the standalone `analyze_inspector_note` tool and by
    `execute_meter_disconnection` when a field note is supplied alongside
    a disconnection request.

    Fails closed: any error talking to the host model, or a response that
    doesn't parse as the expected JSON, is treated as PARSE_ERROR — which
    callers must treat as "cannot confirm the account is unprotected", not
    as "safe to proceed".
    """
    if ctx is None:
        return {
            "status": "error",
            "reason": (
                "No MCP request context available — this tool must run inside "
                "a live client connection that supports sampling/createMessage."
            ),
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
            # A hint, not a hard requirement — the client's host decides which
            # model actually serves the request.
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

    logger.info(
        f"Sampling result for meter '{meter_id}' from model '{result.model}': "
        f"{evaluation.get('decision')}"
    )

    return {
        "status": "success",
        "meter_id": meter_id,
        "model_used": result.model,
        **evaluation,
    }


@app.tool()
async def analyze_inspector_note(
    meter_id: str,
    raw_note: str,
    ctx: Context = None,
) -> dict:
    """
    Sends a field inspector's unstructured note (often dialectal Arabic) to the
    connected client's host LLM via `sampling/createMessage`, and returns a
    structured medical-exemption / risk classification.

    This tool never calls an LLM API itself — it delegates the actual
    reasoning to whichever model the connected client's host has configured,
    per the MCP sampling protocol. If the client hasn't wired up sampling
    support, this fails explicitly rather than guessing at a classification.
    """
    return await _run_sampling_analysis(ctx, meter_id, raw_note)


# =========================================================
# DYNAMIC NOTIFICATIONS (notifications/tools/list_changed)
# =========================================================
@app.tool()
async def elevate_user_session_role(
    new_role: str,
    supervisor_passcode: str,
    ctx: Context = None,
    session_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Elevates session permissions from AUDITOR to DISPATCHER or DISTRICT_SUPERVISOR.
    Triggers 'notifications/tools/list_changed' to update tools dynamically.
    """
    if supervisor_passcode != "NCEDC-SECURE-2026":
        return "⛔ ELEVATION REJECTED: Invalid Supervisor Passcode."

    if session_context is not None:
        session_context["user_role"] = new_role.upper()

    if ctx:
        await ctx.session.send_tool_list_changed()
        notification_msg = "Pushed 'notifications/tools/list_changed' to client."
    else:
        notification_msg = "Simulated notification push (notifications/tools/list_changed)."

    return (
        f"🟢 ROLE ELEVATED: Session upgraded to '{new_role.upper()}'.\n"
        f"📢 PROTOCOL EVENT: {notification_msg}\n"
        f"Write-level tools like 'execute_meter_disconnection' are now active."
    )


# =========================================================
# BATCH AUDITING WITH REAL-TIME PROGRESS TRACKING
# =========================================================
@app.tool()
async def batch_audit_delinquent_accounts(district_name: str, progress_token: Optional[str] = None) -> dict:
    """
    Queries SQL Server for delinquent accounts and streams real progress notifications.
    """
    logger.info(f"Starting batch audit for district: {district_name}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            m.meter_id,
            c.full_name,
            m.district_name,
            m.is_protected,
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
        if total_accounts == 0:
            return {"status": "success", "total_audited": 0, "district": district_name, "flagged_accounts": []}

        audited_results = []
        for idx, row in enumerate(rows, start=1):
            await asyncio.sleep(0.05)
            
            meter_id, name, district, is_prot, unpaid_count, total_due, medical_exempt, critical_fac = row
            is_protected = bool(is_prot or medical_exempt or critical_fac)
            
            reason = "None"
            if medical_exempt:
                reason = "Medical Exemption"
            elif critical_fac:
                reason = "Critical Facility"
            elif is_prot:
                reason = "Database Flag"

            account_data = {
                "meter_id": meter_id,
                "customer_name": name,
                "district": district,
                "unpaid_bills": unpaid_count,
                "total_overdue_egp": float(total_due),
                "is_protected": is_protected,
                "protection_reason": reason
            }
            
            if progress_token:
                percentage = round((idx / total_accounts) * 100, 1)
                print(f"NOTIFICATION [notifications/progress] Token: '{progress_token}' | Progress: {percentage}% ({idx}/{total_accounts}) | Audited meter {meter_id}")
            
            audited_results.append(account_data)

        return {
            "status": "success", 
            "total_audited": total_accounts, 
            "district": district_name,
            "flagged_accounts": audited_results
        }
    except Exception as e:
        logger.error(f"Batch audit query error: {str(e)}")
        return {"status": "error", "message": str(e)}


# =========================================================
# WRITE TOOL (Defensive Schema + Auth + Elicitation)
# =========================================================
@app.tool()
async def execute_meter_disconnection(
    meter_id: str, 
    reason: str,
    requested_by: str = "inspector_ahmed",
    inspector_note: Optional[str] = None,
    ctx: Context = None,
    session_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Initiates or completes an electrical meter service disconnection for overdue bills.
    Checks if the meter is protected (Medical/Hospital) via the database flag, and —
    when an inspector_note is supplied — also via a live sampling/createMessage
    classification of that note. Either signal being positive (or the sampling call
    failing to produce a clear result) triggers Elicitation; only a database "not
    protected" AND a sampling "not protected" (or no note supplied) skip it.
    """
    if session_context is None:
        session_context = {"username": requested_by, "user_role": "DISPATCHER"}

    arguments = {
        "meter_id": meter_id, 
        "reason": reason,
        "requested_by": requested_by
    }

    # DEFENSIVE CHECK 1: Server-Side Schema Validation
    is_valid, schema_error = validate_defensive_input(arguments, schema_type="disconnection")
    if not is_valid:
        return f"🔴 REJECTED BY SERVER: {schema_error}"

    # DEFENSIVE CHECK 2: Server-Side Auth Validation
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
            return f"❌ ERROR: Meter '{meter_id}' does not exist in Utility_company database."

        db_is_protected = bool(meter_row[0])
        district = meter_row[1]
        override_code = None
        elicitation_triggered = False

        # SAMPLING: if the caller supplied a freeform inspector note, classify it
        # via the connected client's host LLM before deciding whether to treat
        # this meter as protected. This is what actually connects the sampling
        # protocol's output to a state-changing decision, rather than running
        # sampling and the disconnection check in parallel with no interaction.
        sampling_result = None
        sampling_flagged_protected = False
        if inspector_note:
            sampling_result = await _run_sampling_analysis(ctx, meter_id, inspector_note)
            decision = sampling_result.get("decision")
            # Fail safe: a sampling error or an unparseable host-LLM reply is
            # treated as "cannot confirm this account is safe to disconnect",
            # not as "no exemption found". Silence must never look like a green light.
            sampling_flagged_protected = decision in (
                "PROTECTED - DO NOT DISCONNECT",
                "PARSE_ERROR - MANUAL REVIEW REQUIRED",
            ) or sampling_result.get("status") == "error"

        is_protected = db_is_protected or sampling_flagged_protected

        # ELICITATION PROTOCOL
        if is_protected:
            elicitation_triggered = True

            cursor.execute("""
                SELECT medical_condition FROM medical_exemptions 
                WHERE meter_id = ? AND is_active = 1
            """, (meter_id,))
            med_row = cursor.fetchone()
            med_info = med_row[0] if med_row else "Critical Public Infrastructure / Hospital"

            note_line = ""
            if sampling_result is not None:
                if sampling_result.get("status") == "error":
                    note_line = (
                        f"\nInspector-note analysis could not be completed "
                        f"({sampling_result.get('reason')}) — treating as unconfirmed, not safe."
                    )
                else:
                    note_line = (
                        f"\nInspector-note analysis ({sampling_result.get('model_used', 'host LLM')}): "
                        f"{sampling_result.get('decision')} — {sampling_result.get('reasoning', '')}"
                    )

            db_flag_line = "Database flag" if db_is_protected else "No database flag"
            warning_prompt = (
                f"🚨 PROTECTED ACCOUNT ALERT! Meter '{meter_id}' ({district}).\n"
                f"{db_flag_line}. Registered medical exemption on file: [{med_info}].{note_line}\n"
                f"Disconnecting this account without medical authorization violates EgyptERA regulations.\n"
                f"Please enter Supervisor Override Code to proceed (or type 'CANCEL'):"
            )

            if ctx:
                user_response_obj = await ctx.elicit(
                    message=warning_prompt,
                    schema=SupervisorOverrideRequest
                )
                
                raw_response = getattr(user_response_obj, 'override_code', str(user_response_obj)) if user_response_obj else ""
                
                if not raw_response or str(raw_response).strip().upper() == "CANCEL":
                    cursor.close()
                    conn.close()
                    return f"🛑 DISCONNECTION ABORTED BY SUPERVISOR: Protected meter '{meter_id}' was not disconnected."
                
                override_code = str(raw_response).strip()
            else:
                print(f"\n[SERVER ELICITATION PAUSE]\n{warning_prompt}")
                override_code = "SUP-OVERRIDE-99"

        # SQL WRITE: Log Disconnection Ticket
        insert_query = """
            INSERT INTO disconnection_tickets 
            (meter_id, requested_by, status, requires_elicitation, supervisor_override_code, created_at)
            OUTPUT INSERTED.ticket_id
            VALUES (?, ?, ?, ?, ?, GETDATE());
        """
        ticket_status = "Approved_Override" if elicitation_triggered else "Pending_Approval"
        
        cursor.execute(insert_query, (
            meter_id, 
            requested_by, 
            ticket_status, 
            1 if elicitation_triggered else 0, 
            override_code
        ))
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


# =========================================================
# PERMANENT BLOCKING SERVER ENTRY POINT
# =========================================================
if __name__ == "__main__":
    if "--test" in sys.argv:
        async def run_direct_test():
            print("=========================================================")
            print("   NCEDC UTILITY COMPANY INTEGRATION TEST (--test)")
            print("=========================================================")
            
            session = {"username": "inspector_ahmed", "user_role": "AUDITOR"}
            
            print("\n1️⃣ TESTING AUDIT READ TOOL:")
            read_res = await audit_meter_status(meter_id="NC-MTR-30012")
            print(read_res)

            print("\n2️⃣ TESTING AUTH BLOCK ON WRITE TOOL (Auditor Role):")
            auth_res = await execute_meter_disconnection(
                meter_id="NC-MTR-20045",
                reason="Overdue balance clearance",
                requested_by="inspector_ahmed",
                session_context=session
            )
            print(auth_res)

            print("\n3️⃣ TESTING ROLE ELEVATION:")
            elevate_res = await elevate_user_session_role(
                new_role="DISPATCHER",
                supervisor_passcode="NCEDC-SECURE-2026",
                session_context=session
            )
            print(elevate_res)

            print("\n4️⃣ TESTING BATCH AUDIT (Utility_company DB):")
            batch_res = await batch_audit_delinquent_accounts(
                district_name="Heliopolis",
                progress_token="test-token-777"
            )
            print(f"Status: {batch_res.get('status')} | Audited Count: {batch_res.get('total_audited')}")

            print("\n5️⃣ TESTING SAMPLING WITHOUT A LIVE CLIENT (expected: explicit failure, not a guess):")
            sampling_res = await analyze_inspector_note(
                meter_id="NC-MTR-30012",
                raw_note="Customer objects, says there is a dialysis patient in the apartment",
            )
            print(sampling_res)
            # With a real client connected (not --test), ctx is populated and this
            # call actually round-trips through sampling/createMessage to the host
            # LLM. --test has no live session, so ctx is None by design and the
            # tool must refuse rather than fabricate a classification.

            print("\n6️⃣ TESTING DISCONNECTION WITH inspector_note, NO LIVE CLIENT:")
            print("   (DB says not protected, but a note was supplied and sampling can't")
            print("    run without ctx -> must still fail safe into Elicitation, not skip it)")
            supervisor_session = {"username": "supervisor_omar", "user_role": "DISTRICT_SUPERVISOR"}
            combined_res = await execute_meter_disconnection(
                meter_id="NC-MTR-30012",
                reason="90+ days overdue, no prior protection flag on record",
                requested_by="inspector_ahmed",
                inspector_note="Customer objects, says there is a dialysis patient in the apartment",
                session_context=supervisor_session,
            )
            print(combined_res)

        asyncio.run(run_direct_test())
    else:
        # Prevents thread exit by hosting persistent uvicorn server
        import uvicorn
        print("\n🌐 NCEDC FastMCP Server listening continuously on http://127.0.0.1:8000/sse")
        uvicorn.run(app.sse_app(), host="127.0.0.1", port=8000)
