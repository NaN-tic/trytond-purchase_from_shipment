from trytond.model import fields
from trytond.pool import PoolMeta


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    purchase_from_shipment_group_lines = fields.Boolean(
        'Group Purchase Lines by Product',
        help='Group moves of the same product into one purchase line when '
        'creating purchases from supplier shipments or returns.')

    @staticmethod
    def default_purchase_from_shipment_group_lines():
        return True
