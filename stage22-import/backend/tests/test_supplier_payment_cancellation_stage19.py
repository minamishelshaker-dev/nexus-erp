from pathlib import Path


def _source():
    return Path(__file__).parents[1].joinpath("app/services/purchase_service.py").read_text()


def test_cancellation_locks_payment_and_invoices():
    source = _source()
    method = source.split("async def cancel_supplier_payment(", 1)[1].split("# List/Query Methods", 1)[0]
    assert "SupplierPayment.id == payment_id" in method
    assert ".with_for_update()" in method
    assert "PurchaseInvoice.id == invoice_id" in method


def test_cancellation_reverses_accounting_before_marking_cancelled():
    method = _source().split("async def cancel_supplier_payment(", 1)[1].split("# List/Query Methods", 1)[0]
    assert "reverse_journal_entry(" in method
    assert method.index("reverse_journal_entry(") < method.index("payment.state = SupplierPaymentState.CANCELLED.value")


def test_cancellation_restores_invoice_balances_and_retains_allocation_history():
    method = _source().split("async def cancel_supplier_payment(", 1)[1].split("# List/Query Methods", 1)[0]
    assert "invoice.amount_paid = paid - allocated" in method
    assert "invoice.amount_residual = Decimal(str(invoice.amount_total or 0)) - invoice.amount_paid" in method
    assert "allocation.is_deleted = True" in method
    assert "allocation.deleted_at = datetime.utcnow()" in method


def test_cancel_endpoint_requires_both_purchase_and_accounting_permissions():
    source = Path(__file__).parents[1].joinpath("app/api/v1/endpoints/purchase.py").read_text()
    route = source.split('async def cancel_supplier_payment(', 1)[1].split('@router.post', 1)[0]
    assert '"purchase.invoice.update"' in route
    assert '"accounting.journal.reverse"' in route
