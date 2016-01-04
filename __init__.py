# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .shipment import *


def register():
    Pool.register(
        Purchase,
        ShipmentIn,
        ShipmentInReturn,
        module='purchase_from_shipment', type_='model')
    Pool.register(
        ReturnShipmentIn,
        module='purchase_from_shipment', type_='wizard')
