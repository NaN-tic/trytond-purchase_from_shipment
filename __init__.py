# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .shipment import *


def register():
    Pool.register(
        ShipmentIn,
        module='purchase_from_shipment', type_='model')
