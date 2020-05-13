# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configuration
from . import cash_bank
from . import reconciliation
from . import account_move


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequences,
        cash_bank.CashBank,
        cash_bank.CashBankDates,
        cash_bank.Receipt,
        reconciliation.Reconciliation,
        reconciliation.ReconciliationLine,
        reconciliation.ReconciliationLog,
        account_move.Move,
        account_move.MoveLine,
        module='cash_bank_reconciliation', type_='model')
