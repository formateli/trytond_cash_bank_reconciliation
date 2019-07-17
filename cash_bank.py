# This file is part of Tryton cash_bank_reconciliation module.
# The COPYRIGHT file at the top level of this repository
# contains the full copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)

__all__ = ['CashBank' 'CashBankDates']


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
