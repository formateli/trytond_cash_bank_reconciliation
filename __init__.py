#This file is part of Tryton cash_bank_reconciliation module. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from . import reconciliation


def register():
    Pool.register(
        reconciliation.Reconciliation,
        reconciliation.ReconciliationLine,
        reconciliation.ReconciliationLog,
        module='cash_bank_reconciliation', type_='model')
