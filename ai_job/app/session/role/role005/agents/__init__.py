"""
ROLE005 LLM Agent 封装。

各 Agent 职责分离：Planner / Interviewer / Evaluator / Scorer / Clarifier。
Interviewer **禁止**访问 reference_answer（见 infra.schema_gate）。
"""
