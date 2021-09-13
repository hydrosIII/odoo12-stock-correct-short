# odoo12-stock-correct-short
Odoo module that works with stock correction to run daily

This is an odoo module to correct an error in odoo 12 because in the table stock_qty the stock is wrongly written. So we have to recalculate the stock from the stock_moves.

This script is to be used with odoo-stock-correct from my other repo https://github.com/hydrosIII/odoo12-stock-correction


Actually this script only checks the difference in stock_qty from the last run of the script, calculates the difference and writes in the table stock_qty.  This is thought to be run on a daily basis. After the first run of the odoo-stock-correct module, this script will only take a few minutes to run. Sou you can run it at night every night.


The original author of this script it ittplabs https://github.com/itpp-labs @yelizariev, but it was written on my comission. 


GPL v2 license.
