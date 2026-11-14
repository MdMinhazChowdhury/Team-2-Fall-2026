from conftest import create_list, create_task, send
from sqlalchemy import event


def test_task_page_batches_children_and_preserves_details(auth, store):
    task_list = create_list(auth)
    tag = send(auth, "POST", "/tags", {"name": "School"}).json()["id"]
    for i in range(25):
        create_task(
            auth,
            task_list["id"],
            title=f"Task {i}",
            checklist=[{"text": f"First {i}"}, {"text": "Second", "completed": True}],
            tag_ids=[tag] if i % 2 else [],
        )
    statements = []

    def count(conn, cursor, sql, parameters, context, executemany):
        if sql.lstrip().upper().startswith("SELECT") and (
            "checklist_items" in sql or "task_tags" in sql
        ):
            statements.append(sql)

    event.listen(store.kw["bind"], "before_cursor_execute", count)
    try:
        response = auth.get("/api/tasks?page_size=25")
    finally:
        event.remove(store.kw["bind"], "before_cursor_execute", count)
    assert response.status_code == 200
    assert len(statements) == 2
    rows = response.json()["items"]
    assert len(rows) == 25
    for row in rows:
        i = int(row["title"].split()[1])
        assert row["checklist"] == [
            {"text": f"First {i}", "completed": False},
            {"text": "Second", "completed": True},
        ]
        assert row["tag_ids"] == ([tag] if i % 2 else [])
