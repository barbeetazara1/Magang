from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta ,datetime
import logging
import json
from odoo.tools import float_compare, float_round, float_is_zero
_logger = logging.getLogger(__name__)

class InspectGreige(models.Model):
    _name = 'inspect.greige'

    production_id           = fields.Many2one('mrp.production', string="Production Id", required=True)
    production_type         = fields.Many2one(related="production_id.type_id", string="Production Type")
    jmlh_roll               = fields.Float(string="Jmlh Roll")
    beam_id                 = fields.Many2one('mrp.beaming', string="Beam ID")
    state                   = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('done', 'Done')], string="State")
    product_id              = fields.Many2one('product.product', string="Product")
    tot_panjang             = fields.Float(string="Tot Panjang")
    uom_id                  = fields.Many2one(related="product_id.uom_id", string="UOM")
    location_id             = fields.Many2one('stock.location', string='Location')
    inspect_detail_ids      = fields.One2many('inspect.details.greige', 'inspect_id', string='Inspect Detail')
    
    
class InspectGreige(models.Model):
    _name = 'inspect.details.greige'
    
    inspect_id            = fields.Many2one('inspect.greige', string="Inspect ID")
    lot_id                = fields.Many2one('stock.production.lot', string="Lot")    
    quantity              = fields.Float(string="Quantity")
    product_id            = fields.Many2one('product.product', string="Product")
    uom_id                = fields.Many2one(related="product_id.uom_id", string="UOM")
    grade_id              = fields.Many2one('makloon.grade', string='Grade')
    defect_ids            = fields.Many2many('product.defect', string='Defect')
    shift                 = fields.Selection([("A","A"),("B","B"),("C","C"),("D","D")], string='Shift', store=True)
    employee_id           = fields.Many2one('hr.employee', string='Kd Operator')
