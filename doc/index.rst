Purchase From Shipment
======================

Automatically creates a purchase for a Supplier Shipment (and Supplier Return
Shipment) that is not created from pending moves comming from purchases.

The supplier's "Group Purchase Lines by Product" option controls whether moves
of the same product generate one purchase line or one line per move. It is
enabled by default and also applies to supplier returns. Grouping keeps the
historical behavior: quantities are converted to the purchase unit and summed,
and the first move's price is used when it is non-zero.
