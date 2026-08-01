"""
NCEDC Client Agent: Handles Capability Negotiation, HTTP Transport, and Sampling
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NCEDC_Client")


class NCEDCClientAgent:
    def __init__(self, endpoint_url: str = None, auth_token: str = None, server_capabilities: dict = None):
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        self.server_capabilities = server_capabilities or {}
        self.can_execute_disconnections = False
        self.mode = "disconnected"

    def connect_http(self):
        """Streamable HTTP Transport with Auth."""
        logger.info(f"Connecting to NCEDC Server over Streamable HTTP at {self.endpoint_url}...")
        
        if not self.auth_token or self.auth_token != "ncedc-secret-api-key-2026":
            logger.error("❌ HTTP 401: Unauthorized access to sub-station endpoint!")
            raise ConnectionError("Authentication failed: Invalid Bearer Token")

        # Simulated POST /initialize endpoint response
        simulated_http_response = {
            "capabilities": {
                "tools": True,
                "elicitation": True,
                "sampling": True,
                "progress_notifications": True,
                "resources": True,
                "prompts": True
            }
        }

        logger.info("✅ Connection established over Streamable HTTP (200 OK).")
        self.server_capabilities = simulated_http_response["capabilities"]
        self.negotiate_capabilities()

    def negotiate_capabilities(self):
        """Reviews initialization payload and assigns operational client modes."""
        logger.info("--- Reviewing Server Capabilities ---")
        logger.info(f"Declared Capabilities: {self.server_capabilities}")

        has_elicitation = self.server_capabilities.get("elicitation", False)

        if has_elicitation:
            self.can_execute_disconnections = True
            self.mode = "interactive-write"
            logger.info("✅ Elicitation supported. Interactive write enabled (Meter Disconnection allowed).")
        else:
            self.can_execute_disconnections = False
            self.mode = "degraded-safe"
            logger.warning("⚠️ CRITICAL: Elicitation capabilities NOT supported by server!")
            logger.warning("🔒 Fallback triggered: Client degrading safely to READ-ONLY mode.")

    def request_medical_sampling(self, meter_id: str, medical_condition: str):
        """MCP Protocol Point: sampling/createMessage for medical document AI checks."""
        if not self.server_capabilities.get("sampling", False):
            logger.warning(f"⚠️ Server does not support sampling capability. Skipping document check for {meter_id}.")
            return None

        logger.info(f"Sending sampling/createMessage request to analyze medical proof for Meter: {meter_id}...")
        
        simulated_sampling_response = {
            "role": "assistant",
            "content": {
                "type": "text",
                "text": f"VALIDATED: Condition '{medical_condition}' requires continuous power under Law 87. Exemption APPROVED."
            },
            "model": "ncedc-medical-eval-v1",
            "stopReason": "endTurn"
        }

        logger.info(f"✅ Sampling Response Received from LLM Model '{simulated_sampling_response['model']}':")
        logger.info(f"   Evaluation Result: {simulated_sampling_response['content']['text']}")
        return simulated_sampling_response

    def execute_disconnection(self, meter_id: str):
        if not self.can_execute_disconnections:
            raise RuntimeError(
                f"Cannot execute disconnection for {meter_id}. "
                f"Client is running in '{self.mode}' mode because elicitation is missing."
            )
        logger.info(f"Proceeding with meter disconnection flow for: {meter_id}")
