# This file is part of cash_bank_reconciliation module. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction


class ReconciliationTestCase(ModuleTestCase):
    'Test Cash Bank Reconciliation module'
    module = 'cash_bank_reconciliation'

    @with_transaction()
    def test_reconciliation(self):
        pool = Pool()
        Reconciliation = pool.get('cash_bank.reconciliation')
        Line = pool.get('cash_bank.reconciliation.line')


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        ReconciliationTestCase))
    return suite
