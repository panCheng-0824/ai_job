from app.skills.job_info.llm_jobs import dedupe_jobs, finalize_match_response, jobs_from_recom_list


def test_dedupe_jobs_by_id_keeps_higher_score():
    jobs = [
        {"job_id": "ABC-123", "job_title": "A", "score": 80},
        {"job_id": "abc-123", "job_title": "A", "score": 92, "match_reasons": ["更长理由"]},
    ]
    out = dedupe_jobs(jobs)
    assert len(out) == 1
    assert out[0]["score"] == 92


def test_jobs_from_recom_list_dedupes():
    recom = [
        {"jobId": "aaa", "jobName": "岗1", "score": 70},
        {"jobId": "AAA", "jobName": "岗1", "score": 90, "reason": "更好"},
    ]
    out = jobs_from_recom_list(recom)
    assert len(out) == 1
    assert out[0]["score"] == 90


def test_finalize_match_response_syncs_recommendation():
    data = {
        "jobs": [
            {"job_id": "x1", "job_title": "T1", "score": 90, "match_reasons": ["r1"]},
            {"job_id": "X1", "job_title": "T1", "score": 80, "match_reasons": ["r0"]},
        ],
        "recommendation": {
            "match_status": "matched",
            "recommended_jobs": [
                {"job_id": "x1", "job_title": "T1", "score": 90, "match_reason": "r1"},
                {"job_id": "X1", "job_title": "T1", "score": 80, "match_reason": "r0"},
            ],
        },
    }
    out = finalize_match_response(data)
    assert len(out["jobs"]) == 1
    assert len(out["recommendation"]["recommended_jobs"]) == 1
    assert out["jobs"][0]["score"] == 90
