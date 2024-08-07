import datetime
import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.exceptions import UserWarning
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        today = datetime.date.today()

        # Install purchase_from_shipment
        config = activate_modules(['purchase_from_shipment', \

            'stock_shipment_return'])

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create journals
        Journal = Model.get('account.journal')
        cash_journal, = Journal.find([('type', '=', 'cash')])
        cash_journal.save()

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()

        # Get stock locations
        Location = Model.get('stock.location')
        warehouse_loc, = Location.find([('code', '=', 'WH')])
        supplier_loc, = Location.find([('code', '=', 'SUP')])
        input_loc, = Location.find([('code', '=', 'IN')])
        storage_loc, = Location.find([('code', '=', 'STO')])

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create account categories
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()
        account_category_tax, = account_category.duplicate()
        account_category_tax.supplier_taxes.append(tax)
        account_category_tax.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.purchasable = True
        template.list_price = Decimal('10')
        template.cost_price_method = 'fixed'
        template.account_category = account_category_tax
        template.save()
        product.template = template
        product.cost_price = Decimal('5')
        product.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Receive 5 products
        ShipmentIn = Model.get('stock.shipment.in')
        shipment_in = ShipmentIn()
        shipment_in.planned_date = today
        shipment_in.supplier = supplier
        shipment_in.company = company
        incoming_move = shipment_in.incoming_moves.new()
        incoming_move.product = product
        incoming_move.quantity = 2
        incoming_move.from_location = supplier_loc
        incoming_move.to_location = shipment_in.warehouse_input
        incoming_move.unit_price = Decimal(0)
        incoming_move.currency = company.currency
        incoming_move = shipment_in.incoming_moves.new()
        incoming_move.product = product
        incoming_move.quantity = 3
        incoming_move.from_location = supplier_loc
        incoming_move.to_location = shipment_in.warehouse_input
        incoming_move.unit_price = Decimal(0)
        incoming_move.currency = company.currency
        shipment_in.save()

        with self.assertRaises(UserWarning):
            shipment_in.click('receive')

        Model.get('res.user.warning')(user=config.user,
                                      name='create_purchase_from_move_%s' %
                                      shipment_in.id,
                                      always=True).save()
        shipment_in.click('receive')
        shipment_in.click('do')
        shipment_in.reload()
        self.assertEqual(shipment_in.state, 'done')

        # Check purchase is created and is processing
        Purchase = Model.get('purchase.purchase')
        PurchaseLine = Model.get('purchase.line')
        self.assertEqual(
            all(
                isinstance(m.origin, PurchaseLine)
                for m in shipment_in.incoming_moves), True)
        purchases = Purchase.find([])
        self.assertEqual(len(purchases), 1)
        self.assertEqual(sorted([l.quantity for l in purchases[0].lines]),
                         [5.0])
        self.assertEqual(len(purchases[0].shipments), 1)
        self.assertEqual(purchases[0].shipments[0], shipment_in)
        self.assertEqual(purchases[0].state, 'processing')
        self.assertEqual(purchases[0].shipment_state, 'received')

        # Return 2 products
        ShipmentInReturn = Model.get('stock.shipment.in.return')
        shipment_in_return = ShipmentInReturn()
        shipment_in_return.planned_date = today
        shipment_in_return.supplier = supplier
        shipment_in_return.company = company
        shipment_in_return.from_location = storage_loc
        shipment_in_return.to_location = supplier_loc
        move = shipment_in_return.moves.new()
        move.product = product
        move.quantity = 2
        move.from_location = storage_loc
        move.to_location = supplier_loc
        move.unit_price = Decimal(0)
        move.currency = company.currency
        shipment_in_return.save()
        shipment_in_return.click('wait')
        Model.get('res.user.warning')(user=config.user,
                                      name='create_purchase_from_move_%s' %
                                      shipment_in_return.id,
                                      always=True).save()
        shipment_in_return.click('assign_try')
        shipment_in_return.click('do')
        shipment_in_return.reload()
        self.assertEqual(shipment_in_return.state, 'done')

        # Check purchase is created and is processing
        Purchase = Model.get('purchase.purchase')
        PurchaseLine = Model.get('purchase.line')
        self.assertEqual(
            all(
                isinstance(m.origin, PurchaseLine)
                for m in shipment_in_return.moves), True)
        purchases = Purchase.find([])
        self.assertEqual(len(purchases), 2)
        self.assertEqual(sorted([l.quantity for l in purchases[0].lines]),
                         [-2.0])
        self.assertEqual(len(purchases[0].shipment_returns), 1)
        self.assertEqual(purchases[0].shipment_returns[0], shipment_in_return)
        self.assertEqual(purchases[0].state, 'processing')
        self.assertEqual(purchases[0].shipment_state, 'received')

        # Return some products using the wizard
        return_shipment = Wizard('stock.shipment.in.return_shipment',
                                 [shipment_in])
        return_shipment.execute('return_')
        returned_shipment, = ShipmentInReturn.find([
            ('state', '=', 'draft'),
        ])
        self.assertEqual(sorted([m.quantity for m in returned_shipment.moves]),
                         [2.0, 3.0])
        returned_shipment.moves.remove(returned_shipment.moves[-1])
        returned_shipment.moves[0].quantity = 1
        returned_shipment.save()
        self.assertEqual(sorted([x.quantity for x in returned_shipment.moves]),
                         [1.0])

        # Process returning shipment
        returned_shipment.click('wait')
        Model.get('res.user.warning')(user=config.user,
                                      name='create_purchase_from_move_%s' %
                                      returned_shipment.id,
                                      always=True).save()
        returned_shipment.click('assign_try')
        returned_shipment.click('do')
        returned_shipment.reload()
        self.assertEqual(returned_shipment.state, 'done')

        # Check purchase is created and is processing
        self.assertEqual(
            all(
                isinstance(m.origin, PurchaseLine)
                for m in returned_shipment.moves), True)
        purchase = returned_shipment.moves[0].origin.purchase
        self.assertEqual(purchase.shipment_returns[0], returned_shipment)
        self.assertEqual(purchase.state, 'processing')
        self.assertEqual(purchase.shipment_state, 'received')
