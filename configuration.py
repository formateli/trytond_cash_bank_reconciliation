# This file is part of Cash & Bank Reconciliation module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from trytond.pyson import Eval, Id


class Configuration(metaclass=PoolMeta):
    __name__ = 'cash_bank.configuration'
    reconciliation_seq = fields.MultiValue(fields.Many2One(
            'ir.sequence', "Bank Reconciliation Sequence",
            domain=[
                ('company', 'in',
                    [Eval('context', {}).get('company', -1), None]),
                ('sequence_type', '=',
                    Id('cash_bank_reconciliation', 'sequence_type_cash_bank_reconciliation')),
                ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'reconciliation_seq':
            return pool.get('cash_bank.configuration.sequences')
        return super(Configuration, cls).multivalue_model(field)


class ConfigurationSequences(metaclass=PoolMeta):
    __name__ = 'cash_bank.configuration.sequences'
    reconciliation_seq = fields.Many2One(
        'ir.sequence', "Bank Reconciliation Sequence",
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('sequence_type', '=',
                Id('cash_bank_reconciliation', 'sequence_type_cash_bank_reconciliation')),
            ], depends=['company'])
