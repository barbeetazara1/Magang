from odoo import models, fields, api

class HistoryWeaving(models.Model):
    _name = 'history.weaving'

    # name = fields.Char(string='Label dari Field')
    lot_id          = fields.Many2one('stock.production.lot', string='Lot')
    production_id   = fields.Many2one('mrp.production', string='Production')
    tgl_naik_beam   = fields.Datetime(string='Tgl. Naik Beam')
    tgl_turun_beam  = fields.Datetime(string='Tgl. Turun Beam')
    quantity        = fields.Float(string='Quantity')
    
