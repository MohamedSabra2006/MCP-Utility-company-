"""
MCP Prompts Layer: Exposes parameterized prompt templates for client interaction
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NCEDC_Prompts")

PROMPTS_REGISTRY = {
    "audit_district_disconnections": {
        "name": "audit_district_disconnections",
        "description": "Generate a parameterized Law 87 disconnect compliance prompt for a specific Cairo district.",
        "arguments": [
            {
                "name": "district_name",
                "description": "The target district to audit (e.g., Heliopolis, Maadi, Nasr City)",
                "required": True
            },
            {
                "name": "include_medical_analysis",
                "description": "Whether to perform deep medical exemption validation using LLM sampling.",
                "required": False
            }
        ]
    }
}


class MCPPromptManager:
    def list_prompts(self):
        """MCP Protocol Point: prompts/list handler."""
        logger.info("Handling MCP request: prompts/list")
        prompt_list = []
        for name, p in PROMPTS_REGISTRY.items():
            prompt_list.append(p)
        return {"prompts": prompt_list}

    def get_prompt(self, name: str, arguments: dict = None):
        """MCP Protocol Point: prompts/get handler."""
        logger.info(f"Handling MCP request: prompts/get for prompt: '{name}' with args: {arguments}")
        if name not in PROMPTS_REGISTRY:
            raise KeyError(f"Prompt template '{name}' not found.")

        args = arguments or {}
        district = args.get("district_name", "All Districts")
        include_medical = args.get("include_medical_analysis", "true")

        prompt_text = (
            f"You are the Lead Compliance Agent for NCEDC operating under Law 87 rules.\n"
            f"Please execute a full batch audit on district: '{district}'.\n"
            f"Medical Exemption Deep Analysis Enabled: {include_medical}.\n"
            f"1. Query all unpaid balances and evaluate active medical exemptions vs. critical facility status.\n"
            f"2. Flag unprotected accounts for disconnection tickets.\n"
            f"3. Generate a structured audit report summarizing actions."
        )

        return {
            "description": PROMPTS_REGISTRY[name]["description"],
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt_text
                    }
                }
            ]
        }