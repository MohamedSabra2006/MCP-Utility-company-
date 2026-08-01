"""
Main System Pipeline: Demonstrates all 8 MCP Protocol Concerns working in sync
"""
import asyncio
import logging
from agent_client import NCEDCClientAgent
from MCP_final.mcp_tools1 import batch_audit_delinquent_accounts, resource_manager, prompt_manager
from sampling_handler import SamplingHandler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("NCEDC_Pipeline")


async def run_ncedc_pipeline():
    print("==================================================")
    print("   NCEDC MCP SYSTEM - END-TO-END PIPELINE DEMO   ")
    print("==================================================\n")

    # 1. Initialize Sampling Handler & Client
    sampling_handler = SamplingHandler()

    logger.info("--- PHASE 1: HTTP Transport & Capability Negotiation ---")
    client = NCEDCClientAgent(
        endpoint_url="https://substation-cairo.ncedc.gov.eg/mcp",
        auth_token="ncedc-secret-api-key-2026"
    )
    client.connect_http()
    print()

    logger.info("--- PHASE 2: Fetch Legal Policy Resource (resources/read) ---")
    policy = resource_manager.read_resource("law87://egypt-era/disconnection-policy")
    print(f"Loaded Resource Policy Title: {policy['contents'][0]['uri']}\n")

    logger.info("--- PHASE 3: Render Compliance Prompt Template (prompts/get) ---")
    rendered_prompt = prompt_manager.get_prompt(
        "audit_district_disconnections", 
        {"district_name": "Heliopolis", "include_medical_analysis": "true"}
    )
    print(f"Generated Audit Prompt:\n{rendered_prompt['messages'][0]['content']['text']}\n")

    logger.info("--- PHASE 4: Batch Audit with Progress Notifications ---")
    audit_results = await batch_audit_delinquent_accounts(
        district_name="Heliopolis",
        progress_token="heliopolis-batch-901"
    )
    print(f"\nAudit Summary: Total Audited = {audit_results.get('total_audited', 0)}\n")

    logger.info("--- PHASE 5: Model-in-the-Loop Sampling Evaluation ---")
    flagged_account = {
        "account_id": "ACC-CAIRO-99201",
        "meter_id": "NC-MTR-30012",
        "medical_attachment": "Medical Certificate: Patient uses active continuous Oxygen Concentrator."
    }

    sampling_request = {
        "prompt": "Evaluate if account has active life-support protection.",
        "document_text": flagged_account["medical_attachment"]
    }
    
    evaluation = sampling_handler.handle_sampling_request(sampling_request)
    decision_data = evaluation["content"]

    print("\n--- FINAL DISCONNECTION DECISION ---")
    if decision_data["has_active_life_support"]:
        logger.info(f"🛑 METER DISCONNECTION ABORTED for {flagged_account['meter_id']}")
        logger.info(f"Reason: {decision_data['reasoning']} Status: {decision_data['decision']}")
    else:
        logger.info(f"⚡ PROCEEDING WITH DISCONNECTION for {flagged_account['meter_id']}")
        client.execute_disconnection(flagged_account["meter_id"])

    print("\n==================================================")
    print("       PIPELINE EXECUTION COMPLETED SUCCESSFULLY  ")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_ncedc_pipeline())
