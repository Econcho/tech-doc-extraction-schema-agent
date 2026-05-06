"""Default constants for the KEP domain plugin."""

DEFAULT_THRESHOLDS = {
    "text_relaxed_f1": 0.8,
    "substring_precision": 0.8,
    "substring_recall": 0.8,
    "lccs_ratio": 0.7,
}

ALLOWED_CLASSES = (
    "summary",
    "motivation",
    "goal",
    "non_goal",
    "design_decision",
    "user_story",
    "definition",
    "future_work",
    "risk",
    "mitigation",
    "test_case",
    "graduation_criterion",
    "drawback",
    "alternative",
    "implementation_history",
)

ALLOWED_ATTRIBUTE_KEYS = (
    "category",
    "definition_type",
    "horizon",
    "test_type",
    "stage",
    "marker",
    "marker_type",
)

CLASS_ATTRIBUTE_SCHEMA = {
    "summary": {"required": (), "optional": ()},
    "motivation": {"required": (), "optional": ()},
    "goal": {"required": (), "optional": ()},
    "non_goal": {"required": (), "optional": ()},
    "design_decision": {"required": ("category",), "optional": ()},
    "user_story": {"required": (), "optional": ()},
    "definition": {"required": ("definition_type",), "optional": ()},
    "future_work": {"required": ("horizon",), "optional": ()},
    "risk": {"required": (), "optional": ()},
    "mitigation": {"required": (), "optional": ()},
    "test_case": {"required": ("test_type",), "optional": ()},
    "graduation_criterion": {"required": ("stage",), "optional": ()},
    "drawback": {"required": (), "optional": ()},
    "alternative": {"required": (), "optional": ()},
    "implementation_history": {"required": ("marker", "marker_type"), "optional": ()},
}

ATTRIBUTE_VALUE_SCHEMA = {
    "summary": {},
    "motivation": {},
    "goal": {},
    "non_goal": {},
    "design_decision": {
        "category": (
            "proposal_definition",
            "workflow",
            "api_change",
            "component_change",
            "compatibility",
            "rollout",
            "upgrade_strategy",
            "version_skew_strategy",
            "dependency",
            "monitoring",
            "scalability",
            "troubleshooting",
            "implementation_detail",
            "other",
        ),
    },
    "user_story": {},
    "definition": {
        "definition_type": ("term", "role", "artifact", "other"),
    },
    "future_work": {
        "horizon": ("post_ga", "future_extension", "backlog", "other"),
    },
    "risk": {},
    "mitigation": {},
    "test_case": {
        "test_type": (
            "prerequisite_update",
            "unit_test",
            "integration_test",
            "e2e_test",
            "conformance_test",
            "manual_validation",
            "benchmark_or_scale",
            "other",
        ),
    },
    "graduation_criterion": {
        "stage": ("alpha", "beta", "ga", "stable", "other"),
    },
    "drawback": {},
    "alternative": {},
    "implementation_history": {
        "marker": None,
        "marker_type": ("release", "date", "stage", "other"),
    },
}
