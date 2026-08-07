"""
NCEDC Domain-Specific RAG Evaluation Test Suite
Contains 12 benchmark questions across 3 query categories.
"""

TEST_QUESTIONS = [
    # --- Category A: General Policy Questions (Naive RAG works well) ---
    {
        "id": "Q1",
        "category": "General Policy",
        "question": "What is the general grace period before an unpaid electricity bill triggers a disconnection notice under NCEDC rules?",
        "expected_keywords": ["30 days", "overdue", "notice"]
    },
    {
        "id": "Q2",
        "category": "General Policy",
        "question": "Are public hospitals subject to immediate power shut-offs for non-payment?",
        "expected_keywords": ["protected", "critical facility", "exempt"]
    },
    {
        "id": "Q3",
        "category": "General Policy",
        "question": "What documentation must a customer present to request a medical exemption?",
        "expected_keywords": ["medical certificate", "life-support", "health authority"]
    },
    {
        "id": "Q4",
        "category": "General Policy",
        "question": "Who can authorize a supervisor override code during a protected meter disconnection attempt?",
        "expected_keywords": ["district supervisor", "dispatcher", "override"]
    },

    # --- Category B: Exact Identifiers & Citations (Hybrid Search wins) ---
    {
        "id": "Q5",
        "category": "Exact Citation",
        "question": "What exact exemption protection rule is defined in Circular Law 87 Clause 1.2?",
        "expected_keywords": ["Law 87", "Clause 1.2", "life-support equipment"]
    },
    {
        "id": "Q6",
        "category": "Exact Citation",
        "question": "What is the penalty code for meter tampering specified in NCEDC Directive 2026-SEC?",
        "expected_keywords": ["2026-SEC", "penalty", "tampering"]
    },
    {
        "id": "Q7",
        "category": "Exact Citation",
        "question": "What specific rule applies to meter ID pattern NC-MTR-30012 regarding dialysis protection?",
        "expected_keywords": ["NC-MTR-30012", "dialysis", "protected"]
    },
    {
        "id": "Q8",
        "category": "Exact Citation",
        "question": "Under EgyptERA Directive Article 4.2b, what happens to water pumping station meters during grid audits?",
        "expected_keywords": ["Article 4.2b", "water pumping", "safeguard"]
    },

    # --- Category C: Multi-Hop / Complex Case Analysis (Agentic RAG wins) ---
    {
        "id": "Q9",
        "category": "Complex Multi-Hop",
        "question": "For a residential customer owing 12,000 EGP who claims a family member uses a ventilator, what sequence of audit checks and supervisor steps must be executed?",
        "expected_keywords": ["verify medical", "sampling", "elicitation", "supervisor override"]
    },
    {
        "id": "Q10",
        "category": "Complex Multi-Hop",
        "question": "If a field inspector submits an Arabic note stating 'مريض غسيل كلي', how does the agent handle both the database flag and the disconnection ticket?",
        "expected_keywords": ["sampling", "dialysis", "abort disconnection", "log ticket"]
    },
    {
        "id": "Q11",
        "category": "Complex Multi-Hop",
        "question": "What conflict resolution policy applies if a database record shows 'Unprotected' but an inspector note from 2 days ago confirms an oxygen concentrator?",
        "expected_keywords": ["consolidation", "update semantic memory", "versioning", "protect"]
    },
    {
        "id": "Q12",
        "category": "Complex Multi-Hop",
        "question": "Compare the disconnection workflow for an unpaid commercial warehouse vs. an unpaid critical medical facility.",
        "expected_keywords": ["warehouse disconnects", "facility protected", "elicitation trigger"]
    }
]