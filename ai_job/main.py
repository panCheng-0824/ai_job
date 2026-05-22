"""
最小入口：从 ``usermodel.json`` 的**用户数组**里选用户，再驱动 ``run_user_query``。

生产场景通常会用 CLI/Web 传入 ``username`` / ``usercode``；本脚本直接打印主答与管道侧输出，
更完整的分步演示见 ``demo.py``。
"""

from user_session import run_user_query


if __name__ == "__main__":
    # 未指定时取数组首条；按人切分可传 usercode= 或 username=
    # 默认开启四段管道；不需要管道时设 use_role_pipeline=False
    result = run_user_query(verbose=True)
    print(result.get("output", result))
    if "adversarial_review" in result:
        print("\n--- 对抗审查（红队）---\n")
        print(result["adversarial_review"])
    if "profile_enrichment" in result:
        print("\n--- 用户画像补充建议 ---\n")
        print(result["profile_enrichment"])
    if "pipeline" in result:
        print("\n--- 管道元信息 ---\n", result["pipeline"])
