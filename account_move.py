# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['Move', 'MoveLine']


class Move(metaclass=PoolMeta):
    __name__ = 'account.move'

    @classmethod
    @ModelView.button
    def post(cls, moves):
        pool = Pool()
        BankReconciliation = pool.get('cash_bank.reconciliation')
        reconciliations = {}  # Key: account, value: last reconc. date
        for move in moves:
            for line in move.lines:
                if line.account.id not in reconciliations:
                    last_date = \
                        BankReconciliation.last_cash_bank_reconciliation_date(
                            line.account)
                    if last_date is None:
                        continue
                    reconciliations[line.account.id] = last_date

                last_date = reconciliations[line.account.id]
                if last_date and move.date <= last_date:
                    raise UserError(
                        gettext(
                            'cash_bank_reconciliation.acc_invalid_move',
                            account=line.account.rec_name
                        ))

        super(Move, cls).post(moves)


class MoveLine(metaclass=PoolMeta):
    __name__ = 'account.move.line'
    cash_bank_reconciliation = fields.Many2One('cash_bank.reconciliation',
        'Reconciliation')
