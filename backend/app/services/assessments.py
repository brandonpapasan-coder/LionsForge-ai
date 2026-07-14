from typing import TypedDict


class AssessmentQuestion(TypedDict):
    id: str
    prompt: str
    options: list[str]
    correct_option: int
    objective: str


ASSESSMENT_BANK: dict[str, dict[str, AssessmentQuestion]] = {
    "financial-statements-foundations": {
        "foundation": {
            "id": "fs-foundation-1",
            "prompt": "Which statement reports cash generated and used during a period?",
            "options": ["Balance sheet", "Cash-flow statement", "Income statement"],
            "correct_option": 1,
            "objective": "Identify the primary purpose of the three core financial statements.",
        },
        "intermediate": {
            "id": "fs-intermediate-1",
            "prompt": "A company reports profit but declining operating cash flow. What should be investigated first?",
            "options": ["Working-capital changes", "Share price", "Dividend yield"],
            "correct_option": 0,
            "objective": "Connect reported earnings to operating cash conversion.",
        },
        "advanced": {
            "id": "fs-advanced-1",
            "prompt": "Which pattern most strongly suggests earnings quality risk?",
            "options": ["Stable margins and cash conversion", "Receivables growing faster than revenue", "Lower debt and higher cash"],
            "correct_option": 1,
            "objective": "Detect cross-statement indicators of weak earnings quality.",
        },
    },
    "valuation-and-cash-flow": {
        "foundation": {
            "id": "valuation-foundation-1",
            "prompt": "What does discounted cash-flow analysis estimate?",
            "options": ["Intrinsic value from future cash flows", "Historical book value only", "Daily trading volume"],
            "correct_option": 0,
            "objective": "Explain the purpose of discounted cash-flow valuation.",
        },
        "intermediate": {
            "id": "valuation-intermediate-1",
            "prompt": "Holding cash flows constant, what usually happens when the discount rate rises?",
            "options": ["Intrinsic value rises", "Intrinsic value falls", "Intrinsic value is unchanged"],
            "correct_option": 1,
            "objective": "Analyze sensitivity of intrinsic value to discount rates.",
        },
        "advanced": {
            "id": "valuation-advanced-1",
            "prompt": "Which assumption commonly dominates a mature-company DCF?",
            "options": ["Terminal growth and terminal value", "Yesterday's volume", "Current employee count"],
            "correct_option": 0,
            "objective": "Identify high-impact assumptions in long-duration valuation models.",
        },
    },
    "evidence-quality-and-bias": {
        "foundation": {
            "id": "evidence-foundation-1",
            "prompt": "Which source is usually closest to primary evidence?",
            "options": ["Original dataset", "Opinion summary", "Unsourced social post"],
            "correct_option": 0,
            "objective": "Distinguish primary evidence from commentary.",
        },
        "intermediate": {
            "id": "evidence-intermediate-1",
            "prompt": "What best reduces confirmation bias during research?",
            "options": ["Seek only supporting sources", "Predefine disconfirming evidence", "Ignore conflicting results"],
            "correct_option": 1,
            "objective": "Apply a falsification-oriented evidence review process.",
        },
        "advanced": {
            "id": "evidence-advanced-1",
            "prompt": "Two studies conflict. What is the strongest first comparison?",
            "options": ["Author popularity", "Methods, samples, and measurement", "Headline wording"],
            "correct_option": 1,
            "objective": "Resolve contradictions through methodological comparison.",
        },
    },
    "research-thesis-construction": {
        "foundation": {
            "id": "thesis-foundation-1",
            "prompt": "What makes a research thesis falsifiable?",
            "options": ["It can be tested against evidence", "It cannot be challenged", "It uses confident language"],
            "correct_option": 0,
            "objective": "Recognize a testable research claim.",
        },
        "intermediate": {
            "id": "thesis-intermediate-1",
            "prompt": "Which element most improves a thesis review?",
            "options": ["Explicit assumptions and failure conditions", "More adjectives", "Removing uncertainty"],
            "correct_option": 0,
            "objective": "Document assumptions and disconfirming conditions.",
        },
        "advanced": {
            "id": "thesis-advanced-1",
            "prompt": "What is the best response when evidence weakens a core assumption?",
            "options": ["Preserve the thesis unchanged", "Revise confidence or the thesis", "Discard the evidence"],
            "correct_option": 1,
            "objective": "Update a thesis rationally when core assumptions change.",
        },
    },
}
