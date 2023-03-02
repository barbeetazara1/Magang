from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta ,datetime
import logging
import json
from odoo.tools import float_compare, float_round, float_is_zero
_logger = logging.getLogger(__name__)

class ProduksiWeaving(models.Model):
    _name = 'produksi.weaving'

    production_id       = fields.Many2one('mrp.production', string='Production', domain=[('type_id', '=', 3)])
    greige_id           = fields.Many2one(related='production_id.product_id', string='Greige')
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
    state               = fields.Selection([("draft","Draft"),("confirm","Confirm"),("progress","In Progress"),("done","Done")], string="State", default="draft")
    weaving_details     = fields.One2many('produksi.weaving.details', 'weaving_id', string='Weaving Details')
    beam_detail_id      = fields.Many2one('mrp.beaming.details',string="Beam Details")
    lot_id              = fields.Many2one(related='beam_detail_id.lot_id', string='Lot')
    move_finished_ids   = fields.One2many('stock.move', 'weaving_id', string="Move Finished")
    lot_weaving_id      = fields.Many2one('stock.production.lot',string="Lot Weaving")
    
    @api.depends('counter_akhir','counter_awal')
    def _compute_quantity(self):
        for a in self:
            a.quantity = a.counter_akhir - a.counter_awal
            
    def button_confirm(self):
        # Majuin State MO WEAVING ke confirmed
        self.production_id.action_confirm()
        for me in self:
            me.write({'state':'confirm'})
    def button_mark_as_done(self):
        for me in self:
            me.write({'state':'done'})
    def set_to_draft(self):
        for me in self:
            me.write({'state':'draft'})
            
    def create_lot(self):
        # Create Lot
        lot_id = self.env['stock.production.lot'].create({
            'production_id': self.production_id.id,
            'product_id': self.production_id.product_id.id,
            'product_uom_id' : self.production_id.product_id.uom_id.id,
            'production_type_id': 3,
            'location_id': self.production_id.location_id.id,
        })
        finish_moves = self.production_id.move_finished_ids.filtered(lambda m: m.product_id == self.production_id.product_id and m.state not in ('done','cancel'))
        stock_id = []
        if finish_moves:
            vals = {
                    # 'move_id': move_line_id.id,
                    "product_id" : self.production_id.product_id.id,
                    'production_id': self.production_id.id,
                    'product_uom_id' : self.production_id.product_id.uom_id.id,
                    'qty_done': self.quantity,
                    'lot_id': lot_id.id,
                    'location_id': 15,
                    'location_dest_id': self.production_id.location_dest_id.id,
                    'company_id': self.production_id.company_id.id,
                }
            move_id = {
                    "name": self.lot_id.product_id.name,
                    "date": self.date,
                    "company_id": self.lot_id.company_id.id,
                    "location_dest_id": self.production_id.location_dest_id.id,
                    "location_id": 15,
                    "production_id": self.production_id.id,
                    "product_id": self.production_id.product_id.id,
                    "product_uom": self.production_id.product_id.uom_id.id,
                    "product_uom_qty": self.quantity,
                    "state": 'done',
                    "move_line_ids": [(0, 0,vals)]
                    } 
            move_line_id = self.env['stock.move'].create(move_id)
            stock_id.append(move_line_id.id) 
            # Untuk write move_finished_ids di weaving
            # self.production_id.create({
            #     "move_finished_ids": [(6,0,stock_id)] 
            # })
            _logger.warning('='*40)
            _logger.warning('MESSAGE')
            _logger.warning(move_line_id)
            _logger.warning('='*40)
            moves_to_finish = self.production_id.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
            # cek isi lot
            _logger.warning('='*40)
            _logger.warning('MESSAGE')
            _logger.warning(lot_id)
            _logger.warning('='*40)
            self.lot_weaving_id = lot_id.id
            return lot_id
        else :
            vals = {
                    # 'move_id': move_line_id.id,
                    "product_id" : self.production_id.product_id.id,
                    'production_id': self.production_id.id,
                    'product_uom_id' : self.production_id.product_id.uom_id.id,
                    'qty_done': self.quantity,
                    'lot_id': lot_id.id,
                    'location_id': 15,
                    'location_dest_id': self.production_id.location_dest_id.id,
                    'company_id': self.production_id.company_id.id,
                }
            move_id = {
                    "name": self.lot_id.product_id.name,
                    "date": self.date,
                    "company_id": self.lot_id.company_id.id,
                    "location_dest_id": self.production_id.location_dest_id.id,
                    "location_id": 15,
                    "production_id": self.production_id.id,
                    "product_id": self.production_id.product_id.id,
                    "product_uom": self.production_id.product_id.uom_id.id,
                    "product_uom_qty": self.quantity,
                    "state": 'done',
                    "move_line_ids": [(0, 0,vals)]
                    } 
            move_line_id = self.env['stock.move'].create(move_id)
            stock_id.append(move_line_id.id) 
            # Untuk write move_finished_ids di weaving
            self.production_id.write({
                "move_finished_ids": [(6,0,stock_id)] 
            })
            # cek isi move line
            _logger.warning('='*40)
            _logger.warning('MESSAGE')
            _logger.warning(move_line_id)
            _logger.warning('='*40)
            moves_to_finish = self.production_id.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
            # cek isi lot
            _logger.warning('='*40)
            _logger.warning('MESSAGE')
            _logger.warning(lot_id)
            _logger.warning('='*40)
            
            _logger.warning('='*40)
            _logger.warning('MESSAGE')
            _logger.warning(vals)
            _logger.warning('='*40)
            self.lot_weaving_id = lot_id.id
            
            # Untuk Qty Producing
            product_qty_stock = self.production_id.move_finished_ids.quantity_done
            for qty in self.production_id:
                qty_producing = qty.qty_producing
                qty.write({
                    'qty_producing': qty_producing + product_qty_stock
                })
            # Majuin State Ke Progress
            self.write({
                'state' : 'progress'
            })
            return lot_id
        
class ProduksiWeavingDetails(models.Model):
    _name = 'produksi.weaving.details'
    
    weaving_id          = fields.Many2one('produksi.weaving', string='Weaving ID')
    lot_id              = fields.Many2one('stock.production.lot', string="Lot")
    quantity            = fields.Float(string="Quantity")
