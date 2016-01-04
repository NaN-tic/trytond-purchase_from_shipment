# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval

__all__ = ['ShipmentIn', 'ShipmentInReturn', 'ReturnShipmentIn', 'Purchase']
__metaclass__ = PoolMeta


def set_depends(field_names, instance, Model):
    pool = Pool()

    for fname in field_names:
        if not hasattr(instance, fname):
            default_method = getattr(Model, 'default_%s' % fname, None)
            default_value = default_method() if default_method else None
            field = getattr(Model, fname)
            if default_value and isinstance(field, fields.Many2One):
                TargetModel = pool.get(field.model_name)
                default_value = TargetModel(default_value)
            setattr(instance, fname, default_value)


class CreatePurchaseMixin:

    def create_purchase(self, warehouse=None):
        pool = Pool()
        Uom = pool.get('product.uom')

        product2moves = {}
        product2quantity = {}
        moves_fname = ('incoming_moves' if self.__name__ == 'stock.shipment.in'
            else 'moves')
        for move in getattr(self, moves_fname, []):
            # TODO
            if move.origin:  # already in purchase
                continue

            assert move.product.purchasable
            product2moves.setdefault(move.product, []).append(move)
            product2quantity.setdefault(move.product, 0.0)
            product2quantity[move.product] += Uom.compute_qty(move.uom,
                move.quantity, move.product.purchase_uom)

        if not product2quantity:
            return

        self.raise_user_warning('create_purchase_from_move',
            'create_purchase_from_move', {
                'shipment': self.rec_name,
                'products_wo_origin': ', '.join([p.rec_name
                        for p in product2moves.keys()]),
                })

        sign = -1.0 if self.__name__ == 'stock.shipment.in.return' else 1.0

        purchase = self.get_purchase(warehouse)
        for product, moves in product2moves.iteritems():
            purchase_line = self.get_purchase_line(purchase, product,
                product2quantity[product] * sign, moves)
            if purchase_line:
                purchase.lines.append(purchase_line)
        purchase.save()
        return purchase

    def get_purchase(self, warehouse):
        pool = Pool()
        Address = pool.get('party.address')
        Currency = pool.get('currency.currency')
        Date = pool.get('ir.date')
        PaymentTerm = pool.get('account.invoice.payment_term')
        Purchase = pool.get('purchase.purchase')

        # TODO: search existing purchase?
        purchase = Purchase()
        purchase.invoice_method = 'shipment'
        purchase.company = self.company
        purchase.purchase_date = self.effective_date or Date.today()
        purchase.party = self.supplier
        purchase.payment_term = None
        purchase.lines = []
        set_depends(Purchase.party.on_change, purchase, Purchase)
        changes = purchase.on_change_party()
        if changes.get('currency'):
            purchase.currency = Currency(changes['currency'])
        if changes.get('invoice_address'):
            purchase.invoice_address = Address(changes['invoice_address'])
        if changes.get('payment_term'):
            purchase.payment_term = PaymentTerm(changes['payment_term'])
        purchase.warehouse = warehouse

        return purchase

    def get_purchase_line(self, purchase, product, quantity, moves):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        PurchaseLine = pool.get('purchase.line')
        Tax = pool.get('account.tax')

        line = PurchaseLine()
        line.purchase = purchase
        line.type = 'line'
        line.product = product
        line.unit = product.purchase_uom
        line.unit_price = product.cost_price  # TODO

        set_depends(
            [f for f in PurchaseLine.product.on_change
                if not f.startswith('_parent_purchase')],
            line, PurchaseLine)
        set_depends(
            [f.split('.')[1] for f in PurchaseLine.product.on_change
                if f.startswith('_parent_purchase')],
            line.purchase, Purchase)
        changes = line.on_change_product()

        if changes.get('description'):
            line.description = changes['description']
        else:
            line.description = product.rec_name

        line.taxes = []
        for tax_id in changes['taxes']:
            line.taxes.append(Tax(tax_id))

        if moves[0].unit_price:
            line.unit_price = moves[0].unit_price
        else:
            line.unit_price = changes['unit_price']

        line.moves = moves

        line.quantity = quantity
        return line


class ShipmentIn(CreatePurchaseMixin):
    __name__ = 'stock.shipment.in'

    @classmethod
    def __setup__(cls):
        super(ShipmentIn, cls).__setup__()
        cls._error_messages.update({
                'create_purchase_from_move': (
                    'The Supplier Shipment "%(shipment)s" has movements '
                    'without origin. It will create a purchase for the next '
                    'products: %(products_wo_origin)s.'),
                })

    @classmethod
    def receive(cls, shipments):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')

        purchases = []
        for shipment in shipments:
            purchase = shipment.create_purchase(warehouse=shipment.warehouse)
            if purchase:
                purchases.append(purchase)
        if purchases:
            Purchase.quote(purchases)
            Purchase.confirm(purchases)
            Purchase.process(purchases)
        super(ShipmentIn, cls).receive(shipments)


class ShipmentInReturn(CreatePurchaseMixin):
    __name__ = 'stock.shipment.in.return'
    supplier = fields.Many2One('party.party', 'Supplier',
        states={
            'readonly': (
                ((Eval('state') != 'draft') | Bool(Eval('moves', [0])))
                & Bool(Eval('supplier'))),
            }, required=True,
        depends=['state', 'supplier'])

    @classmethod
    def __setup__(cls):
        super(ShipmentInReturn, cls).__setup__()
        cls._error_messages.update({
                'create_purchase_from_move': (
                    'The Supplier Shipment Return "%(shipment)s" has '
                    'movements without origin. It will create a negative '
                    'purchase for the next products: %(products_wo_origin)s.'),
                })

    @classmethod
    def assign_try(cls, shipments):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')

        purchases = []
        for shipment in shipments:
            purchase = shipment.create_purchase()
            if purchase:
                purchases.append(purchase)
        if purchases:
            Purchase.quote(purchases)
            Purchase.confirm(purchases)
            Purchase.process(purchases)
        super(ShipmentInReturn, cls).assign_try(shipments)


class ReturnShipmentIn:
    __name__ = 'stock.shipment.in.return_shipment'

    def _get_return_shipment(self, shipment_in):
        shipment = super(ReturnShipmentIn, self)._get_return_shipment(
            shipment_in)
        shipment.supplier = shipment_in.supplier
        return shipment


class Purchase:
    __name__ = 'purchase.purchase'

    def _get_return_shipment(self):
        shipment = super(Purchase, self)._get_return_shipment()
        shipment.supplier = self.party
        return shipment
