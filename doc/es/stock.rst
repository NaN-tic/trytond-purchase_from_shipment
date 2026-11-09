#:inside:stock/stock:section:recepcion_mercaderia#

Recibir (o devolver) mercancía sin compra previa
------------------------------------------------

Si se recibe mercancía de la que no se ha hecho un pedido previamente, habrá
que crear un |shipment_in| y sus |incoming_moves| manualmente.

Al procesar el albarán se creará y procesará automáticamente una compra con los 
productos recibidos, generando la factura correspondiente (excepto si el |invoice_method| por defeto es *Manual*.)

Si se hace un |shipment_in_return| el comportamiento será el mismo siendo
negativas las cantidades de la compra generada.

La opción «Agrupar líneas de compra por producto», en la pestaña Proveedor del
tercero, está activada por defecto. Agrupa los movimientos del mismo producto
en una línea de compra, sumando sus cantidades en la unidad de compra y tomando
el precio del primer movimiento cuando no es cero, como en el comportamiento
original. Si se desactiva, se crea una línea de compra por movimiento. La opción
se aplica tanto a recepciones como a devoluciones sin compra previa.

.. |shipment_in| model:: stock.shipment.in
.. |incoming_moves| field:: stock.shipment.in/incoming_moves
.. |invoice_method| field:: purchase.purchase/invoice_method
.. |shipment_in_return| model:: stock.shipment.in.return
