# This file is part of Tryton cash_bank_reconciliation module.
# The COPYRIGHT file at the top level of this repository
# contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['MoveLine']


class MoveLine(metaclass=PoolMeta):
    __name__ = 'account.move.line'
    cash_bank_reconciliation = fields.Many2One('cash_bank.reconciliation',
        'Reconciliation')
