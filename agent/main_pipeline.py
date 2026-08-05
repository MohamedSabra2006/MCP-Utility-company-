"""
NCEDC MCP Pipeline: end-to-end demo driven by a REAL `mcp.ClientSession`
talking to the REAL `mcp_tool2.py` FastMCP server — not a simulation.

This replaces the earlier version of this file, which imported
`MCP_final.mcp_tools1` and `sampling_handler.SamplingHandler` (neither of
which exist in this project) and drove everything through
`agent_client.NCEDCClientAgent`'s old hardcoded/simulated responses. Every
phase below is now a real MCP protocol call: `resources/read`,
`prompts/get`, `tools/call`, with sampling and elicitation genuinely
round-tripping to the client's own callbacks in `agent_client.py`.

Run:
    python main_pipeline.py            # stdio transport (spawns the server)
    python main_pipeline.py --http     # Streamable HTTP transport
                                        # (start `python mcp_tool2.py` first)
"""
import asyncio
import logging
import sys

from agent_client import NCEDCClientAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("NCEDC_Pipeline")


def _text(call_tool_result) -> str:
    """`CallToolResult.content` is a list of content blocks; join their text."""
    return "\n".join(getattr(block, "text", str(block)) for block in call_tool_result.content)


async def run_ncedc_pipeline(use_http: bool = False):
    print("==================================================")
    print("   NCEDC MCP SYSTEM - END-TO-END PIPELINE DEMO   ")
    print("==================================================\n")

    agent = NCEDCClientAgent()
    connect_cm = agent.connect_http() if use_http else agent.connect_stdio()

    async with connect_cm:
        logger.info("--- PHASE 1: Real initialize/initialized handshake (see agent_client._initialize) ---")
        print(f"Declared server capabilities: {agent.server_capabilities}")
        print(f"Client mode after handshake:  {agent.mode}\n")

        logger.info("--- PHASE 2: Fetch Legal Policy Resource (resources/read) ---")
        resources = await agent.session.list_resources()
        policy_uri = next(r.uri for r in resources.resources if "disconnection-policy" in str(r.uri))
        policy = await agent.session.read_resource(policy_uri)
        print(f"Loaded Resource: {policy_uri}\n")

        logger.info("--- PHASE 3: Render Compliance Prompt Template (prompts/get) ---")
        rendered = await agent.session.get_prompt(
            "audit_district_disconnections",
            {"district_name": "Heliopolis", "include_medical_analysis": "true"},
        )
        print(f"Generated Audit Prompt:\n{rendered.messages[0].content.text}\n")

        logger.info("--- PHASE 4: Auditor session tries the write tool (expected: blocked) ---")
        blocked = await agent.call_tool(
            "execute_meter_disconnection",
            {
                "meter_id": "NC-MTR-20045",
                "reason": "Overdue balance clearance",
                "requested_by": "inspector_ahmed",
            },
        )
        print(_text(blocked), "\n")

        logger.info("--- PHASE 5: Role elevation -> real notifications/tools/list_changed ---")
        elevate = await agent.call_tool(
            "elevate_user_session_role",
            {
                "username": "dispatcher_omar",
                "new_role": "DISPATCHER",
                # Demo-only default; override via NCEDC_SUPERVISOR_PASSCODE
                # in mcp_tool2.py's environment for anything beyond a local demo.
                "supervisor_passcode": "NCEDC-SECURE-2026",
            },
        )
        print(_text(elevate))
        print(f"Client mode after elevation: {agent.mode}\n")

        logger.info("--- PHASE 6: Batch audit with real progress notifications ---")
        batch = await agent.call_tool(
            "batch_audit_delinquent_accounts",
            {"district_name": "Heliopolis", "progress_token": "heliopolis-batch-901"},
        )
        print(_text(batch), "\n")

        logger.info("--- PHASE 7: Disconnection with a protected note -> real sampling + real elicitation ---")
        print("(You'll be prompted for a supervisor override code below — this is a real")
        print(" elicitation/create pause, answered by agent_client._handle_elicitation_request)\n")
        result = await agent.call_tool(
            "execute_meter_disconnection",
            {
                "meter_id": "NC-MTR-30012",
                "reason": "90+ days overdue, no prior protection flag on record",
                "requested_by": "inspector_ahmed",
                "inspector_note": "Customer objects, says there is a dialysis patient in the apartment",
            },
        )
        print(_text(result))

    print("\n==================================================")
    print("       PIPELINE EXECUTION COMPLETED SUCCESSFULLY  ")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_ncedc_pipeline(use_http="--http" in sys.argv))
