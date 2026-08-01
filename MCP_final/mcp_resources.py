"""
MCP Resources Layer: Exposes static legal policy documents (EgyptERA Law 87)
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NCEDC_Resources")

EGYPTERA_LAW_87_POLICY = """
================================================================================
EGYPTERA REGULATORY CIRCULAR: EGYPT ELECTRICITY LAW NO. 87 COMPLIANCE DIRECTIVE
================================================================================
1. PROTECTION ELIGIBILITY:
   - Any customer account linked to active life-support medical equipment IS EXEMPT 
     from forced power disconnection regardless of outstanding bill amounts.
   - Public critical infrastructure (Hospitals, Water Pumping Stations, Emergency Services) 
     are strictly protected under National Infrastructure Safeguard Protocols.

2. DISCONNECTION RULES:
   - Disconnections can only be requested for accounts exceeding 30+ days overdue 
     without registered protection.
   - Disconnection of protected meters requires high-level human supervisor override 
     codes via MCP Elicitation protocol.
"""

RESOURCES_REGISTRY = {
    "law87://egypt-era/disconnection-policy": {
        "uri": "law87://egypt-era/disconnection-policy",
        "name": "EgyptERA Law 87 Disconnection Policy & Critical Exemptions",
        "description": "Official Egyptian Electric Utility & Consumer Protection Regulatory Agency rules on power disconnects.",
        "mimeType": "text/plain",
        "content": EGYPTERA_LAW_87_POLICY
    }
}


class MCPResourceManager:
    def list_resources(self):
        """MCP Protocol Point: resources/list handler."""
        logger.info("Handling MCP request: resources/list")
        resource_list = []
        for key, res in RESOURCES_REGISTRY.items():
            resource_list.append({
                "uri": res["uri"],
                "name": res["name"],
                "description": res["description"],
                "mimeType": res["mimeType"]
            })
        return {"resources": resource_list}

    def read_resource(self, uri: str):
        """MCP Protocol Point: resources/read handler."""
        logger.info(f"Handling MCP request: resources/read for URI: '{uri}'")
        if uri not in RESOURCES_REGISTRY:
            raise KeyError(f"Resource URI '{uri}' not found in registry.")
        
        target = RESOURCES_REGISTRY[uri]
        return {
            "contents": [
                {
                    "uri": target["uri"],
                    "mimeType": target["mimeType"],
                    "text": target["content"]
                }
            ]
        }