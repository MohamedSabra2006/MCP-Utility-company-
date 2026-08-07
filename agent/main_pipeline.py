"""
NCEDC MCP Pipeline: End-to-End Live System Execution
Runs through real MCP tool calls, RAG policy retrieval, and memory-aware disconnection workflows.
"""
import asyncio
import logging
import sys

from agent_client import NCEDCClientAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("NCEDC_Pipeline")

def _text(call_tool_result) -> str:
    return "\n".join(getattr(block, "text", str(block)) for block in call_tool_result.content)

async def run_ncedc_pipeline(use_http: bool = False):
    print("==================================================")
    print("   NCEDC MCP SYSTEM - END-TO-END PIPELINE DEMO   ")
    print("==================================================\n")

    agent = NCEDCClientAgent()
    connect_cm = agent.connect_http() if use_http else agent.connect_stdio()

    async with connect_cm:
        logger.info("--- PHASE 1: Real initialize/initialized handshake ---")
        print(f"Declared server capabilities: {agent.server_capabilities}")
        print(f"Client mode after handshake:  {agent.mode}\n")

        logger.info("--- PHASE 2: Fetch Legal Policy Resource (resources/read) ---")
        resources = await agent.session.list_resources()
        policy_uri = next(r.uri for r in resources.resources if "disconnection-policy" in str(r.uri))
        policy = await agent.session.read_resource(policy_uri)
        print(f"Loaded Resource: {policy_uri}\n")

        logger.info("--- PHASE 3: Query Knowledge Base via Hybrid RAG + Self-RAG ---")
        rag_res = await agent.call_tool(
            "query_policy_knowledge_base",
            {"query": "What are the disconnect exemption rules for senior cardiac or life support patients?", "search_strategy": "hybrid"}
        )
        print(f"RAG Policy Lookup Result:\n{_text(rag_res)}\n")

        logger.info("--- PHASE 4: Role Elevation -> real notifications/tools/list_changed ---")
        elevate = await agent.call_tool(
            "elevate_user_session_role",
            {
                "username": "dispatcher_omar",
                "new_role": "DISPATCHER",
                "supervisor_passcode": "NCEDC-SECURE-2026",
            },
        )
        print(_text(elevate))
        print(f"Client mode after elevation: {agent.mode}\n")

        logger.info("--- PHASE 5: Audit Meter Status with Memory Layer Check ---")
        audit_res = await agent.call_tool("audit_meter_status", {"meter_id": "NC-MTR-30012"})
        print(_text(audit_res), "\n")

        logger.info("--- PHASE 6: Disconnection with Protected Note -> Real Sampling + Elicitation ---")
        print("(You will be prompted for a supervisor override code if triggered)\n")
        result = await agent.call_tool(
            "execute_meter_disconnection",
            {
                "meter_id": "NC-MTR-30012",
                "reason": "90+ days overdue, no prior protection flag on record",
                "requested_by": "inspector_ahmed",
                "inspector_note": "Customer objects, says there is an active oxygen concentrator and dialysis machine in the home",
            },
        )
        print(_text(result))

    print("\n==================================================")
    print("       PIPELINE EXECUTION COMPLETED SUCCESSFULLY  ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_ncedc_pipeline(use_http="--http" in sys.argv))
