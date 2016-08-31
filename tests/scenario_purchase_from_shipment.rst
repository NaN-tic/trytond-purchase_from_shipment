===============================
Purchase From Shipment Scenario
===============================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install purchase_from_shipment::

    >>> Module = Model.get('ir.module')
    >>> purchase_module, = Module.find([
    ...         ('name', '=', 'purchase_from_shipment'),
    ...         ])
    >>> Module.install([purchase_module.id], config.context)
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> party = company.party

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create journals::

    >>> Journal = Model.get('account.journal')
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = account_cash
    >>> cash_journal.debit_account = account_cash
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

    >>> payment_term = create_payment_term()
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
    True
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

Install stock_shipment_return (extra depends)::

    >>> Module = Model.get('ir.module')
    >>> shipment_return_module, = Module.find([
    ...         ('name', '=', 'stock_shipment_return'),
    ...         ])
    >>> Module.install([shipment_return_module.id], config.context)
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Return some products using the wizard::

    >>> return_shipment = Wizard('stock.shipment.in.return_shipment',
    ...     [shipment_in])
    >>> return_shipment.execute('return_')
    >>> returned_shipment, = ShipmentInReturn.find([
    ...     ('state', '=', 'draft'),
    ...     ])
    >>> sorted([m.quantity for m in returned_shipment.moves])
    [2.0, 3.0]
    >>> returned_shipment.moves.remove(returned_shipment.moves[-1])
    >>> returned_shipment.moves[0].quantity = 1
    >>> returned_shipment.save()
    >>> sorted([x.quantity for x in returned_shipment.moves])
    [1.0]

Process returning shipment::

    >>> returned_shipment.click('wait')
    >>> returned_shipment.click('assign_try')
    True
    >>> returned_shipment.click('done')
    >>> returned_shipment.reload()
    >>> returned_shipment.state
    u'done'

Check purchase is created and is processing::

    >>> all(isinstance(m.origin, PurchaseLine)
    ...     for m in returned_shipment.moves)
    True
    >>> purchase = returned_shipment.moves[0].origin.purchase
    >>> purchase.shipment_returns[0] == returned_shipment
    True
    >>> purchase.state
    u'processing'
    >>> purchase.shipment_state
    u'received'
