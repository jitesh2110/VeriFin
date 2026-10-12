"""
VeriFin - One-Shot AI Invoice Analysis

This module performs ONE Gemini API call per invoice.

Flow:
    Invoice data + existing verification results
                ↓
        LangChain Prompt
                ↓
          Gemini 2.5 Flash
                ↓
        AI Analysis Result

No ReAct agent.
No tools.
No multiple iterations.
No repeated Gemini calls.
"""

import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found in environment variables!"
    )


# ============================================================
# INITIALIZE GEMINI
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=api_key,
    convert_system_message_to_human=True,
    max_retries=0
)


# ============================================================
# AI ANALYSIS PROMPT
# ============================================================

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert invoice auditor for VeriFin.

Analyze the invoice information and the verification results provided
to you.

Your job is NOT to perform additional API calls, database queries,
or calculations.

All checks have already been performed by the VeriFin system.

You only need to intelligently interpret the available information
and provide a clear final risk assessment.

Identify:
1. Possible fraud or anomalies
2. GST issues
3. HSN/SAC issues
4. Duplicate invoice concerns
5. Unusual amount concerns
6. Vendor/GST mismatches
7. Overall compliance concerns

Give the final assessment using:

- Risk Level: LOW / MEDIUM / HIGH
- Overall Status
- Key Findings
- Recommended Action

Be concise and practical.

Do not invent information that is not present in the input.
If a check was not performed or the information is unavailable,
say "Not available".

Do not claim that you performed an external verification.
"""
    ),
    (
        "human",
        """
Analyze this invoice:

Invoice Number:
{invoice_number}

Vendor Name:
{vendor_name}

Invoice Date:
{invoice_date}

Total Amount:
₹{total_amount}

GST Numbers:
{gst_numbers}

GST Verification Results:
{gst_verification}

HSN/SAC Verification Results:
{hsn_verification}

ML Anomaly Detection:
{ml_analysis}

Database / Duplicate Anomaly Results:
{database_anomalies}

Compliance Results:
{compliance_results}

Line Items:
{line_items}

Provide the final AI invoice analysis.
"""
    )
])


# ============================================================
# CREATE ONE-SHOT LANGCHAIN CHAIN
# ============================================================

chain = prompt | llm


# ============================================================
# MAIN AI ANALYSIS FUNCTION
# ============================================================

def analyze_invoice_with_agent(invoice_data: dict) -> dict:
    """
    Perform ONE Gemini API call to analyze an invoice.

    IMPORTANT:
    This function does NOT:
        - call databases
        - call GST APIs
        - call HSN APIs
        - call ML models
        - use tools
        - run an agent
        - perform multiple iterations

    It simply sends the already-processed invoice information
    to Gemini once and returns the AI analysis.
    """

    try:

        # ----------------------------------------------------
        # Prepare invoice information
        # ----------------------------------------------------

        invoice_number = invoice_data.get(
            "invoice_number",
            "Unknown"
        )

        vendor_name = invoice_data.get(
            "vendor_name",
            "Unknown"
        )

        invoice_date = invoice_data.get(
            "invoice_date",
            "Unknown"
        )

        total_amount = invoice_data.get(
            "total_amount",
            0
        )

        gst_numbers = invoice_data.get(
            "gst_numbers",
            []
        )

        gst_verification = invoice_data.get(
            "gst_verification",
            "Not available"
        )

        hsn_verification = invoice_data.get(
            "hsn_verification",
            "Not available"
        )

        ml_analysis = invoice_data.get(
            "ml_analysis",
            "Not available"
        )

        database_anomalies = invoice_data.get(
            "database_anomalies",
            "Not available"
        )

        compliance_results = invoice_data.get(
            "compliance_results",
            "Not available"
        )

        line_items = invoice_data.get(
            "line_items",
            []
        )


        # ----------------------------------------------------
        # Convert complex data safely to strings
        # ----------------------------------------------------

        gst_numbers_text = str(gst_numbers)

        gst_verification_text = str(
            gst_verification
        )

        hsn_verification_text = str(
            hsn_verification
        )

        ml_analysis_text = str(
            ml_analysis
        )

        database_anomalies_text = str(
            database_anomalies
        )

        compliance_results_text = str(
            compliance_results
        )

        line_items_text = str(
            line_items
        )


        # ----------------------------------------------------
        # ONE GEMINI CALL
        # ----------------------------------------------------

        print("🤖 Sending invoice to Gemini AI...")
        print("⚡ One-shot AI analysis - 1 Gemini call only")

        response = chain.invoke({
            "invoice_number": invoice_number,
            "vendor_name": vendor_name,
            "invoice_date": invoice_date,
            "total_amount": f"{total_amount:,.2f}",
            "gst_numbers": gst_numbers_text,
            "gst_verification": gst_verification_text,
            "hsn_verification": hsn_verification_text,
            "ml_analysis": ml_analysis_text,
            "database_anomalies": database_anomalies_text,
            "compliance_results": compliance_results_text,
            "line_items": line_items_text
        })


        # ----------------------------------------------------
        # Extract Gemini response
        # ----------------------------------------------------

        analysis = response.content

        print("✅ AI Analysis Complete")
        print("⚡ Gemini calls used: 1")


        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return {
            "success": True,
            "analysis": analysis,
            "agent_used": True,
            "ai_used": True
        }


    except Exception as e:

        print(f"❌ AI Analysis Error: {str(e)}")

        return {
            "success": False,
            "error": str(e),
            "agent_used": False,
            "ai_used": False
        }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_invoice = {
        "invoice_number": "INV-2024-001",
        "vendor_name": "Test Vendor",
        "total_amount": 50000,
        "gst_numbers": [
            "24AAACC1206D1ZM"
        ],
        "invoice_date": "2024-11-08",

        "gst_verification": {
            "status": "Active",
            "valid": True
        },

        "hsn_verification": {
            "code": "71141110",
            "valid": False
        },

        "ml_analysis": {
            "is_anomaly": True,
            "score": -0.0127
        },

        "database_anomalies": [],

        "compliance_results": {
            "gst_compliant": True,
            "hsn_compliant": False
        },

        "line_items": [
            {
                "description": "Silver Item",
                "quantity": 10,
                "amount": 50000
            }
        ]
    }


    print()
    print("=" * 60)
    print("🤖 VeriFin One-Shot AI Analysis")
    print("=" * 60)

    result = analyze_invoice_with_agent(test_invoice)

    print()

    if result["success"]:
        print(result["analysis"])
    else:
        print(f"❌ Error: {result['error']}")