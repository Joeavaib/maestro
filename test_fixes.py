from maestro.orch.plan_filters import (
    clean_diff_output, 
    filter_raven_plan, 
    merge_similar_tasks, 
    contains_diff, 
    compact_no_patch_error
)
from maestro.orch.forest_types import ForestPlan, TreeTask

def test_clean_diff():
    raw = """
    Here is the fix:
    ```diff
    --- a/file.py
    +++ b/file.py
    @@ -1,1 +1,1 @@
    -old
    +new
    ```
    I hope this helps.
    """
    cleaned = clean_diff_output(raw)
    print(f"Cleaned Diff:\n{cleaned}")
    assert cleaned.startswith("--- a/")
    assert "+new" in cleaned

def test_filtering():
    tasks = [
        TreeTask(id="t1", task="Identify the class", intent="Understand class", files="a.py", symbols="A"), # Should be filtered
        TreeTask(id="t2", task="Locate methods", intent="Identify where to place it", files="b.py", symbols="B"), # Should be filtered
        TreeTask(id="t3", task="Integrate RunArchive", intent="Integrate", files="luna.py", symbols="Luna"), # Keep
        TreeTask(id="t4", task="Test the integration", intent="Ensure it works", files="test.py", symbols="Test"), # Should be filtered
        TreeTask(id="t5", task="Create a new test", intent="Write test", files="test.py", symbols="Test"), # Keep (Actionable test)
    ]
    plan = ForestPlan(goal="Test", tasks=tasks)
    filtered = filter_raven_plan(plan)
    print(f"Filtered tasks: {[t.id for t in filtered.tasks]}")
    assert len(filtered.tasks) == 2
    assert "t3" in [t.id for t in filtered.tasks]
    assert "t5" in [t.id for t in filtered.tasks]

def test_merging():
    tasks = [
        TreeTask(id="t3", task="Integrate RunArchive", intent="Integrate", files="luna.py", symbols="Luna", complexity=1),
        TreeTask(id="t4", task="Log info", intent="Log", files="luna.py", symbols="Luna", complexity=2),
    ]
    plan = ForestPlan(goal="Test", tasks=tasks)
    merged = merge_similar_tasks(plan)
    print(f"Merged tasks: {len(merged.tasks)}")
    assert len(merged.tasks) == 1
    assert "Integrate RunArchive AND Log info" in merged.tasks[0].task
    assert merged.tasks[0].complexity == 2

def test_error_compaction():
    task = TreeTask(id="t1", task="Integrate", intent="Feature", files="luna.py", symbols="Luna")
    raw = "I have explained what to do but I didn't write code."
    err = compact_no_patch_error(task, raw)
    print(f"Compact Error: {err}")
    assert "no code change" in err
    assert "luna.py" in err

if __name__ == "__main__":
    test_clean_diff()
    test_filtering()
    test_merging()
    test_error_compaction()
    print("All tests passed!")
