
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta ,datetime
import logging
import json
from odoo.tools import float_compare, float_round, float_is_zero
_logger = logging.getLogger(__name__)

class ProduksiWeaving(models.Model):
    _name = 'produksi.weaving'

    beam_id             = fields.Many2one('mrp.beaming', string="Kartu Beam")
    machine_id          = fields.Many2one('mrp.machine')
    date                = fields.Date(string='Date', default=fields.Date.today())
    rpm                 = fields.Float(string='RPM')
    kd_operator         = fields.Many2one('hr.employee', string='Kd Operator')
    shift               = fields.Selection([("A","A"),("B","B"),("C","C"),("D","D")], string='Shift', store=True)
    counter_awal        = fields.Float(string='Counter Awal')
    counter_akhir       = fields.Float(string='Counter Akhir')
    counter_pjg         = fields.Float(string='Counter Meter')
    quantity            = fields.Float(string='Quantity',compute="_compute_quantity")
    state               = fields.Selection([("draft","Draft"),("confirm","Confirm"),("done","Done")], string="State", default="draft")
    weaving_details     = fields.One2many('produksi.weaving.details', 'weaving_id', string='Weaving Details')
    beam_detail_id      = fields.Many2one('mrp.beaming.details',string="Beam Details")
    lot_id              = fields.Many2one(related='beam_detail_id.lot_id', string='Lot')
    
    @api.depends('counter_akhir','counter_awal')
    def _compute_quantity(self):
        for a in self:
            a.quantity = a.counter_akhir - a.counter_awal
            
    def button_confirm(self):
        for me in self:
            me.write({'state':'confirm'})
    def button_mark_as_done(self):
        for me in self:
            me.write({'state':'done'})
    def set_to_draft(self):
        for me in self:
            me.write({'state':'draft'})
class ProduksiWeavingDetails(models.Model):
    _name = 'produksi.weaving.details'
    
    weaving_id          = fields.Many2one('produksi.weaving', string='Weaving ID')
    lot_id              = fields.Many2one('stock.production.lot', string="Lot")
    quantity            = fields.Float(string="Quantity")
