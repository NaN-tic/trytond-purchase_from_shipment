# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import shipment


def register():
    Pool.register(
        shipment.Purchase,
        shipment.ShipmentIn,
        module='purchase_from_shipment', type_='model')
    Pool.register(
        shipment.ShipmentInReturn,
        depends=['stock_shipment_return'],
        module='purchase_from_shipment', type_='model')
    Pool.register(
        shipment.ReturnShipmentIn,
        depends=['stock_shipment_return'],
        module='purchase_from_shipment', type_='wizard')
