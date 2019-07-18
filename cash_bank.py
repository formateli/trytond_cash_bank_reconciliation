# This file is part of Tryton cash_bank_reconciliation module.
# The COPYRIGHT file at the top level of this repository
# contains the full copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.pyson import Eval, Not, Bool

__all__ = ['CashBank' 'CashBankDates', 'Receipt']


class CashBank(CompanyMultiValueMixin, metaclass=PoolMeta):
    __name__ = 'cash_bank.cash_bank'

    date_ignore = fields.MultiValue(fields.Date('Ignore Lines before'))
    dates = fields.One2Many(
        'cash_bank.dates', 'cash_bank', 'Dates')

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'date_ignore':
            return pool.get('cash_bank.dates')
        return super(CashBank, cls).multivalue_model(field)


class CashBankDates(ModelSQL, CompanyValueMixin):
    "Cash/Bank dates"
    __name__ = 'cash_bank.dates'
    cash_bank = fields.Many2One(
        'cash_bank.cash_bank', 'Cash/Bank', ondelete='CASCADE', select=True)
    date_ignore = fields.Date('Ignore Lines before')


class Receipt(metaclass=PoolMeta):
    __name__ = "cash_bank.receipt"
    cash_bank_reconciliation = fields.Many2One('cash_bank.reconciliation.line',
        'Reconciliation')
    reconciliation_effective_date = fields.Function(
        fields.Date('Effective date'), 'get_reconciliation_field')
    reconciliation_comment = fields.Function(
        fields.Char('Comment'), 'get_reconciliation_field')

    def get_reconciliation_field(self, name=None):
        if self.cash_bank_reconciliation:
            value = getattr(self.cash_bank_reconciliation, name[15:])
            return value

    @classmethod
    def view_attributes(cls):
        return super(Receipt, cls).view_attributes() + [
            ('//page[@name="cash_bank_reconciliation"]', 'states', {
                    'invisible': Not(Bool(Eval('cash_bank_reconciliation'))),
                    })]
