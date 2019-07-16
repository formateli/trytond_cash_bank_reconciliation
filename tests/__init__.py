# This file is part of Tryton cash_bank_reconciliation module. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.cash_bank_reconciliation.tests.test_reconciliation import suite
except ImportError:
    from .test_reconciliation import suite

__all__ = ['suite']
