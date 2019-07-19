# This file is part of trytond-cash_bank_reconciliation module.
# The COPYRIGHT file at the top level of this repository
# contains the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import ModelSQL, fields
from trytond.modules.company.model import CompanyValueMixin
from trytond.pyson import Eval

__all__ = ['Configuration', 'ConfigurationSequences']


class Configuration(metaclass=PoolMeta):
    __name__ = 'cash_bank.configuration'
    reconciliation_seq = fields.MultiValue(fields.Many2One(
        'ir.sequence', "Bank Reconciliation Sequence", required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'cash_bank.reconciliation'),
        ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'reconciliation_seq',}:
            return pool.get('cash_bank.configuration.sequences')
        return super(Configuration, cls).multivalue_model(field)


class ConfigurationSequences(metaclass=PoolMeta):
    __name__ = 'cash_bank.configuration.sequences'
    reconciliation_seq = fields.Many2One(
        'ir.sequence', "Bank Reconciliation Sequence", required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'cash_bank.reconciliation'),
        ])
