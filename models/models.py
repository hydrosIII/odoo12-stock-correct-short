# Copyright 2020 Anvar Kildebekov <https://it-projects.info/team/fedoranvar>
# License MIT (https://opensource.org/licenses/MIT).

from odoo import api, fields, models

class StockQuantBalance(models.Model):

    _inherit = 'stock.quant'

    def turn_wdb(self):
        import wdb;wdb.set_trace()

    @api.constrains('product_id')
    def check_product_id(self):
        pass

    def action_balance_qty(self):
        sqlscrpt_products=(
"""
/*Gets the current entries in a certain location*/
WITH incoming as (
SELECT product_id, Sum(qty_done)
FROM stock_move_line
WHERE location_dest_id=(%s) and state='done'
GROUP BY product_id
), outgoing AS
/* gets the current outgoing stock from one determined location*/
(SELECT product_id, Sum(qty_done)
FROM stock_move_line
WHERE location_id=(%s) and state='done'
GROUP BY product_id
/*puts the quantity of stock incoming aside from its outgoing quantity*/
), incomingvsoutgoing AS (
SELECT incoming.product_id AS id, incoming.sum AS incoming, outgoing.sum AS outgoing
FROM incoming,outgoing
where incoming.product_id = outgoing.product_id 
/*Gets the difference of the incoming stock vs the outgoing stock to get the difference and supposed stock in that location*/
), comparison AS
(select id, Sum(incoming) AS quant_incoming, Sum(outgoing) AS quant_outgoing, Sum(incoming-outgoing) AS supposed_stock
from  incomingvsoutgoing
group by id
/*Get the quantity in that location from the stock_quant table, this table is used by odoo to display the current stock*/
), stock_qty AS 
( SELECT product_id, Sum(quantity) AS quant_stock_ontable
FROM stock_quant
WHERE location_id=(%s)
GROUP BY product_id
/*Gets side by side the calculated supposed quantity and the quantity from the stock_quant*/
), supposed_stock_vs_stock_on_table AS
(SELECT id,quant_incoming,quant_outgoing, supposed_stock, quant_stock_ontable
from comparison, stock_qty
WHERE comparison.id=stock_qty.product_id
/*substracts the difference of supposed stock - quant_stock_on_table to get the difference*/
), results AS 
(select supposed_stock_vs_stock_on_table.id, Sum(supposed_stock_vs_stock_on_table.quant_incoming) AS  quant_incoming, Sum(supposed_stock) AS supposed_stock, Sum(supposed_stock_vs_stock_on_table.quant_outgoing) AS quant_outgoing, Sum(supposed_stock_vs_stock_on_table.supposed_stock-supposed_stock_vs_stock_on_table.quant_stock_ontable) AS difference, Sum(quant_stock_ontable) AS quant_stock_ontable
from supposed_stock_vs_stock_on_table
group by id
/*adds the product barcode*/
), results_w_code AS (
select results.id, results.quant_incoming, results.quant_outgoing, results.difference, supposed_stock, default_code, product_tmpl_id,  quant_stock_ontable
from results, product_product
where results.id = product_product.id)
/*prints the results, adding the product name, and selecting just the products where the supposed stock is not equal to the stock in stock_quant table*/
SELECT results_w_code.id as product_database_id, results_w_code.quant_incoming, results_w_code.quant_outgoing, supposed_stock, results_w_code.quant_stock_ontable, difference, name as corrupted_product_name, product_template.default_code AS corrupted_product_code
from results_w_code, product_template
WHERE results_w_code.product_tmpl_id = product_template.id 
AND difference IS NOT NULL
AND difference <> 0
ORDER BY difference DESC;
"""
                )
        sqlscrpt_moves=(
                "select product_id,location_id,location_dest_id,qty_done,lot_id "
                "from stock_move_line "
                "where state='done' and product_id=(%s) and (location_id=(%s) or location_dest_id=(%s));"
                )

        # check wrong quantities over all warehouses locations
        for loc in self.env['stock.location'].search([]):
            
            loc_id = loc.id
            self._cr.execute(sqlscrpt_products, [(loc_id,),
                                                  (loc_id,),
                                                  (loc_id,)])
            prdcts = self._cr.dictfetchall()

            if prdcts:
                # loop over all products in location
                for prdct in prdcts:

                    prdct_id = prdct.get('product_database_id')


                    # clean wrong quantity of product
                    self.search([
                                  ('location_id','=',loc_id),
                                  ('product_id','=', prdct_id)
                    ]).write({ 'quantity': 0 })
            
                    # balance quants
                    self._cr.execute(sqlscrpt_moves,[
                                                    (prdct_id,),
                                                    (loc_id,),
                                                    (loc_id,),
                                                    ])
                    moves = self._cr.dictfetchall()

                    #check all stockmoves of product (lot) in location
                    for move in moves:
                        lot_id = move['lot_id']

                        qty_done = move['qty_done']
                        if (move['location_id']==loc_id):
                            qty_done *= -1

                        # get stock_quant obj
                        sqrcrd = self.search([
                                ('product_id','=', prdct_id),
                                ('location_id','=', loc_id),
                                ('lot_id','=', lot_id)
                                ], limit=1)


                        if len(sqrcrd) == 0:
                            self.create({
                                'product_id': prdct_id,
                                'location_id': loc_id,
                                'lot_id' : lot_id,
                                'quantity': qty_done
                                })
                        else:
                            sqrcrd.write({
                                'quantity': sqrcrd.quantity + qty_done 
                                })

        print('balance done')

