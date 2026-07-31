# MCP-Utility-company-
# NCEDC Model Context Protocol (MCP) Safety Server
> **North Cairo Electricity Distribution Company (NCEDC)** — Safe, Policy-Compliant LLM-Driven Service Disconnection & Account Management Gateway.

---

## 🏢 Company & Operational Context

The **North Cairo Electricity Distribution Company (NCEDC)** manages power distribution for millions of residential, commercial, and industrial customers across Greater Cairo. As part of revenue protection operations, NCEDC tracks overdue accounts (90+ days delinquent) and dispatches field inspectors to execute physical **Meter Disconnections**.

### ⚖️ Regulatory Framework & Legal Protections
Under the **Egyptian Electricity Regulatory Agency (EgyptERA)** regulations and **Egyptian Electricity Law No. 87 of 2015**, specific accounts are designated as **Protected Customers** and are **legally exempt from disconnection**, regardless of debt duration or amount:
1. **Residential Medical Exemptions (`MEDICAL_CRITICAL`):** Apartments/homes housing patients dependent on home life-support equipment or home hemodialysis machines with certified Ministry of Health documentation.
2. **Critical Infrastructure (`INFRASTRUCTURE_CRITICAL`):** Public hospitals, municipal water pumping stations, emergency response centers, and sewage infrastructure.

---

## 🚨 The Danger: Naïve LLM Disconnection

If an LLM or autonomous AI agent is given direct SQL read/write access to NCEDC's billing database with the command:  
> *"Disconnect all accounts with outstanding debts older than 90 days."*

The LLM will query the billing table, identify all overdue accounts, and execute `DISCONNECT` operations unconditionally.

**The Catastrophic Result:** Power is terminated to a home dialysis unit or a city water station simply because the account was overdue by 3 months.

---

## 🛡️ The Solution: MCP Defensive Safety Gateway

Our solution places a **Model Context Protocol (MCP) Server** as a protective middleware layer between the AI Agent and the NCEDC production database. 

The LLM never has raw database access. Every state-changing action (such as meter disconnection) is gated by:
* **Rule-based Defensive Tool Schemas & Input Constraints**
* **Legal Exemption Automated Intercepts**
* **Human-in-the-Loop (HITL) Elicitation Workflows**
* **Runtime Capability Negotiation & Dynamic Authorization**

---

## 🏗️ Repository Structure

```text
your-repo/
├── README.md
├── .gitignore
├── .env                       # Environment variables (DB credentials, API keys)
│
├── db/                        # Database schemas and seed data
│   ├── schema.sql             # DB Schema definitions
│   ├── seed_data.sql          # Test accounts & mock utility data
│   └── erd.png                # Entity Relationship Diagram
│
├── mcp_server/                # Core MCP Server & Defensive Middleware
│   ├── tools.py               # Single-purpose MCP database execution tools
│   ├── defensive_schemas.py   # Strict Pydantic/JSON schemas (additionalProperties: false)
│   ├── security.py            # Policy Interceptor (Law 87/2015 validation layer)
│   ├── resources.py           # Read-only utility data endpoints
│   ├── prompts.py             # System prompt definitions & guardrails
│   └── sampling.py          # LLM sampling & elicitation handlers
│
└── agent/                     # Client execution & orchestration pipeline
    ├── agent_client.py        # MCP client connection handler
    └── main_pipeline.py       # End-to-end execution entry point
    
🌐 MCP Protocol Concerns & Implementation Mapping
This project implements all 8 mandatory MCP protocol concerns as required by the specification:
1. Capability Negotiation:During handshakes, the client verifies if the server supports required capabilities (e.g., elicitation, sampling) before invoking risky write operations located agent_client.py
2.Dynamic Notifications:When an inspector authenticates or changes roles, the tool set updates dynamically via tools/list_changed without dropping connection located in agent_client.py and security1.py
Human in the loop elicitation:If a disconnection target is flagged with a pending exemption review or high risk, elicitation/create pauses the tool call to require explicit human sign-off mcp_tools1.py
4.Sampling:Server delegates complex rationale checks or medical report summaries back to the client's LLM safely through the client proxy located in sampling handler.py
5.Resources:Exposes static policy documents (e.g., EgyptERA Law 87/2015 guidelines) as read-only context rather than tool wrappers located in mcp_resources.py
6.Prompts:Provides parameterized prompt templates (e.g., standard disconnection warning notice) for consistent agent usage located in mcp_prompts.py
Transport Evaluation:Designed to operate over stdio during local development and seamlessly transition to Streamable HTTP for enterprise multi-branch deployment located in agent_client.py
Progress Tracking:Long-running batch audit lookups and report generations send intermediate progress updates to keep the client informed located in mcp_tools1.py
TOOLS:
1.get_account_status:Queries debt history and protection status without modifying system state.No elicitation required (READ ONLY)
2.read_egyptera_policy:Fetches static legal guidelines under Law 87/2015.(READ ONLY)
3.request_meter_disconnection:Blocked instantly if status is PROTECTED. Triggers Elicitation if status is FLAGGED_PENDING_REVIEW.(CONDITIONAL)
4.override_protection_status:Changing a protected account requires higher-level human manager sign-off.(REQUIRES ELICITATION)

💻 How to Run the Project:
1. Prerequisites
Python 3.10+
Installed dependencies:
pip install mcp pydantic langchain-mcp-adapters
2. Environment Setup:
Create a .env file in the root folder
NCEDC_ENV=development
LOG_LEVEL=INFO
3. Run the Full End-to-End Pipeline Demo
Execute the main pipeline to see capability negotiation, policy resource reading, defensive intercepts, and elicitation in action:
python MCP_final/main_pipeline.py