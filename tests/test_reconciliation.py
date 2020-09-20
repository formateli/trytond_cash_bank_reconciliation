# This file is part of Cash & Bank Reconciliation module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart
from trytond.modules.cash_bank.tests import (
    create_cash_bank, create_sequence,
    create_journal, create_fiscalyear)
import datetime
from decimal import Decimal


class ReconciliationTestCase(ModuleTestCase):
    'Test Cash Bank Reconciliation module'
    module = 'cash_bank_reconciliation'

    @with_transaction()
    def test_reconciliation(self):
        pool = Pool()
        Account = pool.get('account.account')
        Receipt = pool.get('cash_bank.receipt')
        Reconciliation = pool.get('cash_bank.reconciliation')
        Line = pool.get('cash_bank.reconciliation.line')
        Config = pool.get('cash_bank.configuration')

        party = self._create_party('Party test', None)

        transaction = Transaction()

        company = create_company()
        with set_company(company):
            create_chart(company)
            create_fiscalyear(company)

            account_transfer, = Account.search([
                    ('name', '=', 'Main Expense'),
                    ])
            account_cash, = Account.search([
                    ('name', '=', 'Main Cash'),
                    ])
            account_revenue, = Account.search([
                    ('name', '=', 'Main Revenue'),
                    ])
            account_expense, = Account.search([
                    ('name', '=', 'Main Expense'),
                    ])

            config = Config(
                account_transfer=account_transfer)
            config.save()

            journal = create_journal(company, 'journal_cash')

            sequence = create_sequence(
                'Cash/Bank Sequence',
                'cash_bank.receipt',
                company)
            sequence_convertion = create_sequence(
                'Cash/Bank Convertion',
                'cash_bank.convertion',
                company)
            sequence_reconciliation = create_sequence(
                'Cash/Bank Reconciliation',
                'cash_bank.reconciliation',
                company)

            config.convertion_seq = sequence_convertion
            config.reconciliation_seq = sequence_reconciliation
            config.save()

            bank = create_cash_bank(
                company, 'Main Bank', 'bank',
                journal, account_cash, sequence
                )
            self.assertEqual(len(bank.receipt_types), 2)

            date = datetime.date.today()

            rcps = [
                self._get_receipt(
                    company, bank, 'in', date,
                    Decimal('100.0'), account_revenue),
                self._get_receipt(
                    company, bank, 'in', date,
                    Decimal('200.0'), account_revenue),
                self._get_receipt(
                    company, bank, 'in', date,
                    Decimal('300.0'), account_revenue),
                self._get_receipt(
                    company, bank, 'in', date,
                    Decimal('400.0'), account_revenue),
                self._get_receipt(
                    company, bank, 'out', date,
                    Decimal('10.0'), account_expense, party),
                self._get_receipt(
                    company, bank, 'out', date,
                    Decimal('20.0'), account_expense, party),
            ]
            Receipt.save(rcps)
            Receipt.confirm(rcps)

            recon = Reconciliation(
                company=company,
                cash_bank=bank,
                date=date,
                date_start=date,
                date_end=date,
                bank_balance=Decimal(600.0),
                last_bank_balance=Decimal(0.0),
                )
            recon.save()

            Reconciliation.complete_lines([recon])
            self.assertEqual(len(recon.lines), 6)

            transaction.commit()

            with self.assertRaises(UserError):
                # Diff != 0. There is no lines checked
                Reconciliation.confirm([recon])
            transaction.rollback()

            lines = Line.search([
                    ('reconciliation', '=', recon.id),
                    ('amount', 'in',
                        [Decimal('100.0'), Decimal('200.0'),
                        Decimal('300.0')]),
                    ])
            self.assertEqual(len(lines), 3)
            for line in lines:
                line.check = True
            Line.save(lines)
            recon.save()

            self.assertEqual(recon.diff, Decimal('0.0'))
            transaction.commit()

            with self.assertRaises(UserError):
                # Account move lines are not posted
                Reconciliation.confirm([recon])
            transaction.rollback()

            Receipt.post(rcps)
            Reconciliation.confirm([recon])

            # Account moves can not be posted if a confirmed reconciliation
            # invalidates them

            # Same date
            receipt = self._get_receipt(
                    company, bank, 'in', date,
                    Decimal('99.0'), account_revenue)
            receipt.save()
            Receipt.confirm([receipt])

            transaction.commit()
            with self.assertRaises(UserError):
                Receipt.post([receipt])
            transaction.rollback()

            # Date before
            new_date = date - datetime.timedelta(days=1)
            receipt = self._get_receipt(
                    company, bank, 'in', new_date,
                    Decimal('99.0'), account_revenue)
            receipt.save()
            Receipt.confirm([receipt])

            transaction.commit()
            with self.assertRaises(UserError):
                Receipt.post([receipt])
            transaction.rollback()

            # Date OK
            new_date = date + datetime.timedelta(days=1)
            receipt = self._get_receipt(
                    company, bank, 'in', new_date,
                    Decimal('99.0'), account_revenue)
            receipt.save()
            Receipt.confirm([receipt])
            Receipt.post([receipt])

    def _get_receipt(self, company, cash_bank, receipt_type,
                     date, amount, account, party=None):
        pool = Pool()
        Receipt = pool.get('cash_bank.receipt')
        ReceiptType = pool.get('cash_bank.receipt_type')
        Line = pool.get('cash_bank.receipt.line')

        type_ = ReceiptType.search([
            ('cash_bank', '=', cash_bank.id),
            ('type', '=', receipt_type)])[0]

        receipt = Receipt(
            company=company,
            cash_bank=cash_bank,
            party=party,
            type=type_,
            date=date,
            cash=amount,
            lines=[Line(account=account, amount=amount)]
            )

        return receipt

    @classmethod
    def _create_party(cls, name, account):
        pool = Pool()
        Party = pool.get('party.party')
        Address = pool.get('party.address')
        addr = Address(name=name)
        party = Party(
            name=name,
            account_receivable=account,
            addresses=[addr]
            )
        party.save()
        return party


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        ReconciliationTestCase))
    return suite
