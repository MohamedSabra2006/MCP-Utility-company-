"""
Defensive JSON Schemas for North Cairo Electricity Distribution Company (NCEDC)
Enforces: strict types, regex patterns, required fields, and additionalProperties=False
"""
from jsonschema import Draft202012Validator

# Regex format for Egyptian Meter IDs: NC-MTR-XXXXX (e.g., NC-MTR-10042)
METER_ID_REGEX = r"^NC-MTR-[0-9]{5}$"

# 1. Schema for Disconnection Execution
EXECUTE_DISCONNECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "meter_id": {
            "type": "string",
            "pattern": METER_ID_REGEX,
            "description": "Unique NCEDC smart meter identifier in format NC-MTR-XXXXX"
        },
        "reason": {
            "type": "string",
            "minLength": 10,
            "maxLength": 250,
            "description": "Official justification for executing service cutoff"
        },
        "requested_by": {
            "type": "string",
            "minLength": 3,
            "description": "Username of the field inspector or operator requesting disconnection"
        }
    },
    "required": ["meter_id", "reason", "requested_by"],
    "additionalProperties": False  # Prevent LLM key hallucination
}

# 2. Schema for Auditing Overdue Bills
AUDIT_METER_SCHEMA = {
    "type": "object",
    "properties": {
        "meter_id": {
            "type": "string",
            "pattern": METER_ID_REGEX,
            "description": "Target meter ID to query"
        }
    },
    "required": ["meter_id"],
    "additionalProperties": False
}

# Pre-compile JSON Schema validators
disconnection_validator = Draft202012Validator(EXECUTE_DISCONNECTION_SCHEMA)
audit_validator = Draft202012Validator(AUDIT_METER_SCHEMA)


def validate_defensive_input(payload: dict, schema_type: str) -> tuple[bool, str]:
    """
    Independent Server-Side Schema Validation Handler
    Returns (is_valid, error_message)
    """
    validator = disconnection_validator if schema_type == "disconnection" else audit_validator
    
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        error_details = "; ".join([f"Field '{e.json_path}': {e.message}" for e in errors])
        return False, f"Defensive Schema Check Failed: {error_details}"
    
    return True, ""