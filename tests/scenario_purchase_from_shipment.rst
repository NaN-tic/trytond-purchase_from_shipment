===============================
Purchase From Shipment Scenario
===============================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install purchase_from_shipment::

    >>> Module = Model.get('ir.module.module')
    >>> purchase_module, = Module.find([
    ...         ('name', '=', 'purchase_from_shipment'),
    ...         ])
    >>> Module.install([purchase_module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> Journal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')
    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('name', '=', 'Main Cash'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> warehouse_loc, = Location.find([('code', '=', 'WH')])
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> input_loc, = Location.find([('code', '=', 'IN')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('5')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term.save()

Receive 5 products::

    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment_in = ShipmentIn()
    >>> shipment_in.planned_date = today
    >>> shipment_in.supplier = supplier
    >>> shipment_in.company = company
    >>> incoming_move = shipment_in.incoming_moves.new()
    >>> incoming_move.product = product
    >>> incoming_move.quantity = 2
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = shipment_in.warehouse_input
    >>> incoming_move = shipment_in.incoming_moves.new()
    >>> incoming_move.product = product
    >>> incoming_move.quantity = 3
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = shipment_in.warehouse_input
    >>> shipment_in.save()
    >>> shipment_in.click('receive') # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserWarning: ...
    >>> Model.get('res.user.warning')(user=config.user,
    ...     name='create_purchase_from_move', always=True).save()
    >>> shipment_in.click('receive')
    >>> shipment_in.click('done')
    >>> shipment_in.reload()
    >>> shipment_in.state
    u'done'

Check purchase is created and is processing::

    >>> Purchase = Model.get('purchase.purchase')
    >>> PurchaseLine = Model.get('purchase.line')
    >>> all(isinstance(m.origin, PurchaseLine)
    ...     for m in shipment_in.incoming_moves)
    True
    >>> purchases = Purchase.find([])
    >>> len(purchases)
    1
    >>> sorted([l.quantity for l in purchases[0].lines])
    [5.0]
    >>> len(purchases[0].shipments)
    1
    >>> purchases[0].shipments[0] == shipment_in
    True
    >>> purchases[0].state
    u'processing'
    >>> purchases[0].shipment_state
    u'received'

Return 2 products::

    >>> ShipmentInReturn = Model.get('stock.shipment.in.return')
    >>> shipment_in_return = ShipmentInReturn()
    >>> shipment_in_return.planned_date = today
    >>> shipment_in_return.supplier = supplier
    >>> shipment_in_return.company = company
    >>> shipment_in_return.from_location = storage_loc
    >>> shipment_in_return.to_location = supplier_loc
    >>> move = shipment_in_return.moves.new()
    >>> move.product = product
    >>> move.quantity = 2
    >>> move.from_location = storage_loc
    >>> move.to_location = supplier_loc
    >>> shipment_in_return.save()
    >>> shipment_in_return.click('wait')
    >>> shipment_in_return.click('assign_try')
    >>> shipment_in_return.click('done')
    >>> shipment_in_return.reload()
    >>> shipment_in_return.state
    u'done'

Check purchase is created and is processing::

    >>> Purchase = Model.get('purchase.purchase')
    >>> PurchaseLine = Model.get('purchase.line')
    >>> all(isinstance(m.origin, PurchaseLine)
    ...     for m in shipment_in_return.moves)
    True
    >>> purchases = Purchase.find([])
    >>> len(purchases)
    2
    >>> sorted([l.quantity for l in purchases[0].lines])
    [-2.0]
    >>> len(purchases[0].shipment_returns)
    1
    >>> purchases[0].shipment_returns[0] == shipment_in_return
    True
    >>> purchases[0].state
    u'processing'
    >>> purchases[0].shipment_state
    u'received'
