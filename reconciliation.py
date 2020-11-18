# This file is part of Cash & Bank Reconciliation module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.model import (
    Workflow, ModelView, ModelSQL, fields, Unique)
from trytond.pyson import Eval, If, Or, Bool, Not
from trytond.i18n import gettext
from trytond.exceptions import UserError
from trytond.modules.log_action import LogActionMixin, write_log
from decimal import Decimal
from datetime import timedelta


STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('cancel', 'Canceled'),
]

_STATES = {
    'readonly': Eval('state') != 'draft',
}

_DEPENDS = ['state']

_STATES_LINE = {
    'readonly': Eval('reconciliation_state') != 'draft',
}

_DEPENDS_LINE = ['reconciliation_state']


class Reconciliation(Workflow, ModelSQL, ModelView):
    "Bank Reconciliation"
    __name__ = "cash_bank.reconciliation"
    company = fields.Many2One('company.company', 'Company', required=True,
        states={
            'readonly': True,
            },
        domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ],
        select=True)
    cash_bank = fields.Many2One('cash_bank.cash_bank',
            'Bank', required=True,
            states={
                'readonly': Or(
                        Eval('state') != 'draft',
                        Bool(Eval('lines'))
                        ),
                },
            domain=[
                ('company', '=', Eval('company')),
                ('type', '=', 'bank')
                ],
            depends=_DEPENDS + ['company', 'lines'])
    currency = fields.Many2One('currency.currency', 'Currency', required=True,
        states={'readonly': True})
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    number = fields.Char('Number', size=None, readonly=True, select=True)
    reference = fields.Char('Reference', size=None)
    note = fields.Text('Note', size=None,
        states=_STATES, depends=_DEPENDS)
    date = fields.Date('Date', required=True,
        states=_STATES, depends=_DEPENDS)
    date_start = fields.Date('Start Date', required=True,
        states={
            'readonly': Or(
                    Eval('state') != 'draft',
                    Bool(Eval('lines')),
                    Not(Eval('is_first_reconciliation'))
                    ),
            },
            depends=_DEPENDS + ['lines', 'is_first_reconciliation'])
    date_end = fields.Date('End Date', required=True,
        states={
            'readonly': Or(
                    Eval('state') != 'draft',
                    Bool(Eval('lines'))
                    ),
            },
        depends=_DEPENDS + ['lines'])
    lines = fields.One2Many('cash_bank.reconciliation.line', 'reconciliation',
        'Lines', states=_STATES, depends=_DEPENDS)
    last_bank_balance = fields.Numeric('Last Bank Balance', required=True,
        digits=(16, Eval('currency_digits', 2)),
        states={
            'readonly': Or(
                    Eval('state') != 'draft',
                    Not(Eval('is_first_reconciliation'))
                    ),
            },
        depends=_DEPENDS + ['currency_digits', 'is_first_reconciliation'])
    bank_balance = fields.Numeric('Current Bank Balance', required=True,
        digits=(16, Eval('currency_digits', 2)),
        states=_STATES, depends=_DEPENDS + ['currency_digits'])
    check_amount = fields.Function(fields.Numeric('Amount Checked',
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits']),
        'get_check_amount')
    diff = fields.Function(fields.Numeric('Diff',
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits']),
        'get_diff')
    is_first_reconciliation = fields.Function(fields.Boolean('Active'),
        'get_is_first_reconciliation')
    state = fields.Selection(STATES, 'State', readonly=True, required=True)
    logs = fields.One2Many('cash_bank.reconciliation.log_action',
        'resource', 'Logs', readonly=True)

    @classmethod
    def __setup__(cls):
        super(Reconciliation, cls).__setup__()
        cls._order[0] = ('date_start', 'DESC')

        cls._transitions |= set(
            (
                ('draft', 'confirmed'),
                ('confirmed', 'cancel'),
                ('cancel', 'draft'),
            )
            )

        cls._buttons.update({
            'cancel': {
                'invisible': ~Eval('state').in_(['confirmed']),
                },
            'confirm': {
                'invisible': ~Eval('state').in_(['draft']),
                },
            'draft': {
                'invisible': ~Eval('state').in_(['cancel']),
                'icon': If(Eval('state') == 'cancel',
                    'tryton-clear', 'tryton-go-previous'),
                },
            'complete_lines': {
                'invisible': Eval('state') != 'draft',
                },
            })

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            company = Company(company)
            return company.currency.id

    @staticmethod
    def default_currency_digits():
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            company = Company(company)
            return company.currency.digits
        return 2

    @staticmethod
    def default_is_first_reconciliation():
        return True

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2

    def get_check_amount(self, name=None):
        res = Decimal('0.0')
        if self.lines:
            for line in self.lines:
                if line.amount and line.check:
                    res += line.amount
        return res

    def get_diff(self, name=None):
        bank_balance = self.bank_balance if self.bank_balance \
            else Decimal('0.0')
        last_bank_balance = self.last_bank_balance if self.last_bank_balance \
            else Decimal('0.0')
        return (bank_balance - last_bank_balance) - self.check_amount

    def get_is_first_reconciliation(self, name):
        last_reconciliation = self.search([
                ('cash_bank', '=', self.cash_bank.id),
                ('state', '=', 'confirmed'),
                ], limit=1)
        if not last_reconciliation:
            return True
        return False

    def get_rec_name(self, name):
        if self.number:
            return self.number
        return str(self.id)

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('number',) + tuple(clause[1:])]

    @fields.depends('cash_bank')
    def on_change_cash_bank(self):
        self.bank_balance = None
        self.last_bank_balance = None
        self.check_amount = None
        self.diff = None
        self.date_start = None
        self.date_end = None
        self.is_first_reconciliation = False
        if self.cash_bank:
            self.bank_balance = Decimal('0.0')
            self.date_start, self.last_bank_balance = \
                self._get_last_reconciliation(self.cash_bank)
            if self.date_start is None:
                self.is_first_reconciliation = True

    @classmethod
    def last_cash_bank_reconciliation_date(cls, account):
        pool = Pool()
        CashBank = pool.get('cash_bank.cash_bank')

        cash_bank = CashBank.search([
            ('account', '=', account.id)
        ])
        if not cash_bank:
            return

        date, _ = cls._get_last_reconciliation(cash_bank[0])
        if date:
            date = date - timedelta(days=1)
        return date

    @classmethod
    def _get_last_reconciliation(cls, cash_bank):
        last_reconciliation = cls.search([
            ('cash_bank', '=', cash_bank.id),
            ('state', '=', 'confirmed'),
        ], order=[('date_start', 'DESC')], limit=1)
        if not last_reconciliation:
            return None, Decimal('0.0')
        lr = last_reconciliation[0]
        return lr.date_end + timedelta(days=1), lr.bank_balance

    @fields.depends('lines', 'bank_balance', 'last_bank_balance')
    def on_change_bank_balance(self):
        self.check_amount = Decimal('0.0')
        self.diff = Decimal('0.0')
        self.check_amount = self.get_check_amount()
        self.diff = self.get_diff()

    @fields.depends(methods=['on_change_bank_balance'])
    def on_change_last_bank_balance(self):
        self.on_change_bank_balance()

    @fields.depends(methods=['on_change_bank_balance'])
    def on_change_lines(self):
        self.on_change_bank_balance()

    def verify_is_last(self):
        recons = self.search([
                ('cash_bank', '=', self.cash_bank.id),
                ('date_start', '>', self.date_start),
                ('state', '=', 'confirmed'),
                ])
        if recons:
            raise UserError(
                gettext(
                    'cash_bank_reconciliation.reconciliation_last',
                    reconciliation=self.rec_name
                ))

    def verify_is_next(self):
        if self.is_first_reconciliation:
            return
        recons = self.search([
                ('cash_bank', '=', self.cash_bank.id),
                ('date_end', '=', self.date_start - timedelta(days=1)),
                ('state', '=', 'confirmed'),
                ])
        if not recons or len(recons) > 1:
            raise UserError(
                gettext(
                    'cash_bank_reconciliation.reconciliation_next',
                    reconciliation=self.rec_name
                ))

    def verify(self):
        self.verify_is_last()
        self.verify_is_next()
        if self.diff != 0:
            raise UserError(
                gettext(
                    'cash_bank_reconciliation.reconciliation_diff',
                    reconciliation=self.rec_name
                ))
        for line in self.lines:
            mvl = line.move_line
            if mvl.move.state != 'posted':
                raise UserError(
                    gettext(
                        'cash_bank_reconciliation.'
                        'reconciliation_move_line_posted',
                        reconciliation=self.rec_name,
                        line=line.rec_name
                    ))
            if mvl.cash_bank_reconciliation:
                raise UserError(
                    gettext(
                        'cash_bank_reconciliation.'
                        'reconciliation_move_line_reconciliation',
                        reconciliation=self.rec_name,
                        reconciliation2=mvl.cash_bank_reconciliation.rec_name,
                        line=line.rec_name
                    ))

    def write_to_move_line(self, set_none=False):
        # This way we can modify account move lines that are in posted moves.
        if not self.lines:
            return

        str_id = ''
        for line in self.lines:
            if not line.check:
                continue
            if str_id != '':
                str_id += ','
            str_id += str(line.move_line.id)
        if str_id == '':
            return
        str_id = '(' + str_id + ')'

        value = str(self.id)
        if set_none:
            value = 'NULL'

        cursor = Transaction().connection.cursor()
        sql = "UPDATE account_move_line SET cash_bank_reconciliation="
        sql += value
        sql += " WHERE id IN " + str_id
        cursor.execute(sql)

    @classmethod
    def create(cls, vlist):
        reconciliations = super(Reconciliation, cls).create(vlist)
        write_log('log_action.msg_created', reconciliations)
        return reconciliations

    @classmethod
    def delete(cls, reconciliations):
        for reconciliation in reconciliations:
            if reconciliation.state not in ['draft']:
                write_log('log_action.msg_deletion_attempt', [reconciliation])
                raise UserError(
                    gettext(
                        'cash_bank_reconciliation.'
                        'reconciliation_delete_draft',
                        reconciliation=reconciliation.rec_name,
                        state='Draft'
                    ))
        super(Reconciliation, cls).delete(reconciliations)

    @classmethod
    def set_number(cls, reconciliations):
        pool = Pool()
        Sequence = pool.get('ir.sequence')
        Config = pool.get('cash_bank.configuration')
        config = Config(1)
        for reconciliation in reconciliations:
            if reconciliation.number:
                continue
            reconciliation.number = \
                Sequence.get_id(config.reconciliation_seq.id)
        cls.save(reconciliations)

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, reconciliations):
        write_log('log_action.msg_draft', reconciliations)

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, reconciliations):
        pool = Pool()
        Receipt = pool.get('cash_bank.receipt')
        receipts = []
        for recon in reconciliations:
            recon.verify()
            recon.write_to_move_line()
            for line in recon.lines:
                if line.check and line.receipt:
                    line.receipt.cash_bank_reconciliation = line
                    receipts.append(line.receipt)
        Receipt.save(receipts)
        cls.set_number(reconciliations)
        write_log('log_action.msg_confirmed', reconciliations)

    @classmethod
    @ModelView.button
    @Workflow.transition('cancel')
    def cancel(cls, reconciliations):
        pool = Pool()
        Receipt = pool.get('cash_bank.receipt')
        rps = []
        for recon in reconciliations:
            recon.verify_is_last()
            recon.write_to_move_line(True)
            for line in recon.lines:
                if line.check and line.receipt:
                    line.receipt.cash_bank_reconciliation = None
                    rps.append(line.receipt)
        Receipt.save(rps)
        write_log('log_action.msg_cancelled', reconciliations)

    @classmethod
    @ModelView.button
    def complete_lines(cls, reconciliations):
        for recon in reconciliations:
            cls._complete_lines(recon)

    @classmethod
    def _complete_lines(cls, recon):
        pool = Pool()
        Line = pool.get('cash_bank.reconciliation.line')
        Move = pool.get('account.move.line')

        lines = []
        move_ids = {}

        for line in recon.lines:
            if line.move_line:
                move_ids[line.move_line.id] = line

        domain = [
            ('account', '=', recon.cash_bank.account),
            ('move.date', '<=', recon.date_end),
            ('move.company', '=', recon.company.id),
            ('cash_bank_reconciliation', '=', None),
            ]
        if recon.cash_bank.date_ignore:
            domain.append(
                ('move.date', '>', recon.cash_bank.date_ignore)
                )

        moves = Move.search(domain)
        for mv in moves:
            if mv.id in move_ids:
                line = move_ids[mv.id]
            else:
                line = Line()
                line.move_line = mv
            line.date = mv.date
            line.amount = mv.debit - mv.credit
            line.reconciliation = recon
            lines.append(line)

        Line.save(lines)


class ReconciliationLine(ModelSQL, ModelView):
    'Bank Reconciliation Line'
    __name__ = 'cash_bank.reconciliation.line'
    reconciliation = fields.Many2One('cash_bank.reconciliation',
        'Reconciliation', required=True, ondelete='CASCADE',
        states=_STATES_LINE, depends=_DEPENDS_LINE)
    move_line = fields.Many2One('account.move.line', 'Move line',
        states={
            'readonly': True,
            },
        domain=[
            ('account', '=', Eval('account')),
            ('move.date', '<=',
                Eval('_parent_reconciliation', {}).get('date_end', None)),
            ('move.company', '=',
                Eval('_parent_reconciliation', {}).get('company', -1)),
            If(Eval('reconciliation_state') == 'draft',
                [],
                [
                    ('move.state', '=', 'posted'),
                    ('move.cash_bank_reconciliation', '=', Eval('id'))
                ]
            )
        ], depends=_DEPENDS_LINE + ['id', 'account'])
    account = fields.Function(fields.Many2One('account.account', "Account"),
        'get_account')
    receipt = fields.Function(fields.Many2One('cash_bank.receipt', 'Receipt'),
        'get_receipt')
    date = fields.Date('Date',
        states={
            'required': True,
            'readonly': True,
        })
    amount = fields.Numeric('Amount',
        digits=(16, Eval('currency_digits', 2)),
        states={
            'required': True,
            'readonly': True,
        }, depends=['currency_digits'])
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    effective_date = fields.Date('Effective date',
        states=_STATES_LINE, depends=_DEPENDS_LINE)
    comment = fields.Char('Comment',
        states=_STATES_LINE, depends=_DEPENDS_LINE)
    description = fields.Function(fields.Char('Description'),
        'get_move_line_field')
    move_description = fields.Function(fields.Char('Move Description'),
        'get_move_line_field')
    reconciliation_state = fields.Function(
        fields.Selection(STATES, 'Reconciliation State'),
        'on_change_with_reconciliation_state')
    check = fields.Boolean('Check',
        states=_STATES_LINE, depends=_DEPENDS_LINE)

    @classmethod
    def __setup__(cls):
        super(ReconciliationLine, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('reconciliation_line_move_line_uniq',
                Unique(t, t.reconciliation, t.move_line),
             'Account Move Line can appear just once '
             'in the Reconciliation.'),
            ]

        cls._order = [
                ('date', 'ASC'),
                ('move_line.id', 'ASC')
                ]

    @fields.depends('reconciliation',
                    '_parent_reconciliation.currency_digits')
    def on_change_with_currency_digits(self, name=None):
        if self.reconciliation:
            return self.reconciliation.currency_digits
        return 2

    @fields.depends('reconciliation', '_parent_reconciliation.state')
    def on_change_with_reconciliation_state(self, name=None):
        if self.reconciliation:
            return self.reconciliation.state

    @fields.depends('move_line')
    def on_change_move_line(self):
        self.date = None
        self.amount = None
        self.move_description = None
        self.description = None
        self.receipt = None
        if self.move_line:
            self._get_move_line_data()
            if self.move_line.move.origin:
                self.receipt = self.move_line.move.receipt

    def _get_move_line_data(self):
        if self.move_line:
            self.date = self.move_line.date
            self.amount = self.move_line.debit - self.move_line.credit
            self.move_description = self.move_line.move_description
            self.description = self.move_line.description

    def get_move_line_field(self, name=None):
        if self.move_line:
            value = getattr(self.move_line, name)
            return value

    def get_account(self, name=None):
        if self.reconciliation:
            return self.reconciliation.cash_bank.account.id

    def get_receipt(self, name=None):
        if self.move_line and self.move_line.move.origin:
            if self.move_line.move.origin.__class__.__name__ == \
                    'cash_bank.receipt':
                return self.move_line.move.origin.id

    def get_rec_name(self, name):
        show = self.reconciliation.rec_name
        show += ' (' + str(self.reconciliation.date_start) + ' - '
        show += str(self.reconciliation.date_end) + ') - '
        show += str(self.date)
        if self.receipt:
            show += ' / ' + self.receipt.rec_name
        return show


class ReconciliationLog(LogActionMixin):
    "Reconciliation Logs"
    __name__ = "cash_bank.reconciliation.log_action"
    resource = fields.Many2One('cash_bank.reconciliation',
        'Reconciliation', ondelete='CASCADE', select=True)
