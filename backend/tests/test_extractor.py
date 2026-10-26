from datetime import date, timedelta
from app.extractor import local_extract, parse_date

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

def test_hinglish_task_extraction():
    text = "Action: Priya ko kal tak launch plan send karna hai. Alex Friday tak deployment script fix karega."
    r = local_extract(text, "hinglish_meeting.txt")
    assert len(r.tasks) >= 2
    priya_task = next(t for t in r.tasks if t.assignee == "Priya")
    alex_task = next(t for t in r.tasks if t.assignee == "Alex")
    
    # Check that "kal tak" resolved to tomorrow
    expected_tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert priya_task.due_date is not None
    assert priya_task.due_date.isoformat() == expected_tomorrow
    
    # Check that Alex has a due date for Friday
    assert alex_task.due_date is not None
    assert alex_task.due_date.weekday() == 4  # Friday
