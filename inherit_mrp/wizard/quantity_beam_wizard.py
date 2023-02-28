from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta ,datetime
import logging
import json
from odoo.tools import float_compare, float_round, float_is_zero


_logger = logging.getLogger(__name__)
class QuantityBeamWizard(models.TransientModel):
    _name = 'quantity.beam.wizard'

    production_id        = fields.Many2one('mrp.production', string='Production')
    beaming_ids          = fields.Many2many(comodel_name='mrp.beaming', string='Beam')
    lot_id               = fields.Many2one(related='production_id.lot_producing_id', string='Lot')
    product_qty          = fields.Float(string='Lot Quantity', related='production_id.partial_qty')
    # lot_qty              = fields.Float(string='Lot Qty', compute="_compute_lot_qty")
    produce_qty          = fields.Float(string='Produce Quantity')
    production_qty       = fields.Float(string='Production Quantity')
    qty_sisa             = fields.Float(string='Qty Sisa',compute="get_sisa")
    
    
    #Liat Qty Sisa di Open Inventory
    @api.depends('production_qty')
    def get_sisa(self):
        _logger.warning('GET DAPET SISA')
        for line in self:
            line.qty_sisa = line.production_qty - sum(line.production_id.move_finished_ids.mapped('quantity_done'))
            
    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        work_center_cost = 0
        finished_move = self.production_id.move_finished_ids.filtered(lambda x: x.product_id == self.production_id.product_id.id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(lambda x: x.date_end and not x.cost_already_recorded)
                duration = sum(time_lines.mapped('duration'))
                time_lines.write({'cost_already_recorded': True})
                work_center_cost += (duration / 60.0) * work_order.workcenter_id.costs_hour
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                qty_done = finished_move.product_uom._compute_quantity(finished_move.quantity_done, finished_move.product_id.uom_id)
                extra_cost = self.extra_cost * qty_done
                finished_move.price_unit = (sum([-m.stock_valuation_layer_ids.value for m in consumed_moves.sudo()]) + work_center_cost + extra_cost) / qty_done
        return True
    
    #Produce Button di open inventory
    def action_refresh_qty(self):
        for wizard in self:
            moves_not_to_do = wizard.production_id.move_raw_ids.filtered(lambda x: x.state == 'done')
            moves_to_do = wizard.production_id.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            for move in moves_to_do.filtered(lambda m: m.product_qty == 0.0 and m.quantity_done > 0):
                move.product_uom_qty = move.quantity_done
            # MRP do not merge move, catch the result of _action_done in wizard.production_id
            # to get extra moves.
            moves_to_do = moves_to_do._action_done()
            moves_to_do = wizard.production_id.move_raw_ids.filtered(lambda x: x.state == 'done') - moves_not_to_do

            finish_moves = wizard.production_id.move_finished_ids.filtered(lambda m: m.product_id == wizard.production_id.product_id and m.state not in ('done','cancel'))
            # the finish move can already be completed by the workwizard.production_id.
            existing_move_line = finish_moves.move_line_ids.filtered(lambda x: x.lot_id == self.lot_id)
            for qty in self.production_id:
                qty_producing = qty.qty_producing
                qty.write({
                    'qty_producing': qty_producing + self.produce_qty,
                })
            
            if finish_moves:
                for beam in self.production_id.beaming_ids.filtered(lambda x : not x.state):
                    for line in beam.beaming_details_ids:
                        vals_exist = {
                            "name": wizard.production_id.product_id.name,
                            "date": wizard.production_id.date_planned_start,
                            # "quantity_done": self.produce_qty,
                            "company_id": wizard.production_id.company_id.id,
                            "location_dest_id": wizard.production_id.location_id.id,
                            "location_id": 15,
                            "product_id": wizard.production_id.product_id.id,
                            "product_uom": wizard.production_id.product_id.uom_id.id,
                            "product_uom_qty": self.produce_qty,
                            "state": 'done',
                            # "origin": wizard.production_id.name,
                            # "group_id": wizard.production_id.name,
                            } 
                        move_id = self.env['stock.move'].create(vals_exist)
                        vals = {
                                'move_id': move_id.id,
                                'product_id': line.product_id.id,
                                'production_id': self.production_id.id,
                                # 'product_uom_qty': line.quantity,
                                'product_uom_id': line.product_id.uom_id.id,
                                'qty_done': line.quantity,
                                'lot_id': line.lot_id.id,
                                'location_id': finish_moves.location_id.id or 15,
                                'location_dest_id': finish_moves.location_dest_id.id or self.production_id.location_dest_id.id,
                                'company_id': self.production_id.company_id.id,
                            }     
                        self.env['stock.move.line'].create(vals)
                moves_to_finish = wizard.production_id.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
                # finish_moves.product_uom_qty = self.produce_qty + finish_moves.quantity_done
                # # existing_move_line.qty_done = self.production_id.partial_qty + existing_move_line.qty_done
                # for sm in self.production_id.move_finished_ids.filtered(lambda x: x.state != 'done'):
                #     qty_done = sm.quantity_done
                #     sm.write({"quantity_done": qty_done + self.produce_qty})
                #     _logger.warning('='*40)
                #     _logger.warning(sm.id)
                #     _logger.warning('='*40)
                    # moves_to_finish = wizard.production_id.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                    # moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
                    
            else:
                for beam in self.production_id.beaming_ids.filtered(lambda x : not x.state):
                    for line in beam.beaming_details_ids:
                        vals_exist = {
                            "name": wizard.production_id.product_id.name,
                            "date": wizard.production_id.date_planned_start,
                            # "quantity_done": self.produce_qty,
                            "company_id": wizard.production_id.company_id.id,
                            "location_dest_id": wizard.production_id.location_id.id,
                            "location_id": 15,
                            "product_id": wizard.production_id.product_id.id,
                            "product_uom": wizard.production_id.product_id.uom_id.id,
                            "product_uom_qty": self.produce_qty,
                            "state": 'done',
                            # "origin": wizard.production_id.name,
                            # "group_id": wizard.production_id.name,
                            } 
                        move_id = self.env['stock.move'].create(vals_exist)
                        vals = {
                                'move_id': move_id.id,
                                'product_id': line.product_id.id,
                                'production_id': self.production_id.id,
                                # 'product_uom_qty': line.quantity,
                                'product_uom_id': line.product_id.uom_id.id,
                                'qty_done': line.quantity,
                                'lot_id': line.lot_id.id,
                                'location_id': finish_moves.location_id.id or 15,
                                'location_dest_id': finish_moves.location_dest_id.id or self.production_id.location_dest_id.id,
                                'company_id': self.production_id.company_id.id,
                            }     
                        self.env['stock.move.line'].create(vals)
                moves_to_finish = wizard.production_id.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
            
            
            # if existing_move_line:
            #     finish_moves.product_uom_qty = self.produce_qty + finish_moves.quantity_done
            #     # existing_move_line.qty_done = self.production_id.partial_qty + existing_move_line.qty_done
            #     for sm in self.production_id.move_finished_ids.filtered(lambda x: x.state != 'done'):
            #         qty_done = sm.quantity_done
            #         sm.write({"quantity_done": qty_done + self.produce_qty})
            #         _logger.warning('='*40)
            #         _logger.warning(sm.id)
            #         _logger.warning('='*40)
                    # moves_to_finish = wizard.production_id.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                    # moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
                
            # else:
            #     for beam in self.production_id.beaming_ids:
            #         for line in beam.beaming_details_ids:
            #             vals = {
            #                     'move_id': finish_moves.id,
            #                     'product_id': line.product_id.id,
            #                     'production_id': self.production_id.id,
            #                     'product_uom_qty': line.quantity,
            #                     'product_uom_id': line.product_id.uom_id.id,
            #                     'qty_done': line.quantity,
            #                     'lot_id': line.lot_id.id,
            #                     'location_id': finish_moves.location_id.id or 15,
            #                     'location_dest_id': finish_moves.location_dest_id.id or self.production_id.location_dest_id.id,
            #                     'company_id': self.production_id.company_id.id,
            #                 }     
            #             self.env['stock.move.line'].create(vals)
            # else:
            #     vals = {
            #             'move_id': finish_moves.id,
            #             'product_id': finish_moves.product_id.id or self.production_id.product_id.id,
            #             'production_id': self.production_id.id,
            #             'product_uom_qty': self.produce_qty,
            #             'product_uom_id': self.production_id.product_uom_id.id,
            #             'qty_done': self.produce_qty,
            #             'lot_id': self.lot_id.id,
            #             'location_id': finish_moves.location_id.id or 15,
            #             'location_dest_id': finish_moves.location_dest_id.id or self.production_id.location_dest_id.id,
            #             'company_id': self.production_id.company_id.id,
            #         }     
            #     self.env['stock.move.line'].create(vals)
            if not finish_moves.quantity_done:
                finish_moves.quantity_done = float_round(wizard.production_id.qty_producing - wizard.production_id.qty_produced, precision_rounding=wizard.production_id.product_uom_id.rounding, rounding_method='HALF-UP')
                finish_moves.move_line_ids.lot_id = wizard.production_id.lot_producing_id
            wizard._cal_price(moves_to_do)

            wizard.production_id.action_assign()
            consume_move_lines = moves_to_do.mapped('move_line_ids')
            wizard.production_id.move_finished_ids.move_line_ids.consume_line_ids = [(6, 0, consume_move_lines.ids)]
            for beam in self.beaming_ids.filtered(lambda x:not x.state):
                beam.write({"state":True})
            #INI HARUS DI KONDISIKAN LAGI YANG PRODUCE_QTY > QTY SISA
            _logger.warning('='*40)
            _logger.warning('='*40)
            _logger.warning("CEK PRODUCE_QTY > QTY SISA")
            _logger.warning(wizard.produce_qty)
            _logger.warning('='*40)
            _logger.warning('='*40)
            if wizard.qty_sisa < 0 :
                raise UserError('Produce Qty must be less than Qty Sisa')
            elif wizard.production_id.partial_qty > wizard.production_id.product_qty:
                raise UserError('Partial Qty must be less than Product Qty')
            # elif wizard.production_id.partial_qty == wizard.production_id.product_qty:
            #     moves_to_finish = wizard.production_id.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            #     moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
            

            
        return True
        
        
       
