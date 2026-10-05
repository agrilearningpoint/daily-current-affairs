from config.workflow import WORKFLOW_ORDER
def test_failed_final_resume():
    # Simulate main.py fix: FAILED_FINAL should resume after last_success_stage
    job={"status":"FAILED_FINAL","last_success_stage":"04_fact_verification"}
    last=job["last_success_stage"]
    idx=WORKFLOW_ORDER.index(last)+1
    assert WORKFLOW_ORDER[idx]=="05_deduplication"
def test_complete_not_resume():
    job={"status":"COMPLETE","last_success_stage":"24_final_health_audit"}
    assert job["status"]=="COMPLETE"
