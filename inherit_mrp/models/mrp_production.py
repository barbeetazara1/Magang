from itertools import product
from multiprocessing.dummy import active_children
from operator import length_hint
from odoo import models, fields, api, _ ,SUPERUSER_ID
from odoo.addons.mrp.models.mrp_production import MrpProduction as Mrp
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
import logging
from datetime import timedelta,time,datetime
import math
import json
from ast import literal_eval
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    
    @api.depends('product_id','workorder_ids','workorder_ids.state', 'workorder_id')
    def _work_in_progress(self):
        for production in self:
            if production.workorder_ids and production.type_id.id == 2 and production.state == 'progress' or production.state == 'to_close':
                # workcenter_on_progress = production.workorder_ids.filtered(lambda x:x.state == 'progress').mapped('workcenter_id')
                # workcenter_finished    = production.workorder_ids.filtered(lambda x:x.state == 'done').mapped('workcenter_id')
                workorder = production.workorder_ids.filtered(lambda x:x.state == 'progress')
                workorder_finished    = production.workorder_ids.filtered(lambda x:x.state == 'done').sorted(lambda workorder: workorder.name)
                
                if len(workorder) >= 1:
                    # production.workcenter_on_progress = workcenter_on_progress[0].id
                    production.workorder_id = workorder[0].id
                elif len(workorder) == 0  and len(workorder_finished) > 1:
                    # production.workcenter_on_progress = workcenter_finished[len(workcenter_finished) - 1].id
                    print('_work_in_progress=======', workorder_finished)
                    production.workorder_id = workorder_finished[len(workorder_finished) - 1].id
                elif len(workorder) == 0  and len(workorder_finished) == 0:
                    production.workcenter_on_progress = False
                    production.workorder_id = False
                
            else:
                production.workcenter_on_progress = False
                production.workorder_id = False

    @api.depends('product_id','workorder_ids','workorder_ids.qc_pass', 'workorder_id')
    def _get_qc_pass(self):
        for production in self:
            if production.workorder_ids and production.type_id.id == 2 and production.state == 'progress' or production.state == 'to_close':
                # workcenter_finished    = production.workorder_ids.filtered(lambda x:x.state == 'done').mapped('workcenter_id')
                wo_finished    = production.workorder_ids.filtered(lambda x:x.state == 'done')
                wo_qc_on_finished      = production.workorder_ids.filtered(lambda x:x.state == 'done').sorted(lambda workorder: workorder.name).mapped('qc_pass')
                if len(wo_finished) >= 1:
                    print('wo_qc_on_finished', wo_qc_on_finished)
                    qc_passed =  wo_qc_on_finished[len(wo_qc_on_finished)-1]
                    production.qc_pass = qc_passed
                        
                elif len(wo_finished) == 0:
                    production.qc_pass = ''
                    
                
            else:
                production.workcenter_on_progress = False
                production.qc_pass = ''
        
        
        
    #order
    sale_id                    = fields.Many2one('sale.order', string='Sale')
    partner_id                 = fields.Many2one( related="sale_id.partner_id", string='Customer')
    sale_line_id               = fields.Many2one('sale.order.line', string='sale Order Line')
    process_type_id            = fields.Many2one(related='sale_line_id.process_type_id', string='Kategori Resep', store=False,)
    td_id                      = fields.Many2one('test.development', related='bom_id.td_id', string='TD')
    process_type               = fields.Many2one('master.opc',string='Process Type', )
    process_category_id        = fields.Many2one('process.chemical.type',string='Kategori Resep', compute="_compute_kategori_resep")
    labdip_id                  = fields.Many2one('labdip', related='bom_id.labdip_id', string='Labdip')
    chemical_process_type_id   = fields.Many2one( related='labdip_id.chemical_process_type_id', string='Process Type', store=True,)
    qc_pass                    = fields.Char(string='QC Pass' ,compute="_get_qc_pass",store=True)
    remaining_qty              = fields.Float(related='sale_line_id.qty_remaining', string='Remaining Quantity')
    handling                   = fields.Selection(string='Handling',related='sale_id.handling')
    handling_id                = fields.Many2one('master.handling', string='Master Handling', related='sale_id.handling_id')
    jumlah_order               = fields.Integer(string='Jumlah Order')
    sale_type                  = fields.Selection(related="sale_id.sale_type", string='Sale type')
    process_id                 = fields.Many2one('master.proses', string='Process Terkini')
    mesin_id                   = fields.Many2one('mrp.machine', string='Mesin')
    volume_air                 = fields.Float(string="Volume Air",related="mesin_id.volume_air")
    max_batch                  = fields.Integer(related='mesin_id.max_batch', string='Max Batch Machine')
    workcenter_on_progress     = fields.Many2one('mrp.workcenter',compute="_work_in_progress", string='On Progress',store=True,)
    workorder_id               = fields.Many2one('mrp.workorder',compute="_work_in_progress", string='Workorder',store=True,)
    html_color                 = fields.Char(string='Color Visualitation',related="bom_id.color_final_id.html_color", store=True,)
    design_id                  = fields.Many2one( related='product_id.design_id', string='Design')
    program_ids                = fields.Many2many(comodel_name='mrp.program', string='Program')
    amount_duration            = fields.Float(compute='_compute_duration', string='Duration Expected', store=False)
    planned_hours              = fields.Float(compute='_compute_duration', string='Scheduled Hours', store=False)
    lot_ids_count              = fields.Float(compute='_compute_lot_ids', string='Total', store=False)
    is_request_extra_chemical  = fields.Boolean(string='Is Request extra Chemical ?')    
    is_request_extra_component = fields.Boolean(string='Is Request extra COmponent ?')    
    labdip_extra_ids           = fields.Many2many(comodel_name='labdip.extra', string='Extra Chemical')
    labdip_extra_count         = fields.Integer(string='Labdip Extra Count',compute="_get_extra_labdip")
    no_urut_labdip_final       = fields.Char(string='No Urut Labdip final')
    color_id                   = fields.Many2one(related='product_id.color_id', string='Color', store=True,)
    labdip_warna_obj           = fields.Many2one('labdip.warna', string='Labdip Warna',compute='get_labdip_warna',)
    labdip_warna_id            = fields.Many2one('labdip.warna', string='Labdip Warna', related='labdip_warna_obj', store=True,)
    is_dyeing_failed           = fields.Boolean(string='Is Dyeing Failed ?',compute="_compute_dyeing_failed",store=True,)
    returned_finished_ids      = fields.Many2many('mrp.production.return', string='Returned Production')
    picking_finished_id        = fields.Many2one('stock.picking', string='Picking Finished')
    state                      = fields.Selection( selection_add=[("return", "Return")],string='State')
    greige_code                = fields.Char(string='Greige Code', related='greige_id.default_code')
    kelompok_mesin             = fields.Char(string='Kelompok Mesin', related='mesin_id.kelompok', store=True,)
    greige_name                = fields.Char(string='Greige name', related='greige_id.product_tmpl_id.name', store=True,)
    opc_scouring_id            = fields.Many2one('master.opc', string='Obat Scouring', related='process_type.opc_scouring_id')
    state_type                 = fields.Selection(string='Obat Scouring', related='process_type.state_type',store=True,)
    no_warna                   = fields.Char(string='No Warna', related='product_id.color_id.name', store=True,)
    no_urut                    = fields.Integer(string='No Urut')
    is_failed                  = fields.Boolean(string='Is Failed ?', default=False)
    is_failed_need_approve_lab = fields.Boolean(string='Is Failed Need Revision ?', default=False)
    chemical_fix_failed_ids    = fields.One2many('mrp.chemical.fix.failed', 'production_id', 'Chemical Fix Failed')
    is_print_resep             = fields.Boolean(string='Print Resep ?', default=False)
    is_print_resep_scouring    = fields.Boolean(string='Print Resep Scouring ?', default=False)
    greige_code_act            = fields.Float(compute='_compute_greige', string='Greige Code', store=False)
    permintaan_kain_id         = fields.Many2one('permintaan.kain', string='No Bon Permintan Kain')
    operator_id                = fields.Many2one('hr.employee', string='Operator', store=False, compute='_compute_workorder')
    shift                      = fields.Selection([("A","A"),("B","B"),("C","C"),("D","D")], compute='_compute_workorder', string='Shift', store=False)
    state_packing              = fields.Selection([('kirim_packing','Kirim Packing'),('terima_packing','Terima Packing')], string='State')
    tanggal_kirim_packing      = fields.Datetime(string='Tanggal Scan Kirim')
    tanggal_terima_packing     = fields.Datetime(string='Tanggal Scan Terima')
    scan_additional_workcenter = fields.Selection([('input_obat','Input Obat'),('planning','Planning'), ('done', 'Done')], string = 'Kategori')
    saw_input_obat_setup_ids   = fields.One2many('mrp.saw.input.obat', 'production_id', 'SAW - Input Obat')
    process_type_add           = fields.Many2one('master.opc', string='Process')
    workcenter_id_add          = fields.Many2one('mrp.workcenter', string='Worcenter Add')
    reprocess_count            = fields.Integer('ReProses Count',default=0)
    reprocess_confirmation     = fields.Selection(selection=[('need_approve','Need Approve'),('approve_mkt','Approve MKT'),('approve_acc','Approve Accounting')],string='ReProses Confirmation')
    # kode_prod_ids              = fields.One2many('kode.prod.sizing','production_id',string='Kode Prod')
    greige_name                = fields.Many2one('product.product',string='Nama Greige/Corak',default=84746, domain=[('categ_id.name', 'in', ('greige', 'GREY'))])
    qty_hasil                  = fields.Float(string="Quantity Hasil") 
    partial_qty                = fields.Float(string="Partial Quantity", compute="_compute_partial_qty",)
    tgl_keluar_lab             = fields.Date(string='Tanggal Masuk')
    

    @api.depends('partial_qty')
    def _compute_partial_qty(self):
        for line in self:
            line.partial_qty = sum(line.move_finished_ids.mapped('quantity_done'))
    
    @api.depends('picking_ids')
    def _compute_greige(self):
        for line in self:
            picking_ids = line.picking_ids.filtered(lambda x:x.picking_type_id.id == 604)
            if picking_ids:
                for picking in picking_ids:
                    line.greige_code_act = picking.move_ids_without_package[0].product_id.default_code
            else:
                line.greige_code_act = False

    @api.depends('workorder_ids')
    def _compute_workorder(self):
        for line in self:
            workorder_ids = line.workorder_ids.filtered(lambda x:x.workcenter_id.name == "DYEING")
            if workorder_ids:
                # for workorders in workorder_ids:
                # line.shift = workorder_ids[0].shift
                line.shift = False
                line.operator_id = workorder_ids[0].employee_id.id
            else:
                line.shift = False
                line.operator_id = False
                
    def reset_wo(self):
        for production in self:
                workorder_ids = production.workorder_ids.filtered(lambda x: x.workcenter_id.id == 1)
                if len(workorder_ids) == 1:
                    open_roll = production.workorder_ids.filtered(lambda x: x.workcenter_id.id == 9 and x.state != 'pending')
                    for roll in open_roll:
                        roll.write({'state':'pending'})  
                    
    
    def create_picking_finished(self):
        picking_finished_id = self.env['stock.picking'].sudo().create({
            'picking_type_id': self.type_id.picking_type_finished_id.id,
            'date': fields.Date.today(),
            'scheduled_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'production_id':self.id,
            'origin':self.name,
            "location_id":self.picking_type_id.default_location_dest_id.id,
            "location_dest_id":self.type_id.picking_type_finished_id.default_location_dest_id.id,
            'immediate_transfer': False,
            'move_line_nosuggest_ids': [(0,0,{
                    'product_id': self.product_id.id,
                    'lot_id': self.lot_producing_id.id,
                    'lot_name': self.lot_producing_id.name,
                    'product_uom_id': self.product_id.uom_id.id,
                    "location_id":self.picking_type_id.default_location_dest_id.id,
                    "location_dest_id":self.type_id.picking_type_finished_id.default_location_dest_id.id,
                    
                    # 'qty_done': self.qty_producing,
                    'qty_done': self.product_qty,
                    'company_id':self.env.company.id,
                })],
            'move_lines': [(0,0,{
                'name': self.product_id.name,
                'picking_type_id': self.type_id.picking_type_finished_id.id,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'product_id': self.product_id.id,
                "location_id":self.picking_type_id.default_location_src_id.id,
                "location_dest_id":self.type_id.picking_type_finished_id.default_location_dest_id.id,
                'product_uom': self.product_id.uom_id.id,
                'product_uom_qty': self.product_qty,
                # 'product_uom_qty': self.qty_producing,
                'company_id': self.env.company.id,
                
                })],
            
        })
        
        # picking_finished_id.action_confirm()
        # picking_finished_id.button_validate()
        
        return picking_finished_id
    
    
    def button_mark_done(self):
        if self.type_id.name == 'DYEING':
            ## UPDATE BOM
            self.bom_id.bom_line_ids = False
            self.bom_id.write({
                'bom_line_ids': [(0, 0, {
                    'product_id' : b.product_id.id,
                    'product_qty' : b.product_uom_qty,
                    # 'product_qty' : td_material.quantity_finish,
                    'product_uom_id' : b.product_id.uom_id.id,
                    # 'location_id': td_material.location_id.id,
                    # 'kategori_id': td_material.workcenter_id.id,
                    # 'type': td_material.type
                }) for b in self.move_raw_ids]
            })
        
        res = super(MrpProduction, self).button_mark_done()
        
        
        if res is True and not self.production_origin_id and self.type_id.name not in ('PAPERTUBE', 'SIZING', 'WEAVING') :
            self.picking_finished_id = self.create_picking_finished()
            self.picking_finished_id.action_confirm()
            self.picking_finished_id.button_validate()
            
        elif res is True and not self.production_origin_id and self.type_id.name == 'SIZING':
            self.lot_producing_id.write({
                "production_id":self.id,
        })
        
        if self.type_id.name == 'SIZING' and self.qty_producing < 1:
            self.qty_producing = self.partial_qty
        
        return res
        
    
    @api.depends('workorder_ids','workorder_ids.qc_pass')
    def _compute_dyeing_failed(self):
        for rec in self:
            rec.is_dyeing_failed = len(self.workorder_ids.filtered(lambda x :x.workcenter_id.name == "DYEING" and x.qc_pass == 'fail')) >= 1
    
    @api.depends('color_id', 'labdip_id')
    def get_labdip_warna(self):
        for rec in self:
            labdip_warna_obj = self.env['labdip.warna'].search([('labdip_id','=',rec.labdip_id.id),('color_id','=',rec.color_id.id)], limit=1)
            rec.labdip_warna_obj = labdip_warna_obj.id
    
    
    def action_view_chemical_extra(self):
        _logger.warning('='*40)
        action = self.env.ref('inherit_mrp.open_labdip_extra_action').read()[0]
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {}
        return action
         
         
    def _get_extra_labdip(self):
        for production in self:
            production.labdip_extra_count = len(production.labdip_extra_ids)
    
    
    def load_opc(self):
        # if self.state == 'draft':
        opc_ids = []
        for move in self.move_raw_ids.filtered(lambda x: x.type == 'opc'):
            move._action_cancel()
            move.action_back_to_draft()
            move.unlink()
            
        for auxiliaries in self.process_type.line_ids:
            opc_ids += [(0, 0, {
                    # 'kategori': 'aux',
                    "name":auxiliaries.product_id.name,
                    'product_id': auxiliaries.product_id.id,
                    'chemical_conc': auxiliaries.qty,
                    'product_uom_qty': auxiliaries.qty,
                    "product_uom":auxiliaries.product_id.uom_id.id,
                    "kelompok_id":auxiliaries.kelompok_id.id,
                    "location_id":self.location_src_id.id,
                    "location_dest_id":15,
                    'type': 'opc'
                })]            
        self.write({
            "move_raw_ids": opc_ids
        })
        self.load_obat_scouring()
    
    def load_obat_scouring(self):
        print("load_obat_scouring")
        opc_ids = []
        for move in self.move_raw_ids.filtered(lambda x: x.type == 'obat_scouring'):
            move._action_cancel()
            move.action_back_to_draft()
            move.unlink()
            
        for auxiliaries in self.opc_scouring_id.line_ids:
            product_qty = (auxiliaries.qty * self.volume_air ) / 1000
            opc_ids += [(0, 0, {
                    # 'kategori': 'aux',
                    "name":auxiliaries.product_id.name,
                    'product_id': auxiliaries.product_id.id,
                    'chemical_conc': auxiliaries.qty,
                    'product_uom_qty': product_qty,
                    "product_uom":auxiliaries.product_id.uom_id.id,
                    "location_id":self.location_src_id.id,
                    "kelompok_id":auxiliaries.kelompok_id.id,
                    "location_dest_id":15,
                    "forecast_availability": product_qty,
                    'type': 'obat_scouring'
                })]            
        self.write({
            "move_raw_ids": opc_ids
        })

    def action_requst_extra_chemical(self):
        color_final = self.env['labdip.color.final'].sudo().search([('labdip_id','=',self.labdip_id.id),('color_id','=',self.product_id.color_id.id)],limit=1)
        color_final.sudo().write({"is_failed":True})
        color_final.sudo().write({"production_id":self.id})
        self.is_request_extra_chemical = True
        title = _("Warning")
        message = _("Request Extra Chemical Has been sent!!")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': True,
                'type': 'success',
            }
        }
        
        
    
    
    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        for production in self:
            if not production.bom_id.labdip_id and production.type_id.name == 'DYEING':
                raise UserError('Labdip cannot be empty !!!')
            if not production.bom_id.td_id and production.type_id.name == 'DYEING':
                raise UserError('TD cannont be empty  !!!')
                
        return res
            
    def action_open_inventory(self):
        _logger.warning('='*40)
        _logger.warning('='*40)
        _logger.warning('ACTION OPEN QTY')
        _logger.warning('='*40)
        _logger.warning('='*40)
        return {
            'type'      : 'ir.actions.act_window',
            'name'      : 'Open Inventory',
            'res_model' : 'quantity.beam.wizard',
            'view_mode' : 'form',
            'target'    : 'new',
            'context'   : {
                'default_production_id': self.id,
                "default_beaming_ids": self.beaming_ids.filtered(lambda x: not x.state).ids,
                "default_production_qty": self.product_qty,
                # "default_lot_qty": self.product_qty,
                "default_produce_qty": sum(self.beaming_ids.filtered(lambda x: not x.state).mapped('total_panjang')),
                
                    
                    },
        }
    def post_inventory_open(self):
        _logger.warning('='*40)
        _logger.warning('='*40)
        _logger.warning('ACTION POST INVENTORY')
        _logger.warning('='*40)
        _logger.warning('='*40)
        return {
            'type'      : 'ir.actions.act_window',
            'name'      : 'Post Inventory Weaving',
            'res_model' : 'post.inventory.weaving',
            'view_mode' : 'form',
            'target'    : 'new',
            'context'   : {
                # 'default_production_id': self.id,
                # "default_beaming_ids": self.beaming_ids.filtered(lambda x: not x.state).ids,
                # "default_production_qty": self.product_qty,
                # # "default_lot_qty": self.product_qty,
                # "default_produce_qty": sum(self.beaming_ids.filtered(lambda x: not x.state).mapped('total_panjang')),
                
                    
                    },
        }
    @api.onchange('program_ids')
    def onchange_program(self):
        dt = timedelta(minutes=self.amount_duration)
        self.write({"date_planned_finished": self.date_planned_start + dt})
    
    
    @api.depends('move_finished_ids')
    def _compute_lot_ids(self):
        for production in self:
            production.lot_ids_count = len([moveline.lot_id.id for moveline in move.move_line_ids  for move in production.move_finished_ids])
    
    
    @api.depends('program_ids')
    def _compute_duration(self):
        for production in self:
            amount_duration = sum(production.program_ids.mapped('duration'))
            production.amount_duration = amount_duration
            production.planned_hours =  production.amount_duration / 60.0
    

    def _compute_kategori_resep(self):
        for rec in self:
            if rec.labdip_id:
                rec.process_category_id = rec.labdip_id.labdip_color_final_ids.filtered(lambda x: x.color_id.id == rec.color_id.id).process_type_id.id or False
    
    def action_terima_packing(self,context=None):
        self.state_packing = 'terima_packing'
        self.tanggal_terima_packing = datetime.now()

        # move = self.env['mrp.production'].search([('product_id', '=', self.id)])
        # action = {
        #             'name': 'Terima Packing',
        #             'type': 'ir.actions.act_window',
        #             'view_mode': 'tree,form',
        #             'res_model': 'mrp.production',
        #             'domain': [('id', '=', move.ids)],
        #             'view_id ref="inherit_mrp.mrp_terima_packing_tree"': '',
        #         }
        # return action
    
    # def action_terima_gdjd(self,context=None):
    #     self.state_packing = 'terima_gdjd'
    #     self.tanggal_scan = datetime.now()
    
    # progress = fields.Float('Progress Done (%)', digits=(16, 2), compute='_compute_progress')
    

    production_origin_id   = fields.Many2one('mrp.production', string='Repeat Production')
    flag                    = fields.Boolean(string='Flag',default=True)
    
    #Design
    warna = fields.Char(string='Warna', compute="_compute_warna")

    #greige
    greige_id           = fields.Many2one('product.product', string='Greige Name')
    std_potong          =  fields.Float(string='Std Potong',related="greige_id.std_potong")
    greige_code         =  fields.Char(string='Greige Code',related="greige_id.default_code")
    gramasi_target      = fields.Float(string='Gramasi Target',related="sale_id.gramasi")
    lebar_target        = fields.Float(string='Lebar Target',related="sale_id.lebar")
    gramasi_greige      = fields.Float(string='Gramasi Greige',related="greige_id.gramasi_greige")
    lebar_greige        = fields.Float(string='Lebar Greige',related="greige_id.lebar_greige")    
    gramasi_kain_finish = fields.Float(string='Gramasi Kain Finish')
    lebar_kain_finish   = fields.Float(string='Lebar Kain Finish')
    density_kain_finish = fields.Float(string='Density Kain Finish')
    mkt_id              = fields.Many2one('marketing.order', string='Marketing Order',track_visibility='onchange')
    mkt_production_id   = fields.Many2one('mkt.production.line', string='Mkt Production')
    qty_mkt             = fields.Float(string='Total Order')
    
    component_chemical_has_request = fields.Boolean(string='Component chemical Requested ?',default=False)
    component_chemical_scr_has_request = fields.Boolean(string='Component chemical Scr Requested ?',default=False)

    #Quantity OM
    qty_roll_kp = fields.Float(string='Qty Roll Kp')
    qty_kg_kp = fields.Float(string='Qty Kg',compute="_compute_quantity")
    qty_yard_kp = fields.Float(string='Qty Yard')
    qty_meter_kp = fields.Float(string='Qty Meter',compute="_compute_quantity")


    #Quantity Request P yana
    qty_roll_kp_ppc = fields.Float(string='Qty Roll Kp')
    qty_kg_kp_ppc = fields.Float(string='Qty Kg',compute="_compute_quantity")
    qty_yard_kp_ppc = fields.Float(string='Qty Yard',compute="_compute_quantity")
    qty_meter_kp_ppc = fields.Float(string='Qty Meter',compute="_compute_quantity")


    #Quantity Actual Greige
    qty_roll_kp_actual = fields.Float(string='Qty Roll Kp')
    qty_kg_kp_actual = fields.Float(string='Qty Kg',compute="_compute_quantity")
    qty_yard_kp_actual = fields.Float(string='Qty Yard', compute="_compute_quantity")
    qty_meter_kp_actual = fields.Float(string='Qty Meter',compute="_compute_quantity")

    #WIP
    qty_process = fields.Float(string='Qty Process')
    susut = fields.Float(string='Susut')
    ref_volume_mesin = fields.Float(string='Ref volume mesin')
    volume_mesin = fields.Float(string='Volume mesin')

    #inspect
    kategori_id = fields.Many2one('type.ship', string='Kategori')
    grading = fields.Selection([("10","10 Points"),("4","4 Points")], string='Grading')
    piece_length = fields.Integer(string='Piece Length')
    acessories_id = fields.Many2one('acessories', string='Acessories')
    hangtag_id = fields.Many2one('hangtag', string='Hangtag')

    proses_ids = fields.One2many('test.development.final', 'mrp_production_id', string='Flow Proses')

    #Start Field kebutuhan MO Sizing
    unit_sizing = fields.Char(string='Unit Sizing')
    location_id = fields.Many2one('stock.location', string='Location')
    kd_benang = fields.Char(string='Kode Benang')
    jenis_benang  = fields.Char(string='Jenis Benang')
    qty_benang = fields.Float(string='Berat Benang')
    sc_id = fields.Many2one('sale.contract', string='Kontrak', readonly=True,)
    
    nama_design = fields.Char(string='Nama Design')
    sisir_id = fields.Many2one('master.sisir', string='Sisir')
    total_end = fields.Float(string='Total End')
    jml_beam_stand = fields.Float(string='Jumlah Beam Stand')
    total_creel = fields.Integer(string='Creel')
    beaming_ids = fields.One2many('mrp.beaming', 'production_id', string='Beaming', readonly=False,)

    #End Field kebutuhan MO Sizing

    # Start Field Kebutuhan MO Weaving
    # lot_id          = fields.Many2one('stock.production.lot', string='Kartu Beam')
    # beam_id         = fields.Many2one('mrp.production.beam', related='lot_id.beam_id',string='No Beam')
    # beam_type_id    = fields.Many2one('mrp.production.beam.type', string='Beam Type')
    kode_test       = fields.Char(string='Kode Test')
    total_lusi      = fields.Float(string='Total Lusi')
    pick_in_greige  = fields.Float(string='Pick In Greige')
    jarum           = fields.Float(string='Jarum')
    pakan           = fields.Float(string='Pakan')
    rpm             = fields.Integer(string='Rpm')
    tgl_naik_beam   = fields.Date(string='Tanggal Naik Beam')
    tgl_hbs_beam    = fields.Date(string='Tanggal Habis Beam')
    date_selesai_proofing = fields.Date(string='Selesai Proofing')
    note            = fields.Text(string='Note')
    # End Field Kebutuhan MO Weaving

    # Start Field kebutuhan MO Twisting
    qty_penarikan_sw    = fields.Char(string='Penarikan Sw')
    no_om               = fields.Char(string='No SO')
    jenis_order         = fields.Selection([("lusi","Lusi"),("pakan","Pakan")], string='Jenis Order')
    jenis_mesin         = fields.Selection([("wjl","WJL"),("shuttle","Shuttle")], string='Jenis Mesin Weaving')
    revisi              = fields.Integer(string='Revisi')
    order_penarikan_sw  = fields.Float(string='Order Penarikan Sw')
    # End Field kebutuhan MO Twisting
    
    type_id             = fields.Many2one('mrp.type', string='Order Type',required=True, track_visibility='onchange')
    is_permintaan_kain  = fields.Boolean(string='Is Permintaan Kain ?', default=False)
    journal_count       = fields.Integer(string='Journal Count', compute="compute_journal_count")
    employee_id         = fields.Many2one('hr.employee', string='Pegawai')
    waste               = fields.Float(string='Waste')
    
    is_inspected            = fields.Boolean(string='Is Inspected',default=False)
    temp_program_id         = fields.Many2one('mrp.program', string='Program')   
    keterangan_perbaikan    = fields.Char(string='Keterangan Gagal')
    was_failed              = fields.Boolean(string='Was Failed ?', default=False)
    was_need_approve_lab    = fields.Boolean(string='Need Approve lab ?', default=False)
    was_request_reprocess   = fields.Boolean(string='Need Request Reprocess ?', default=False)
    was_reprocessed         = fields.Boolean(string='Was Reprocessed ?', default=False)
    note_failed             = fields.Char(string='Note Failed')
    is_printed              = fields.Boolean(string='Is Printed ?', default=False)
    date_attempt            = fields.Date(string='Date Attempt')
    # date_attempt    = fields.Datetime(string="Date Attempt", default=fields.Datetime.now())
    date_analisa            = fields.Datetime(string="Date Analisa", default=fields.Datetime.now())
    date_action             = fields.Datetime(string="Date Action", default=fields.Datetime.now())
    analisa                 = fields.Text('Analisa')
    tgl_masuk_lab           = fields.Datetime(string="Tgl Masuk Lab", default=fields.Datetime.now())




    @api.onchange('mkt_production_id')
    def get_mkt_production_id(self):
        for rec in self:
            rec.qty_mkt = rec.mkt_production_id.quantity
    
    def action_chemical_excomponent_request(self):
        move_raw_ids = []
        move_chemical_request_ids = []
        if len(self.labdip_extra_ids) > 0:
            for component in self.labdip_extra_ids:
                product_qty = (component.conc * self.qty_kg_kp * 10 ) / 1000 if component.kategori == 'dye' else (component.conc * self.volume_air ) / 1000
                move_raw_ids.append((0,0,{
                    "name":component.product_id.name,
                    "product_id":component.product_id.id,
                    "product_uom_qty":product_qty,
                    "product_uom":component.product_id.uom_id.id,
                    "is_extra":True,
                    "location_id":self.type_id.component_location.id,
                    "location_dest_id":15,
                }))
            self.move_raw_ids = move_raw_ids
            for move_raw in self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.name != 'GREY' and x.is_extra):
                    move_chemical_request_ids.append((0,0,{
                        "name":move_raw.product_id.name,
                        "product_id":move_raw.product_id.id,
                        "product_uom_qty":move_raw.product_uom_qty,
                        "product_uom":move_raw.product_id.uom_id.id,
                        "location_id":self.type_id.component_chemical_location.id,
                        "location_dest_id":self.type_id.component_location.id,
                        "move_dest_ids":[(4,move.id) for move in self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.name != 'GREY')]
                    }))
                    
            
            self.env['stock.picking'].sudo().create({
                    "picking_type_id":self.type_id.component_chemical_picking_type_id.id,
                    "location_id":self.type_id.component_chemical_location.id,
                    "location_dest_id":self.type_id.component_location.id,
                    "mrp_request_id": self.mrp_request_id.id,
                    "production_id": self.id,
                    "origin": self.name,
                    "note": "Extra Obat",
                    "move_ids_without_package":move_chemical_request_ids
                })
                
            self.write({"is_request_extra_component":True})
            
    
    
    #overide
    def _plan_workorders(self, replan=False):
        """ Plan all the production's workorders depending on the workcenters
        work schedule.

        :param replan: If it is a replan, only ready and pending workorder will be take in account
        :type replan: bool.
        """
        self.ensure_one()

        if not self.workorder_ids:
            return
        # Schedule all work orders (new ones and those already created)
        qty_to_produce = max(self.product_qty - self.qty_produced, 0)
        qty_to_produce = self.product_uom_id._compute_quantity(qty_to_produce, self.product_id.uom_id)
        start_date = max(self.date_planned_start, datetime.now())
        if replan:
            workorder_ids = self.workorder_ids.filtered(lambda wo: wo.state in ['ready', 'pending'])
            # We plan the manufacturing order according to its `date_planned_start`, but if
            # `date_planned_start` is in the past, we plan it as soon as possible.
            workorder_ids.leave_id.unlink()
        else:
            workorder_ids = self.workorder_ids.filtered(lambda wo: not wo.date_planned_start)
        for workorder in workorder_ids:
            workcenters = workorder.workcenter_id | workorder.workcenter_id.alternative_workcenter_ids

            best_finished_date = datetime.max
            vals = {}
            for workcenter in workcenters:
                # compute theoretical duration
                if workorder.workcenter_id == workcenter:
                    duration_expected = workorder.duration_expected
                else:
                    duration_expected = workorder._get_duration_expected(alternative_workcenter=workcenter)

        #         from_date, to_date = workcenter._get_first_available_slot(start_date, duration_expected)
        #         # If the workcenter is unavailable, try planning on the next one
        #         if not from_date:
        #             continue
        #         # Check if this workcenter is better than the previous ones
        #         if to_date and to_date < best_finished_date:
        #             best_start_date = from_date
        #             best_finished_date = to_date
        #             best_workcenter = workcenter
        #             vals = {
        #                 'workcenter_id': workcenter.id,
        #                 'duration_expected': duration_expected,
        #             }

        #     # If none of the workcenter are available, raise
        #     # if best_finished_date == datetime.datetime.max:
        #     #     raise UserError(_('Impossible to plan the workorder. Please check the workcenter availabilities.'))

        #     # Instantiate start_date for the next workorder planning
        #     if workorder.next_work_order_id:
        #         start_date = best_finished_date

        #     # Create leave on chosen workcenter calendar
        #     leave = self.env['resource.calendar.leaves'].create({
        #         'name': workorder.display_name,
        #         'calendar_id': best_workcenter.resource_calendar_id.id,
        #         'date_from': best_start_date,
        #         'date_to': best_finished_date,
        #         'resource_id': best_workcenter.resource_id.id,
        #         'time_type': 'other'
        #     })
        #     vals['leave_id'] = leave.id
        #     workorder.write(vals)
        # self.with_context(force_date=True).write({
        #     'date_planned_start': self.workorder_ids[0].date_planned_start,
        #     'date_planned_finished': self.workorder_ids[-1].date_planned_finished
        # })
    
    Mrp._plan_workorders = _plan_workorders   
    
    # def write(self, vals):
    #     if 'workorder_ids' in self:
    #         production_to_replan = self.filtered(lambda p: p.is_planned)
    #     # res = super(MrpProduction, self).write(vals)

    #     for production in self:
    #         if 'date_planned_start' in vals and not self.env.context.get('force_date', False):
    #             if production.state in ['done', 'cancel']:
    #                 raise UserError(_('You cannot move a manufacturing order once it is cancelled or done.'))
    #             if production.is_planned:
    #                 production.button_unplan()
    #                 move_vals = self._get_move_finished_values(self.product_id, self.product_uom_qty, self.product_uom_id)
    #                 production.move_finished_ids.write({'date': move_vals['date']})
    #         if vals.get('date_planned_start'):
    #             production.move_raw_ids.write({'date': production.date_planned_start, 'date_deadline': production.date_planned_start})
    #         if vals.get('date_planned_finished'):
    #             production.move_finished_ids.write({'date': production.date_planned_finished})
    #         if any(field in ['move_raw_ids', 'move_finished_ids', 'workorder_ids'] for field in vals) and production.state != 'draft':
    #             if production.state == 'done':
    #                 # for some reason moves added after state = 'done' won't save group_id, reference if added in
    #                 # "stock_move.default_get()"
    #                 production.move_raw_ids.filtered(lambda move: move.additional and move.date > production.date_planned_start).write({
    #                     'group_id': production.procurement_group_id.id,
    #                     'reference': production.name,
    #                     'date': production.date_planned_start,
    #                     'date_deadline': production.date_planned_start
    #                 })
    #                 production.move_finished_ids.filtered(lambda move: move.additional and move.date > production.date_planned_finished).write({
    #                     'reference': production.name,
    #                     'date': production.date_planned_finished,
    #                     'date_deadline': production.date_deadline
    #                 })
    #             production._autoconfirm_production()
    #             if production in production_to_replan:
    #                 production._plan_workorders(replan=False)
    #         if production.state == 'done' and ('lot_producing_id' in vals or 'qty_producing' in vals):
    #             finished_move_lines = production.move_finished_ids.filtered(
    #                 lambda move: move.product_id == self.product_id and move.state == 'done').mapped('move_line_ids')
    #             if 'lot_producing_id' in vals:
    #                 finished_move_lines.write({'lot_id': vals.get('lot_producing_id')})
    #             if 'qty_producing' in vals:
    #                 finished_move_lines.write({'qty_done': vals.get('qty_producing')})

    #         if not production.bom_id.operation_ids and vals.get('date_planned_start') and not vals.get('date_planned_finished'):
    #             new_date_planned_start = fields.Datetime.to_datetime(vals.get('date_planned_start'))
    #             if not production.date_planned_finished or new_date_planned_start >= production.date_planned_finished:
    #                 production.date_planned_finished = new_date_planned_start + datetime.timedelta(hours=1)
    #     # return res
        
        
    # Mrp.write = write              
    
    def action_chemical_component_request(self,qty_greige):
        move_raw_ids = []
        move_chemical_request_ids = []
        if self.labdip_id:
            labdip_final_ids = self.labdip_id.labdip_color_final_ids.filtered(lambda x: x.color_id.id == self.product_id.color_id.id)
            qty_kg_greige =  (self.greige_id.gramasi_greige * qty_greige )/ 1000  
            if self.move_raw_ids:
                # self.move_raw_ids = move_raw_ids
                for move_raw in self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.name != 'GREY' and x.type != 'obat_scouring'):
                    category = move_raw.product_id.categ_id.kategori_obat
                    product_qty = (move_raw.chemical_conc * qty_kg_greige * 10 ) / 1000 if category == 'dye' else (move_raw.chemical_conc * self.volume_air ) / 1000
                    move_chemical_request_ids.append((0,0,{
                        "name":move_raw.product_id.name,
                        "product_id":move_raw.product_id.id,
                        "product_uom_qty":product_qty,
                        "product_uom":move_raw.product_id.uom_id.id,
                        "chemical_conc":move_raw.chemical_conc,
                        "type":move_raw.type,
                        "kelompok_id":move_raw.kelompok_id.id,
                        "location_id":self.type_id.component_chemical_location.id,
                        "location_dest_id":self.picking_type_id.default_location_src_id.id,
                        "move_dest_ids":[(4,move.id) for move in self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.name != 'GREY' and x.product_id.id == move_raw.product_id.id)]
                    }))

            
                self.env['stock.picking'].sudo().create({
                    "picking_type_id":self.type_id.component_chemical_picking_type_id.id,
                    "location_id":self.type_id.component_chemical_location.id,
                    "location_dest_id":self.picking_type_id.default_location_src_id.id,
                    "mrp_request_id": self.mrp_request_id.id,
                    "production_id": self.id,
                    "origin": self.name,
                    "greige_qty_req":self.product_qty,
                    "scheduled_date": self.date_planned_start,
                    "move_ids_without_package":move_chemical_request_ids
                })
                
                self.write({"component_chemical_has_request":True})
    
    def action_chemical_component_scouring_request(self,qty_greige):
        move_raw_ids = []
        move_chemical_request_ids = []
        if self.labdip_id:
            qty_kg_greige =  (self.greige_id.gramasi_greige * qty_greige )/ 1000  
            if self.move_raw_ids:
                self.move_raw_ids = move_raw_ids
                for move_raw in self.move_raw_ids.filtered(lambda x: x.type == 'obat_scouring'):
                    category = move_raw.product_id.categ_id.kategori_obat
                    product_qty = (move_raw.chemical_conc * qty_kg_greige * 10 ) / 1000 if category == 'dye' else (move_raw.chemical_conc * self.volume_air ) / 1000
                    move_chemical_request_ids.append((0,0,{
                        "name":move_raw.product_id.name,
                        "product_id":move_raw.product_id.id,
                        "product_uom_qty":product_qty,
                        "product_uom":move_raw.product_id.uom_id.id,
                        "chemical_conc":move_raw.chemical_conc,
                        "type":move_raw.type,
                        "kelompok_id":move_raw.kelompok_id.id,
                        "location_id":self.type_id.component_chemical_location.id,
                        "location_dest_id":self.picking_type_id.default_location_src_id.id,
                        "move_dest_ids":[(4,move.id) for move in self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.name != 'GREY' and x.product_id.id == move_raw.product_id.id)]
                    }))

            
                self.env['stock.picking'].sudo().create({
                    "picking_type_id":self.type_id.component_chemical_picking_type_id.id,
                    "location_id":self.type_id.component_chemical_location.id,
                    "location_dest_id":self.picking_type_id.default_location_src_id.id,
                    "mrp_request_id": self.mrp_request_id.id,
                    "production_id": self.id,
                    "origin": self.name,
                    "greige_qty_req":self.product_qty,
                    "scheduled_date": self.date_planned_start,
                    "move_ids_without_package":move_chemical_request_ids,
                    "is_scouring" : True
                })

                self.write({"component_chemical_scr_has_request":True})

    def _compute_quantity(self):
        for production in self:            
            production.qty_meter_kp = production.product_qty * 0.9144
            production.qty_kg_kp =   (production.greige_id.gramasi_greige * production.product_qty ) / 1000  

            production.qty_yard_kp_ppc = production.product_qty_ppc
            production.qty_meter_kp_ppc = production.product_qty_ppc * 0.9144
            production.qty_kg_kp_ppc =   (production.greige_id.gramasi_greige * production.mrp_request_id.quantity_greige ) / 1000  

            production.qty_yard_kp_actual =  sum(production.picking_request_ids.filtered(lambda x:x.picking_type_id.id == 604).mapped('move_ids_without_package.quantity_done'))
            production.qty_meter_kp_actual = production.qty_yard_kp_actual * 0.9144
            production.qty_kg_kp_actual = production.greige_id.gramasi_greige * production.qty_yard_kp_actual / 1000
            
            
    
            
    
    
    def _read(self, fields):
        # untuk kebutuhan view gantt planning production
        res = super()._read(fields)
        if self.env.context.get('display_product_and_color') and 'mesin_id' in self.env.context.get('group_by', []):
            name_field = self._fields['name']
            for record in self.with_user(SUPERUSER_ID):
                # variant = record.product_id.product_template_attribute_value_ids._get_combination_name()
                self.env.cache.set(record, name_field,record.name +' ' + record.product_id.name + ' ' + ' ' + record.sale_id.name + record.partner_id.name + ' ' + record.color_id.name)
        return res
    
    
    
    
    @api.model
    def create(self, vals):
        type_id = self.env['mrp.type'].browse(vals.get('type_id'))
        if not vals.get('name'):
            vals['name'] = type_id.production_sequence_id.next_by_id()
        result = super(MrpProduction, self).create(vals)
        return result


    def action_change_src_location(self):
        bom_line_dict = {rec.product_id.id: rec.location_id.id for rec in self.bom_id.bom_line_ids}
        for rec in self.move_raw_ids:
            rec.write({'location_id' : bom_line_dict.get(rec.product_id.id)})
    
    @api.onchange('bom_id')
    def onchange_bom_id(self):
        print('onchange_bom_id')
        self.location_dest_id = self.bom_id.location_dest_id.id

    def _compute_warna(self):
        for a in self:
            for b in a.product_id:
                a.warna = b.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id.name == 'WARNA').name
                break


    
    def get_parameter_process(self):
        data = {}
        for a in self.bom_id.operation_ids:
            data[a.workcenter_id.id] = [{'parameter_id': b.parameter_id.id, 'no_urut':b.no_urut, 'plan':b.plan,
            'actual':b.actual, 'uom_id':b.uom_id.id} for b in a.routing_paramter_ids]
        
        for rec in self.workorder_ids:
            rec.parameter_ids = False
            for x in data[rec.workcenter_id.id]:
                rec.parameter_ids = [(0, 0, x)]
                
    
    def get_last_wo(self):
        query = """
                SELECT  max(date_planned_finished)  as date_planned_finished 
                FROM mrp_workorder
                WHERE state != 'done' and
                is_planning = true
            """
        self._cr.execute(query)
        result = self._cr.dictfetchone()
        return result.get('date_planned_finished')
                
                
    def check_wo_planning(self):
        query = """
                SELECT id,production_id,date_planned_start 
                FROM mrp_workorder
                WHERE date_planned_start = '%s' and is_planning = true ORDER by date_planned_finished
            """%(fields.Datetime.add(fields.Datetime.now(), hours=7))
        self._cr.execute(query)
        result = self._cr.dictfetchall()
        if len(result) > 0:
            return True
        return False            
    
    
    
    
    # Start Overiding from base odoo
    def _create_workorder(self):
        sync_time = timedelta(hours=7)
        
        for production in self:
            if not production.bom_id:
                continue
            
            workorders_values = []
            filled = None
            if self.check_wo_planning():
                filled = True
            else:
                filled = False
            

            product_qty = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
            exploded_boms, dummy = production.bom_id.explode(production.product_id, product_qty / production.bom_id.product_qty, picking_type=production.bom_id.picking_type_id)

            for bom, bom_data in exploded_boms:
                # If the operations of the parent BoM and phantom BoM are the same, don't recreate work orders.
                if not (bom.operation_ids and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.operation_ids != bom.operation_ids)):
                    continue
                for idx,operation in enumerate(bom.operation_ids):
                    prev = workorders_values[idx - 1] if idx >= 1 else None
                    
                    duration = operation.program_id.duration
                    dt = timedelta(minutes=duration) if operation.program_id and operation.workcenter_id.is_planning else False
                    
                    dt_start = self.date_planned_start
                    # dt_start = datetime.combine(self.date_planned_start.date(), datetime.min.time()) 
                    dt_finished = None
                    
                    if operation.program_id and operation.workcenter_id.is_planning and not  prev.get('date_planned_finished'):
                        dt_start = self.date_planned_start
                        # dt_start = datetime.combine(self.date_planned_start.date(), datetime.min.time())
                        dt_finished = dt_start + dt if operation.program_id and operation.workcenter_id.is_planning else False
                        # start_working = timedelta(hours=6,minutes=30) 
                        # dt_start =  dt_start + start_working  if operation.program_id and operation.workcenter_id.is_planning else False
                        dt_start = fields.Datetime.add(dt_start,minutes=30) if not filled and operation.program_id and operation.workcenter_id.is_planning else dt_finished 
                        # dt_start = dt_start - sync_time if not filled and operation.program_id and operation.workcenter_id.is_planning else dt_finished 
                    
                    elif operation.program_id and operation.workcenter_id.is_planning and idx > 0 and prev and prev.get('date_planned_finished'):
                        dt_start = prev.get('date_planned_finished')
                        dt_finished = dt_start + dt
                                
                        
            
                    
                    workorders_values += [{
                        'name': operation.name,
                        'production_id': production.id,
                        'workcenter_id': operation.workcenter_id.id,
                        'product_uom_id': production.product_uom_id.id,
                        "date_planned_start":dt_start if operation.workcenter_id.is_planning else False,
                        "date_planned_finished":dt_finished if operation.workcenter_id.is_planning else False,
                        "duration_expected":duration if duration else False,
                        'operation_id': operation.id,
                        'state': 'pending',
                        'consumption': production.consumption,
                        'mesin_id': operation.mesin_id.id,
                        'program_id': operation.program_id.id,
                    }]
            production.workorder_ids = [(5, 0)] + [(0, 0, value) for value in workorders_values]
            for workorder in production.workorder_ids:
                workorder.duration_expected = workorder._get_duration_expected()
            max_date = max(production.workorder_ids.filtered(lambda x:x.date_planned_finished).mapped('date_planned_finished')) if production.workorder_ids.filtered(lambda x:x.date_planned_finished).mapped('date_planned_finished') else False
            # min_date = max(production.workorder_ids.filtered(lambda x:x.date_planned_start).mapped('date_planned_start'))
            if max_date:
                production.write({"date_planned_finished":max_date,
                                #   "date_planned_start":min_date
                                  })
    # End Overiding from base odoo

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        res = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False)
        if self.state == 'draft':
            self.move_raw_ids = False
        to_consume = 0
        
        category = product_id.categ_id.kategori_obat
        if category:
            to_consume = (res.get('product_uom_qty', 0) * self.qty_kg_kp_actual * 10 ) / 1000 if category == 'dye' else (res.get('product_uom_qty', 0) * self.volume_air ) / 1000
            res['chemical_conc'] = res.get('product_uom_qty', 0)
        else:
            to_consume = res.get('product_uom_qty', 0)
        # ksldnfsld
        # if self.type_id.name == 'DYEING':
        #     kateg_obat = bom_line.kategori_obat
        #     if kateg_obat:
        #         if kateg_obat == 'dye':
        #             to_consume = res.get('product_uom_qty', 0) * self.product_qty
        #         else:
        #             to_consume = res.get('product_uom_qty', 0) * self.kapasitas_mesin
        #     else:
        #         to_consume = res.get('product_uom_qty', 0) * self.product_qty
        # else:
        # to_consume = res.get('product_uom_qty', 0) * self.product_qty
        # if product_id

        res['kategori_id'] = bom_line.kategori_id.id
        res['product_uom_qty'] = to_consume # Customize To Consume
        res['location_id'] = bom_line.location_id.id
        res['kategori_obat'] = bom_line.kategori_obat
        res['kode_benang'] = bom_line.product_id.default_code
        res['lot_id'] = bom_line.lot_id.id
        res['type'] = bom_line.type
        # res['move_line_ids'] = [(0, 0, {'lot_id': bom_line.lot_id.id, 'location_id': self.location_src_id, ''})]
        print('resss', res)
        return res

    @api.onchange('type_id')
    def onchange_type_id(self):
        type = self.type_id
        # if type.id:
   
        res = {}
        res['domain'] = {'product_id': [('categ_id', 'in', type.finished_product_category_ids.ids)],"mkt_id":[('type_marketing','=','manufacture'),('production_type','=',self.type_id.id),('state','=','confirm')]}
        return res





    # def insert_process(self):
        # self.ensure_one()
        # production_id = self.id
        # import logging;
        # _logger = logging.getLogger(__name__)
        # wo_dyeing = self.workorder_ids.filtered(lambda x:x.workcenter_id.is_production)
        # # wo_dyeing = self.workorder_ids._origin.filtered(lambda x:x.workcenter_id.is_production)
        # for wo in wo_dyeing:
            # # query = "UPDATE mrp_workorder SET process_type = %s WHERE production_id = %s and is_planning = True"%(self.process_type.id,self.id)
            # # self._cr.execute(query)
            # _logger.warning('='*40)
            # _logger.warning('MESSAGE')
            # _logger.warning(self.process_type.id)
            # _logger.warning(self._origin.process_type.id)
            # _logger.warning('='*40)
            # wo.write({'process_type':self.process_type.id})
            # wo.write({'process_type':self.process_id.id})
            # wo.process_type = self.process_type.id
        
    # @api.onchange('process_type')
    # def onchange_process_type(self):
        # self.insert_process()




    def write(self,vals):
        res = super(MrpProduction,self).write(vals)
        if 'process_type' in vals and self.state in ('draft','confirmed'):
            wo_dyeing = self.workorder_ids.filtered(lambda x:x.workcenter_id.is_production or x.workcenter_id.process_type_id)
            for wo in wo_dyeing:
                if wo.workcenter_id.process_type_id and wo.workcenter_id.process_type_id:
                    wo.write({'process_type':wo.workcenter_id.process_type_id.id})
                elif wo.workcenter_id.is_production:
                # if wo.workcenter_id.
                    wo.write({'process_type':self.process_type.id})
        if 'process_type' in vals and self.state in ('progress','to_close'):
            wo_dyeing = self.workorder_ids.filtered(lambda x:x.workcenter_id.is_production and x.state == 'ready')
            for wo in wo_dyeing:
                    wo.write({'process_type':self.process_type.id})
        return res

        # for mrp in self:
            # wo_dyeing = mrp.workorder_ids.filtered(lambda x:x.workcenter_id.is_production)
            # for wo in wo_dyeing:
                # wo.process_type = mrp.process_type.id
    
    @api.onchange('mkt_id')
    def onchange_mkt_id(self):
        type = self.type_id
        if self.type_id.id == 4 and self.mkt_id:
            self.picking_type_id = type.picking_type_id.id
            self.location_dest_id = type.finished_location.id
            self.location_src_id = type.component_location.id
            self.product_id = self.mkt_id.yarn_id.id
            self.product_qty = self.mkt_id.quantity
            self.order_penarikan_sw = self.mkt_id.order_pull_sw
            self.jenis_order = self.mkt_id.yarn_type
            self.jenis_mesin = self.mkt_id.weaving_mc_type
            self.note = self.mkt_id.note
        elif self.type_id.id == 6 and self.mkt_id:
            self.picking_type_id = type.picking_type_id.id
            self.location_dest_id = type.finished_location.id
            self.location_src_id = type.component_location.id
            self.product_id = self.mkt_id.yarn_id.id
            self.greige_id = self.mkt_id.greige_id.id
            self.location_id = self.mkt_id.location_id.id
            self.product_qty = self.mkt_id.quantity
            self.order_penarikan_sw = self.mkt_id.order_pull_sw
            self.note = self.mkt_id.note

    @api.onchange('bom_id')
    def onchange_bom_id(self):
        type = self.type_id
        if type:
            self.picking_type_id = type.picking_type_id.id
            self.location_dest_id = type.finished_location.id
            self.location_src_id = type.component_location.id
        
    
    def action_view_journal(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('ref', 'ilike', self.name)]
        action['context'] = {}
        return action

    
    def compute_journal_count(self):
        count = self.env['account.move'].search_count([('ref', 'ilike', self.name)])
        self.journal_count = count
    
    def split_list_id(self, table):
        wo_ids = self.workorder_ids.sorted(lambda x: x.name).mapped('parameter_ids.id')
        count_id = len(wo_ids)
        split = round(count_id / 2)
        if table == 'table_1':
            return wo_ids[0:split]
        if table == 'table_2':
            return wo_ids[split:]

    def action_print_resep(self):
        ctx = self.env.context
        # active_ids = ctx.get('active_ids')
        # url = "/report/pdf/inherit_mrp.report_mrp_print_resep/%s" % (','.join(list(map(str, active_ids))))
        # return {
        #     'name': 'Print Resep',
        #     'type': 'ir.actions.act_url',
        #     'url': url,
        #     'target': 'new',
        # }
        # print('action_print_resep==================')
        # ctx = self.env.context
        # active_ids = ctx.get('active_ids')
        # print('active_ids', active_ids)
        # url = "/report/pdf/inherit_mrp.report_mrp_print_resep/%s" % (','.join(list(map(str, active_ids))))
        # return {
        #     'name': 'Print Resep',
        #     'type': 'ir.actions.act_url',
        #     'url': url,
        #     'target': 'new',
        # }
        self.browse(ctx.get('active_ids')).write({'is_print_resep': True})
        return self.env.ref('inherit_mrp.action_mrp_production_resep').report_action(self)

    def action_print_scouring(self):
        ctx = self.env.context
        self.browse(ctx.get('active_ids')).write({'is_print_resep_scouring': True})
        return self.env.ref('inherit_mrp.action_mrp_production_scouring').report_action(self)

    def group_by_resep(self):
        # query = """
        #             select
        #             sm.type as type
        #             from stock_move sm
        #             where raw_material_production_id = %s and type is not null
        #             GROUP BY sm.type
        #             ORDER BY sm.type
        #         """ % (self.id)
        # self._cr.execute(query)
        # res = self._cr.dictfetchall()
        print('group_by_resep', sorted(set(self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.id != 127).mapped('product_id.categ_id.name'))))
        return sorted(set(self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.id != 127).mapped('product_id.categ_id.name')))
    
    def get_raw_chemical(self):
        move_raw_ids = []
        
        def sort_move(move):
            return move['recipe_category']
        for move in self.move_raw_ids.filtered(lambda x: x.product_id.categ_id.id != 127):
            # category_id = 121 | 1.OBAT DYE- STUFF
            # category_id = 147 | 2.OBAT PEMBANTU CELUP
            # category_id = 148 | 3.OBAT FINISHING
            _type = ''
            if not move.type and move.product_id.categ_id.id == 121:
                _type = 'DISPERSE'
            elif not move.type and move.product_id.categ_id.id == 147:
                _type = move.kelompok_id.name
            elif not move.type and move.product_id.categ_id.id == 148:
                _type = 'FINISH'
            elif move.type and move.type == 'opc':
                _type = move.kelompok_id.name
            else:
                _type = move.type
                
            move_raw_ids += [{
                "product_category": move.product_id.categ_id.name,
                "recipe_category": _type,
                "default_code": move.product_id.default_code,
                "product": move.product_id.name,
                "chemical_conc": move.chemical_conc,
                "quantity_done": move.quantity_done,
            }]
        move_raw_ids.sort(key=sort_move)
        return move_raw_ids
        # return move_raw_ids.sort(key=sort_move)
                
                
                
            
    
    def action_reprocess(self):
        print('action_reprocess')

    def action_saw_reprocess(self):
        print('action_saw_reprocess')
        
    # @api.onchange('jenis_order')
    # def ganti_domain_product(self):
    #     if self.jenis_order:
    #         self.product_id = False
    #         return {'domain':{'product_id': [('categ_id', '=', 164 if self.jenis_order == 'lusi' else 162)]},} #BENANG LUSI TWISTING


    
    
    def action_view_stock_move_line(self):
        # _logger.warning('='*40)
        return {
            'res_model' : 'stock.move.line',
            'type'      : 'ir.actions.act_window',
            'name'      : _("Stock Move Line"),
            'domain'    : [('production_id', '=', self.id)],
            'view_mode' : 'tree,form',
        }
    
    def apply_to_reprocess(self):
        for rec in self.browse(self.env.context.get('active_ids', False)):
            rec.write({
                'is_failed_need_approve_lab': False,
                'was_request_reprocess': True,
                })

    def unreprocess(self):
        for rec in self.browse(self.env.context.get('active_ids', False)):
            rec.write({'is_failed' : False, 'is_failed_need_approve_lab': False})

    def open_wizard_chemical_fix(self):
        action = self.env.ref('inherit_mrp.mrp_chemical_fix_failed_action').read()[0]
        action['res_id'] = self.id
        if self.reprocess_count >=2:
            return self.env.ref('inherit_mrp.reprocess_wo_wizard_action').sudo().read()[0]
        return action
    
    def save_and_apply(self):
        if self.temp_program_id:
            self.workorder_id.write({'program_id': self.temp_program_id.id})
            self.temp_program_id = False
        self.write({'is_failed_need_approve_lab': False, 'was_request_reprocess': True, 'tgl_keluar_lab':fields.Date.today()})

    def save_and_apply_saw(self):
        self.write({'scan_additional_workcenter': 'planning'})

    def action_save(self):
        self.ensure_one()
        if self.temp_program_id:
            self.workorder_id.write({'program_id': self.temp_program_id.id})
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def update_is_printed(self):
        self.write({'is_printed': True})

    # Override From base odoo
    def _pre_button_mark_done(self):
        productions_to_immediate = self._check_immediate()
        if productions_to_immediate:
            return productions_to_immediate._action_generate_immediate_wizard()

        for production in self:
            if float_is_zero(production.qty_producing, precision_rounding=production.product_uom_id.rounding):
                raise UserError(_('The quantity to produce must be positive!'))
            # if not any(production.move_raw_ids.mapped('quantity_done')):
            #     raise UserError(_("You must indicate a non-zero amount consumed for at least one of your components"))

        consumption_issues = self._get_consumption_issues()
        if consumption_issues:
            return self._action_generate_consumption_wizard(consumption_issues)

        quantity_issues = self._get_quantity_produced_issues()
        if quantity_issues:
            return self._action_generate_backorder_wizard(quantity_issues)
        return True
    # End Override From base odoo

    def open_saw_input_obat(self):
        action = self.env.ref('inherit_mrp.mrp_saw_input_obat_action').read()[0]
        action['res_id'] = self.id
        return action
    
    def generate_obat_add(self):
        if self.process_type_add:
            self.saw_input_obat_setup_ids = False
            self.write({
                'saw_input_obat_setup_ids': [(0, 0, {
                    'product_id': opc.product_id.id,
                    'quantity': opc.qty,
                    # 'type': ,
                    'kelompok': opc.kelompok_id.id, 
                }) for opc in self.process_type_add.line_ids]
            })
            action = self.env.ref('inherit_mrp.mrp_saw_input_obat_action').read()[0]
            action['res_id'] = self.id
            return action

    def open_mo_sizing_form(self):
        return {
            'res_model' : 'mrp.production',
            'res_id'    : self.id,
            'type'      : 'ir.actions.act_window',
            'view_mode' : 'form',
            'view_id'   : self.env.ref('inherit_mrp.mrp_production_sizing_form').id,
        }

    def open_mo_weaving_form(self):
        return {
            'res_model' : 'mrp.production',
            'res_id'    : self.id,
            'type'      : 'ir.actions.act_window',
            'view_mode' : 'form',
            'view_id'   : self.env.ref('inherit_mrp.mrp_production_weaving_form').id,
        }

