from app.extractor import local_extract

def test_extracts_action_and_evidence():
    text="Action: Priya must send the launch plan by 2026-11-02."
    r=local_extract(text,"notes.txt")
    assert len(r.tasks)==1
    assert r.tasks[0].due_date.isoformat()=="2026-11-02"
    assert r.tasks[0].evidence[0].quote==text

def test_missing_owner_flag():
    r=local_extract("Please review the onboarding checklist by 2026-11-05.","notes.txt")
    assert r.tasks
    assert any("Missing owner" in f for f in r.tasks[0].uncertainty_flags)

def test_non_action_text():
    assert local_extract("The room was bright and coffee was warm.","notes.txt").tasks==[]
