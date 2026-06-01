"""ROLE005 产物契约单元测试。"""

from app.session.role.role005.domain.models import InterviewPlan, QuestionItem
from app.session.role.role005.infra.schema_gate import (
    strip_reference_from_interviewer_context,
    validate_interview_plan,
)


def test_validate_plan_ok():
    plan = InterviewPlan(
        plan_id="plan_test",
        version=1,
        target_role="后端开发",
        questions=[
            QuestionItem(
                id="q1",
                text="介绍一个项目",
                dimensions=["技术"],
                reference_answer="内部",
            )
        ],
    )
    out, err = validate_interview_plan(plan.model_dump())
    assert err == ""
    assert out is not None
    assert len(out.questions) == 1


def test_validate_plan_empty_questions():
    plan = InterviewPlan(plan_id="p", version=1, questions=[])
    out, err = validate_interview_plan(plan.model_dump())
    assert out is None
    assert "至少需要" in err


def test_strip_reference():
    plan = InterviewPlan(
        plan_id="p",
        version=1,
        questions=[
            QuestionItem(
                id="q1",
                text="题",
                reference_answer="secret",
                eval_criteria={"a": 1},
            )
        ],
    )
    safe = strip_reference_from_interviewer_context(plan)
    assert "secret" not in str(safe)
    assert safe["questions"][0].get("reference_answer") is None
