#This file is part of tryton-cash_bank_reconciliation module. The COPYRIGHT file at the top level of this
#repository contains the full copyright notices and license terms.
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.model import (
    Workflow, ModelView, ModelSQL, fields)
from trytond.pyson import Eval, If
from trytond.modules.log_action import LogActionMixin, write_log

__all__ = ['Reconciliation', 'ReconciliationLine', 'ReconciliationLog']

STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('cancel', 'Canceled'),
]

_STATES = {
    'readonly': Eval('state') != 'draft',
}

_DEPENDS=['state']

_STATES_LINE = {
    'readonly': Eval('reconciliation_state') != 'draft',
}

_DEPENDS_LINE=['reconciliation_state']


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
            states=_STATES,
            domain=[
                ('company', '=', Eval('company')),
                ('type', '=', 'bank')
            ], depends=_DEPENDS + ['company'])
    currency = fields.Many2One('currency.currency', 'Currency', required=True,
        states={'readonly': True})
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    number = fields.Char('Number', size=None, readonly=True, select=True)
    reference = fields.Char('Reference', size=None)
    note = fields.Char('Note', size=None,
        states=_STATES, depends=_DEPENDS)
    date = fields.Date('Date', required=True,
        states=_STATES, depends=_DEPENDS)
    date_start = fields.Date('Date', required=True,
        states=_STATES, depends=_DEPENDS)
    date_end = fields.Date('Date', required=True,
        states=_STATES, depends=_DEPENDS)
    lines = fields.One2Many('cash_bank.reconciliation.line', 'reconciliation',
        'Lines', states=_STATES, depends=_DEPENDS)
    state = fields.Selection(STATES, 'State', readonly=True, required=True)
    logs = fields.One2Many('cash_bank.reconciliation.log_action',
        'resource', 'Logs')

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
                    'readonly': Eval('state') != 'draft',
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

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2

    def get_rec_name(self, name):
        if self.number:
            return self.number
        return str(self.id)

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('number',) + tuple(clause[1:])]

    @classmethod
    def create(cls, vlist):
        reconciliations = super(Reconciliation, cls).create(vlist)
        write_log('Created', reconciliations)
        return reconciliations

    @classmethod
    def delete(cls, reconciliations):
        for reconciliation in reconciliations:
            if reconciliation.state not in ['draft']:
                raise UserError(
                    gettext(
                        'cash_bank_reconciliation.reconciliation_delete_draft',
                        reconciliation=reconciliation.rec_name
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
        write_log('Draft', reconciliations)

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, reconciliations):
        write_log('Confirmed', reconciliations)

    @classmethod
    @ModelView.button
    @Workflow.transition('cancel')
    def cancel(cls, reconciliations):
        write_log('Cancelled', reconciliations)

    @classmethod
    @ModelView.button
    def complete_lines(cls, reconciliations):
        pass


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
            ('move.state', '=', 'posted'),
            ('move.company', '=',
                Eval('_parent_reconciliation', {}).get('company', -1)),
        ])
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
        cls._order[0] = ('date', 'DESC')

    @fields.depends('reconciliation', '_parent_reconciliation.currency_digits')
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
            if self.move_line.move.receipt:
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

    def get_receipt(self, name=None):
        if self.move_line and self.move_line.move.receipt:
            return self.move_line.move.receipt.id


class ReconciliationLog(LogActionMixin):
    "Reconciliation Logs"
    __name__ = "cash_bank.reconciliation.log_action" 
    resource = fields.Many2One('cash_bank.reconciliation',
        'Reconciliation', ondelete='CASCADE', select=True)
