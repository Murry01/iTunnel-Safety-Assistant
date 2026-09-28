# -*- coding: utf-8 -*-
"""tools/display_chart.py — render a chart in the Streamlit UI.

The tool itself only validates and acknowledges; the orchestrator intercepts
the call and forwards the spec to the UI as a ("chart", spec) event.
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "display_chart",
        "description": (
            "Display a chart to the user in the app. Use whenever the user asks "
            "for a chart/graph/plot/visualization (차트, 그래프, 히스토그램, 시각화) "
            "of data you have from other tools. Call the data tools FIRST, then "
            "this with the numbers. Korean labels are fully supported."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie"],
                    "description": "bar for category counts (use for 히스토그램 of categories)",
                },
                "title": {"type": "string"},
                "labels": {
                    "type": "array", "items": {"type": "string"},
                    "description": "category names / x values",
                },
                "values": {
                    "type": "array", "items": {"type": "number"},
                    "description": "numeric values, same length as labels",
                },
                "y_label": {"type": "string", "description": "axis label, e.g. 사고 건수"},
            },
            "required": ["chart_type", "labels", "values"],
        },
    },
}


def run(chart_type: str, labels: list, values: list, title: str = "",
        y_label: str = "") -> list[dict]:
    if len(labels) != len(values):
        return [{"error": "labels and values must have the same length"}]
    if not labels:
        return [{"error": "empty data"}]
    return [{
        "result": f"{chart_type} chart '{title}' with {len(labels)} categories "
                  "has been displayed to the user. Refer to it briefly; do not "
                  "repeat all the numbers in a table."
    }]
