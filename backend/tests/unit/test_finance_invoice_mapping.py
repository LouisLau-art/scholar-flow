from app.services.editor_service import EditorService, FinanceListFilters


def test_effective_status_uses_amount_zero_as_waived():
    svc = EditorService()
    assert svc._effective_status(raw_status="paid", amount=0) == "waived"
    assert svc._effective_status(raw_status="waived", amount=100) == "waived"
    assert svc._effective_status(raw_status="paid", amount=1200) == "paid"
    assert svc._effective_status(raw_status="unpaid", amount=1200) == "unpaid"


def test_filter_and_sort_finance_rows_status_query_and_amount():
    svc = EditorService()
    rows = [
        {
            "invoice_id": "1",
            "manuscript_id": "m1",
            "invoice_number": "INV-001",
            "manuscript_title": "Cancer Trial",
            "authors": "A",
            "amount": 200.0,
            "raw_status": "paid",
            "effective_status": "paid",
            "updated_at": "2026-02-09T01:00:00Z",
        },
        {
            "invoice_id": "2",
            "manuscript_id": "m2",
            "invoice_number": "INV-002",
            "manuscript_title": "Brain Study",
            "authors": "B",
            "amount": 100.0,
            "raw_status": "unpaid",
            "effective_status": "unpaid",
            "updated_at": "2026-02-09T02:00:00Z",
        },
        {
            "invoice_id": "3",
            "manuscript_id": "m3",
            "invoice_number": "INV-003",
            "manuscript_title": "Genome Maps",
            "authors": "C",
            "amount": 0.0,
            "raw_status": "paid",
            "effective_status": "waived",
            "updated_at": "2026-02-09T03:00:00Z",
        },
    ]

    filtered = svc._filter_and_sort_finance_rows(
        rows,
        filters=FinanceListFilters(status="unpaid", q="brain", sort_by="amount", sort_order="asc"),
    )
    assert len(filtered) == 1
    assert filtered[0]["invoice_id"] == "2"


def test_list_finance_invoices_applies_pagination_and_meta():
    svc = EditorService()
    fake_rows = [
        {
            "invoice_id": "1",
            "manuscript_id": "m1",
            "invoice_number": "INV-001",
            "manuscript_title": "Paper 1",
            "authors": "A",
            "amount": 300.0,
            "currency": "USD",
            "raw_status": "unpaid",
            "effective_status": "unpaid",
            "confirmed_at": None,
            "updated_at": "2026-02-09T00:00:00Z",
            "payment_gate_blocked": True,
        },
        {
            "invoice_id": "2",
            "manuscript_id": "m2",
            "invoice_number": "INV-002",
            "manuscript_title": "Paper 2",
            "authors": "B",
            "amount": 100.0,
            "currency": "USD",
            "raw_status": "paid",
            "effective_status": "paid",
            "confirmed_at": "2026-02-09T01:00:00Z",
            "updated_at": "2026-02-09T01:00:00Z",
            "payment_gate_blocked": False,
        },
    ]

    # 适配新实现：分页/总数在 _load_finance_source_rows 完成，service 仅映射当前页行。
    svc._load_finance_source_rows = (  # type: ignore[method-assign]
        lambda *, filters, export_mode: ([{"id": "stub-page-2"}], 2)
    )
    svc._build_finance_rows = lambda _rows: [fake_rows[1]]  # type: ignore[method-assign]

    result = svc.list_finance_invoices(
        filters=FinanceListFilters(status="all", page=2, page_size=1, sort_by="amount", sort_order="desc")
    )
    assert result["meta"]["total"] == 2
    assert result["meta"]["page"] == 2
    assert len(result["rows"]) == 1
    assert result["rows"][0]["invoice_id"] == "2"
