from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta ,datetime
import logging
import json
_log = logging.getLogger(__name__)


class ManufacturingRequest(models.Model):
    _name = 'mrp.request'
    _description = 'Material Production Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # @api.onchange('sale_id')
    # def _get_sale_order_line(self):
    #     for request in self:
    #         request.order_temp_ids = False
    #         for line in request.sale_id.order_line:
    #             request.order_temp_ids = [(0,0,{
    #                 "product_id":line.product_id.id,
    #                 "order_line_id":line.id,
    #                 "sale_id":line.order_id.id,
    #                 "mrp_request_id":self.id,
    #                 "product_uom_id":line.product_uom.id,
    #                 "quantity":line.product_uom_qty,
    #                 "remaining_qty":line.remaining_qty,
    #                 "state":line.state
    #             })]

    def action_add_process(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Process',
            'res_model': 'add.process.wizard',
            'view_mode': 'form',
            'context': {'default_mrp_request_id':self.id},
            'target': 'new',
        }
        
        
        
    
    
    def _update_sale_order_line(self):
        for request in self:
            request.order_line_ids = False
            for line in request.order_temp_ids:
                request.update({"order_line_ids": [(4,line.order_line_id.id)]})
    
    @api.depends('quantity','shrinkage_id')
    def _compute_quantity_shrinkage(self):
        for request in self:
            shrinkage = 0
            if request.quantity > 0 and request.shrinkage_id:
                shrinkage = request.quantity * request.shrinkage_id.percentage / 100
            request.quantity_shrinkage = request.quantity + shrinkage
            
    name                 = fields.Char(string='Name', default=lambda self: _('New'))
    state                = fields.Selection([('draft', 'Draft'),('confirm', 'Confirm'),('done', 'Done')], string='Status', default='draft')
    partner_id           = fields.Many2one('res.partner', string='Customer')
    production_type_id   = fields.Many2one('mrp.type', string='Production Type')
    sale_id              = fields.Many2one('sale.order', string='Sale Order')
    td_id                = fields.Many2one(related='sale_id.hanger_code', string='TD')
    process_type         = fields.Many2one(related='td_id.process_type', string='Process Type')
    process_category_id  = fields.Many2one(related='process_type.category_id', string='Process Category')
    sale_qty             = fields.Float(related='sale_id.amount_qty', string='Sale Quantity')
    tanggal              = fields.Date(string='Date', required=True
    # default=fields.Date.today()
    )
    jumlah_spk           = fields.Integer(string='Jumlah Spk')
    product_id           = fields.Many2one('product.template', string='Product')
    
    # 
    component_type       = fields.Selection([("one","One Kind"),("combine","Combine")], string='Component Type')
    component_ids        = fields.One2many('mrp.request.component', 'mrp_request_id', string='Component')
    yarn_template_id     = fields.Many2one('product.template', string='Yarn Template',domain=[('categ_id.name', 'ilike', '%benang%')])
    yarn_id              = fields.Many2one(comodel_name='product.product', string='Product',domain=[('categ_id.name', 'ilike', '%benang%')])
    yarn_stock_ids       = fields.One2many('mrp.yarn.stock', 'mrp_request_id', string='Yarn Stock')
    sisir_id             = fields.Many2one('master.sisir', string='Sisir')
    total_end            = fields.Integer(string='Total End')
    total_creel          = fields.Integer(string='Creel')
    total_beam           = fields.Integer(string='Total Beam')
    sale_line_ids        = fields.One2many(string='Orders',related="sale_id.order_line")
    order_line_ids       = fields.Many2many(comodel_name='sale.order.line', string='Order Line' ,compute="_update_sale_order_line")
    order_temp_ids       = fields.One2many('sale.order.line.temp', 'mrp_request_id', string='Order Detail')      
    machine_temp_ids     = fields.One2many('machine.planning.temp', 'mrp_request_id', string='Machine Plan')      
    machine_id           = fields.Many2one('mrp.machine', string='Machine')    
    greige_mkt_ids       = fields.Many2many(comodel_name='product.template', relation='greige_id_rel',column1='matang_id', compute='_compute_greige_mkt_ids',)

    greige_template_id   = fields.Many2one('product.template', string='Greige Template',
        domain="[('categ_id.name', '=', 'GREY')]"
    )
    greige_id            = fields.Many2one('product.product', string='Greige Name',
        # domain="[('categ_id.name', '=', 'GREY'), ('kd_product_mkt_id', 'in', greige_mkt_ids)]"
    )
    # greige_name         = fields.Many2one('product.product',string='Nama Greige/Corak',domain=[('categ_id.name', 'in', ('greige', 'GREY'))])

    picking_ids          = fields.Many2many('stock.picking', compute='_compute_picking', string='Request Greige', copy=False,)
    picking_count        = fields.Integer(compute='_compute_picking', string='Picking count', default=0,)
    greige_stock_ids     = fields.One2many('mrp.greige.stock', 'mrp_request_id', string='Greige Stock')
    shrinkage_id         = fields.Many2one('mrp.shrinkage', string='Shrinkage')
    shrinkage_percentage = fields.Float(string='Shrinkage Percentage',related='shrinkage_id.percentage')
    quantity_shrinkage   = fields.Float(string='Quantity With Shrinkage',compute='_compute_quantity_shrinkage')
    mrp_picking_type     = fields.Many2one('stock.picking.type', string='Manufacture',domain=[('default_location_src_id.location_id.complete_name', 'ilike', '%GPD%'),('code','=','mrp_operation')])
    benang_id            = fields.Many2one('product.product', string='Produk Beam')
    kode_benang          = fields.Char(related="benang_id.default_code", string='Kode Benang')
    berat_per_cones      = fields.Float(string='Berat Per Cones')
    lot_id               = fields.Many2one('stock.production.lot', string='Lot')
    beam_product_id      = fields.Char(string='Create Beam')
    
    #fix me waving only
    pakan               = fields.Char(string='Pakan')
    std_susut           = fields.Float(string='Std Susut')
    pic                 = fields.Integer(string='Pic')
    gramasi             = fields.Integer(string='Gramasi')
    lebar               = fields.Integer(string='Lebar')
    density             = fields.Integer(string='Density')
    sale_type           = fields.Selection(string='Sale Type',related='sale_id.sale_type')
    handling            = fields.Selection(string='Handling',related='sale_id.handling')
    handling_id         = fields.Many2one('master.handling', string='Master Handling', related='sale_id.handling_id')
    
    quantity            = fields.Float(string='Quantity', required=True)
    quantity_greige     = fields.Float(string='Quantity (Greige)', required=True, )
    uom_id              = fields.Many2one('uom.uom', string='Uom', required=True, default=46 ,domain=[('category_id','=',4)])
    bom_id              = fields.Many2one('mrp.bom', string='BoM')
    picking_type_id     = fields.Many2one('stock.picking.type', string='Operation Type', related='production_type_id.picking_type_id')
    component_location  = fields.Many2one('stock.location', string='Component Location', related='production_type_id.component_location')
    finished_location   = fields.Many2one('stock.location', string='Finished Location', related='production_type_id.finished_location')
    finished_product_category_ids = fields.Many2many('product.category', string='Finished Product Category', related='production_type_id.finished_product_category_ids')
    location_id         = fields.Many2one('stock.location', string='Department',domain=[('usage', '=', 'internal')])
    detail_ids          = fields.One2many('mrp.request.detail', 'mrp_request_id', string='Detail')
    mrp_ids             = fields.One2many('mrp.production', 'mrp_request_id', string='Manufacturing Order')
    batched_count       = fields.Integer(string='Batched',compute="_count_batch")
    multiplier          = fields.Integer(string='Multiplier', default=1) 
    component_product_category_ids = fields.Many2many(
        comodel_name='product.category', 
        string='Component Product Category',
        related='production_type_id.component_product_category_ids'
        )
    

    mkt_production_id   = fields.Many2one('mkt.production.line', string='Mkt Production')
    type_twist          = fields.Selection([("interlace","Interlace"),("tfo","TFO")], string='Type Twist')
    revisi              = fields.Integer(string='Revisi')
    qty_mkt             = fields.Float(string='Total Order')
    qty_tarik           = fields.Float(string='Order Penarikan SW')
    yarn_type           = fields.Selection([("lusi","Lusi"),("pakan","Pakan")], string='Yarn Type')
    weaving_mc_type     = fields.Selection([("wjl","WJL"),("shuttle","Shutter")], string='Weaving Machine Type')
    so_line_temp        = fields.Many2many('sale.order.line', string='Detail', store=False, compute="_compute_so_line_temp")
    sale_order_line_ids = fields.Many2many('sale.order.line', string='Detail',domain="[('id','in',so_line_temp)]")    
    std_potong          = fields.Float(string='Standar Potong', related='greige_id.std_potong')
    berat_greige        = fields.Float(string='Berat Greige (Kg)', compute='_compute_berat_greige')
    domain_greige_id    = fields.Char(string='Domain Greige',compute="_compute_domain_greige")
    jml_mesin           = fields.Float(string='Jumlah Mesin')
    lot_benang_id       = fields.Many2one('stock.production.lot', string='Lot Benang')
    # mkt_product_id      = fields.Many2one('product.template', string='Product MKT', related='sale_id.greige_id.mkt_product_id', store=False,) 
    # kontruksi_id         = fields.Many2one('kontruksi', string="Konstruksi")   
    
    
    def _compute_domain_greige(self):
        for line in self:
            line.domain_greige_id = json.dumps([('kd_product_tmpl_mkt_id','=',line.product_id.id)])
            
    
    
    
    # @api.onchange('mkt_production_id')
    # def get_mkt_production_id(self):
    #     for rec in self:
    #         print(rec.mkt_production_id.name)
            # rec.qty_mkt = rec.mkt_production_id.quantity
            # rec.greige_id = rec.mkt_production_id.product_id.id
    
    def _count_batch(self):
        for request in self:
            request.batched_count = len(request.mrp_ids)
        
        
    @api.onchange('greige_id')
    def get_quants(self):
        if not self.greige_id:
            self.greige_stock_ids = False 
        variant_ids = self.env['product.product'].search([('kd_product_mkt_id','in',self.greige_mkt_ids.ids)])
        if self.greige_stock_ids:
            variant_ids = variant_ids.filtered(lambda x:x.id not in [ product.id for  product in self.greige_stock_ids.mapped('greige_id')])
        for variant in variant_ids:
            self.greige_stock_ids = [(0,0,{
                "mrp_request_id":self.id,
                "greige_id":variant.id,
            })]
            
            
    def create_bom(self,product):
        bom = self.env['mrp.bom'].create({
            "product_tmpl_id": product.product_tmpl_id.id,
            "product_id": product.id,
            "type":"normal",
            "location_destinaion":self.production_type_id.component_location.id,
            
        })
    
    
    
    def request_material(self):
        for production in self.mrp_ids:
            if self.production_type_id.id == 2:
                self.env['stock.picking'].sudo().create({
                    "scheduled_date": production.date_planned_start,
                    "picking_type_id":self.production_type_id.component_greige_picking_type_id.id,
                    "location_id":self.production_type_id.component_greige_location.id,
                    "location_dest_id":self.mrp_picking_type.default_location_src_id.id,
                    # "location_dest_id":self.production_type_id.component_location.id,
                    "mrp_request_id": self.id,
                    "production_id": production.id,
                    # "greige_qty_req":sum(production.move_raw_ids.filtered(lambda x:x.product_id.categ_id.name == 'GREY').mapped('product_uom_qty')),
                    "origin": production.name,
                    "move_ids_without_package":[(0,0, {
                        "name":self.greige_id.name,
                        "product_id":self.greige_id.id,
                        "product_uom_qty":self.quantity_greige,
                        "product_uom":self.greige_id.uom_id.id,
                        "location_id":self.production_type_id.component_greige_location.id,
                        # "location_dest_id":self.production_type_id.component_location.id,
                        "location_dest_id":self.mrp_picking_type.default_location_src_id.id,
                        "move_dest_ids":[(4,move.id) for move in production.move_raw_ids.filtered(lambda x: x.product_id.categ_id.name == "GREY")]
                    })]
                })
            else:
                # TWISTING
                self.env['stock.picking'].create({
                    "picking_type_id"   : self.picking_type_id.id,
                    "location_id"       : self.component_location.id,
                    "location_dest_id"  : self.finished_location.id,
                    "mrp_request_id"    : self.id,
                    "production_id"     : production.id,
                    "origin"            : production.name,
                    "move_line_ids_without_package":[(0,0, {
                        "lot_id"            : move.lot_id.id,
                        "product_id"        : move.product_id.id,
                        "product_uom_qty"   : move.product_uom_qty,
                        "product_uom_id"    : move.product_id.uom_id.id,
                        "location_id"       : self.component_location.id,
                        "location_dest_id"  : self.finished_location.id,
                    }) for move in production.move_raw_ids]
                })
    
    @api.depends('mrp_ids')
    def _compute_picking(self):
        for request in self:
            pickings = self.env['stock.picking'].search([('mrp_request_id','=',request.id)])
            request.picking_count = len(pickings)
            request.picking_ids = pickings
    
    

    @api.onchange('mrp_ids','mrp_ids.process_type')
    def _onchange_mrp_ids(self):
        for mrp in self.mrp_ids:
            if mrp.process_type:
                wo_dyeing = mrp.workorder_ids.filtered(lambda x:x.workcenter_id.is_production)
                for wo in wo_dyeing:
                    wo.write({"process_type":mrp.process_type.id})



    @api.onchange('sale_id')
    def get_partner_id(self):
        self.partner_id         = self.sale_id.partner_id.id
        self.greige_template_id = self.sale_id.greige_id.id 
        self.product_id         = self.sale_id.product_id.id 
        self.production_type_id = 2 if self.sale_id else False
        self.gramasi            = self.sale_id.gramasi if self.sale_id else False
        self.lebar              = self.sale_id.lebar if self.sale_id else False
        self.handling           = self.sale_id.handling if self.sale_id else False
        self.density            = self.sale_id.density if self.sale_id else False
        self.sale_order_line_ids = False
        self.order_temp_ids = False
        for line in self.sale_id.order_line:
            if line.design_id.id != self.sale_id.design_id.id:
                raise UserError('Cek kembali kd design di sales order marketing !! ')
            line.onchange_production_ids()
    
    @api.depends('sale_id')
    def _compute_so_line_temp(self):
        if self.sale_id:
            self.so_line_temp = self.sale_id.order_line.filtered(lambda x: x.remaining_qty > 0 and x.state in ('draft','confirm')).ids
        else:
            self.so_line_temp = False

    
    @api.onchange('sale_order_line_ids')
    def _onchange_sale_order_line_ids(self):
        order_temp_ids = []
        for line in self.sale_order_line_ids:
            if line not in self.order_temp_ids.mapped('order_line_id'):
                
                order_temp_ids += [(0,0,{
                    "product_id":line.product_id.id,
                    "order_line_id":line._origin.id,
                    "sale_id":line.order_id.id,
                    "mrp_request_id":self.id,
                    "product_uom_id":line.product_uom.id,
                    "quantity":line.product_uom_qty,
                    "remaining_qty":line.remaining_qty,
                    "state":line.state
                })]
                
        for line in self.order_temp_ids:
                if line.order_line_id.id not in self.sale_order_line_ids.mapped('id'):
                    order_temp_ids += [(3,line.id,0)]
        
        self.order_temp_ids = order_temp_ids
        
        
    
    
    def action_draft(self):
        self.state = 'draft'
        for picking in self.picking_ids:
            picking.unlink()
            
        for production in self.mrp_ids:
            production.write({"move_raw_ids":False})
        
        self.machine_temp_ids = False
            
        
        
    def action_view_picking(self):
        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        pick_ids = self.mapped('picking_ids')
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,view) for state,view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result
        
    

    def action_confirm(self):
        if self.production_type_id.id == 2:
            sol = self.order_temp_ids
            if sol and self.production_type_id.name == 'DYEING':
                if self.quantity > min(sol.mapped('remaining_qty')):
                    raise ValidationError("Mohon maaf quantity batch melebihi quantity sisa order marketing")
            if not self.order_temp_ids:
                raise ValidationError('Harap isi detail warna terlebih dahulu!')        
            if not self.mrp_ids:
                mrp_ids = []
                machine_plan = []
                for line in self.order_temp_ids:
                    qty_kg_greige =  (self.gramasi / 1000 * self.lebar / 100) * 0.9144 * self.quantity_greige
                    
                # for line in self.order_temp_ids.filtered(lambda x: x.remaining_qty >= self.quantity):
                    bom_id = self.env['mrp.bom'].search([('product_id','=',line.product_id.id),('td_id','=',self.sale_id.hanger_code.id)], limit=1)
                    color_final = self.env['labdip.color.final'].sudo().search([('color_id','=',line.product_id.color_id.id),('labdip_id','=',self.sale_id.design_id.labdip_id.id)],limit=1)
                    
                    if self.sale_id.design_id.labdip_id:
                        for design_line in self.sale_id.design_id.line_ids.filtered(lambda x: x.variant_id.id == line.product_id.id):
                            design_line.sudo().write({"greige_id":self.greige_id.id})
                    
                        
                    
                    if bom_id:
                        bom_id.write({
                            "picking_type_id":self.mrp_picking_type.id,
                            "labdip_id":self.sale_id.design_id.labdip_id.id,
                            "td_id":self.sale_id.hanger_code.id,
                            "location_id":self.mrp_picking_type.default_location_src_id.id,
                            
                        })
                        
                        # if not bom_id.operation_ids:
                        
                        bom_id.action_set_to_draft()
                        

                        bom_id.update({'material_td_ids': False, 'mrp_first_compenent_ids': False, 'bom_line_ids': False}) # delete material Td, lab, operations
                        bom_id.update({
                                            "mrp_first_compenent_ids":[(0,0,{"product_id":self.greige_id.id,
                                            "quantity":self.quantity_greige,
                                            "quantity_finish":self.quantity_greige,
                                            "product_uom_id":self.greige_id.uom_id.id,
                                            "location_id":self.mrp_picking_type.default_location_src_id.id
                                            # "location_id":self.production_type_id.finished_location.id
                                            })],  
                        })
                        bom_id.action_get_material_td(self.mrp_picking_type.default_location_src_id.id)
                        
                        bom_id.action_get_material_lab(self.mrp_picking_type.default_location_src_id.id,{
                            "qty_kg_greige":qty_kg_greige,
                        })
                        bom_id.action_confirm()
                        
                        # bom_line_ids = bom_id.bom_line_ids.filtered(lambda x:x.product_id.categ_id.id == 127)
                        # first_line_ids = bom_id.mrp_first_compenent_ids.filtered(lambda x:x.product_id.categ_id.id == 127)
                        # if len(bom_line_ids) > 0:
                        #     for bomline in bom_line_ids:
                        #         bomline.write({"product_id":self.greige_id.id,
                        #                     "product_qty":self.quantity_shrinkage,
                        #                     "product_uom_id":self.greige_id.uom_id.id,
                        #                     "location_id":self.production_type_id.finished_location.id})
                        # else:
                        #     bom_id.write({
                        #                     "bom_line_ids":[(0,0,{"product_id":self.greige_id.id,
                        #                     "product_qty":self.quantity_shrinkage,
                        #                     "product_uom_id":self.greige_id.uom_id.id,
                        #                     "location_id":self.production_type_id.finished_location.id})]})
                            
                        # if len(first_line_ids) > 0:
                        #     for fistline in first_line_ids:
                        #         fistline.write({"product_id":self.greige_id.id,
                        #                     "quantity":self.quantity_shrinkage,
                        #                     "product_uom_id":self.greige_id.uom_id.id,
                        #                     "location_id":self.production_type_id.finished_location.id})
                        # else:
                        #     bom_id.write({"mrp_first_compenent_ids":[(0,0,{"product_id":self.greige_id.id,
                        #                     "quantity":self.quantity_shrinkage,
                        #                     "product_uom_id":self.greige_id.uom_id.id,
                        #                     "location_id":self.production_type_id.finished_location.id})]})
                    else:
                        bom_id = bom_id.create({"product_tmpl_id":self.product_id.id,
                                                "product_id":line.product_id.id,
                                                "location_id":self.production_type_id.finished_location.id,
                                                "type":"normal",
                                                "picking_type_id":self.mrp_picking_type.id,
                                                "location_id":self.mrp_picking_type.default_location_src_id.id,
                                                
                                                
                                                "labdip_id":self.sale_id.design_id.labdip_id.id,
                                                "color_final_id": color_final.id,
                                                "td_id":self.sale_id.hanger_code.id,
                                                "product_uom_id":line.product_id.uom_id.id,
                                                "mrp_first_compenent_ids":[(0,0,{"product_id":self.greige_id.id,
                                                    "quantity":self.quantity_shrinkage,
                                                    "quantity_finish":self.quantity_shrinkage,
                                                    
                                                    "product_uom_id":self.greige_id.uom_id.id,
                                                    "location_id":self.mrp_picking_type.default_location_src_id.id
                                                    # "location_id":self.production_type_id.finished_location.id
                                                    })],
                                                # "bom_line_ids":[(0,0,{"product_id":self.greige_id.id,
                                                #     "product_qty":self.quantity_shrinkage,
                                                #     "product_uom_id":self.greige_id.uom_id.id,
                                                #     "location_id":self.production_type_id.finished_location.id})]
                                            })
                        # bom_id.action_set_to_draft()
                        bom_id.action_get_material_td(self.mrp_picking_type.default_location_src_id.id)
                        bom_id.action_get_material_lab(self.mrp_picking_type.default_location_src_id.id,{
                            "qty_kg_greige":qty_kg_greige,
                        })
                        bom_id.action_confirm()
                        
                    multiplier = self.multiplier
                    if multiplier > 0:
                        workorder_list = []
                        for work in bom_id.operation_ids:
                            param = [(0, 0, {'parameter_id': b.parameter_id.id, 'no_urut':b.no_urut, 'plan':b.plan,
                            'actual':b.actual, 'uom_id':b.uom_id.id}) for b in work.routing_paramter_ids]
                            duration = work.program_id.duration
                            dt = timedelta(minutes=duration) if work.program_id else False
                            dt_st = datetime.combine(self.tanggal, datetime.min.time())
                            dt_finished = datetime.combine(self.tanggal, datetime.min.time()) + dt if dt else False
                            
                            
                            workorder_list.append((0, 0, {"name": work.name,
                                            "workcenter_id": work.workcenter_id.id,
                                            "mesin_id": work.mesin_id.id,
                                            "program_id": work.program_id.id,
                                            "date_planned_start":dt_st,
                                            "date_planned_finished":dt_finished,
                                            "product_uom_id": self.uom_id.id,
                                            "consumption": 'flexible',
                                            "parameter_ids": param}))
                        for a in range(multiplier):
                            type_id          = self.env['mrp.type'].browse(self.production_type_id.id)
                            mo_name          = type_id.production_sequence_id.next_by_id()
                            lot_producing_id = self.env['stock.production.lot'].sudo().create({
                                    "name": mo_name,
                                    "inspect_date":self.tanggal,
                                    "tanggal_produksi":self.tanggal,
                                    "location_id":self.mrp_picking_type.default_location_dest_id.id,
                                    "product_id":line.product_id.id,
                                    "company_id":self.env.user.company_id.id
                                })
                            dt_start = datetime.combine(self.tanggal, datetime.min.time())
                            dt_end = datetime.combine(self.tanggal, datetime.max.time())
                            import logging;
                            _logger = logging.getLogger(__name__)
                            _logger.warning('='*40)
                            _logger.warning('MESSAGE')
                            _logger.warning(dt_start)
                            _logger.warning(dt_end)
                            _logger.warning(fields.Datetime.subtract(dt_start,hours=1))
                            _logger.warning(fields.Datetime.subtract(dt_end,hours=1))
                            _logger.warning('='*40)
                            # start_working = timedelta(hours=6,minutes=30) 
                            # dt_start =  dt_start + start_working 
                            
                            mrp_ids.append((0,0,{
                                "name":mo_name,
                                "product_id":line.product_id.id,
                                "lot_producing_id": lot_producing_id.id,
                                "type_id":self.production_type_id.id,
                                "product_uom_id":self.uom_id.id,
                                "date_planned_start": dt_start,
                                "date_planned_finished": dt_end,
                                # "date_planned_start": fields.Datetime.subtract(dt_start,hours=1),
                                # "date_planned_finished": fields.Datetime.subtract(dt_end,hours=1),
                                "bom_id":bom_id.id,
                                "mrp_request_id":self.id,
                                "quantity_request": self.quantity_shrinkage,
                                "greige_id":self.greige_id.id,
                                "gramasi_kain_finish":self.gramasi,
                                "lebar_kain_finish":self.lebar,
                                "density_kain_finish":self.density,
                                "qty_yard_kp" :self.quantity_shrinkage,
                                "product_qty" :self.quantity_shrinkage,
                                # "qty_producing":self.quantity_shrinkage,
                                "sale_line_id":line.order_line_id.id,
                                "origin": self.name,
                                "sale_type":self.sale_type,
                                "mesin_id":self.machine_id.id,
                                "sale_id":self.sale_id.id,
                                "sc_id":self.sale_id.sc_id.id,
                                "picking_type_id":self.mrp_picking_type.id,
                                "location_src_id":self.mrp_picking_type.default_location_src_id.id,
                                "location_dest_id":self.mrp_picking_type.default_location_dest_id.id,
                                # "picking_type_id":self.production_type_id.picking_type_id.id,
                                # "location_src_id":self.production_type_id.component_location.id,
                                # "location_dest_id":self.production_type_id.finished_location.id,
                                # "move_raw_ids": [(0,0,{
                                #     "name":self.greige_id.name,
                                #     "product_id":self.greige_id.id,
                                #     "product_uom_qty":self.quantity_shrinkage,
                                #     "product_uom":self.greige_id.uom_id.id,
                                #     "location_id":self.production_type_id.component_location.id,
                                #     "location_dest_id":15,
                                #     })],
                                # "workorder_ids": workorder_list,
                                "no_urut_labdip_final" : color_final.no_urut
                                }))
                
                self.mrp_ids = mrp_ids
                for mrp in self.mrp_ids:
                    mrp.sale_line_id.onchange_production_ids()
                    mrp._onchange_bom_id()
                    mrp._onchange_move_raw()
                    mrp._onchange_move_finished()
                    mrp._onchange_workorder_ids()
                    mrp.get_parameter_process()
                    mrp.update({'product_qty': self.quantity_shrinkage})
                    mrp.action_confirm()
                    for wo in mrp.workorder_ids.filtered(lambda x:x.workcenter_id.is_planning):
                        machine_plan.append((0,0,{
                            "production_id":wo.production_id.id,
                            "workorder_id":wo.id,
                        }))
                        
                        
                    

                
                self.machine_temp_ids = machine_plan
                
                    # raise UserError('Quantity Request more than outstanding !!!')
            else:
                for production in self.mrp_ids:
                    # production.write({"move_raw_ids": [(0,0,{
                    #             "name":self.greige_id.name,
                    #             "product_id":self.greige_id.id,
                    #             "product_uom_qty":self.quantity_shrinkage,
                    #             # "mesin_id":self.machine_id.id,
                    #             "product_uom":self.greige_id.uom_id.id,
                    #             "location_id":self.production_type_id.component_location.id,
                    #             "location_dest_id":15,
                    #         })],})
                    production._onchange_bom_id()
                    production._onchange_move_raw()
                    production._onchange_move_finished()
                    production._onchange_workorder_ids()
                    production.get_parameter_process()
            self.request_material()

        elif self.production_type_id.id == 5: 
            if self.beam_product_id:
                product = self.env['product.product'].sudo().create({
                    "id" : self.id,
                    "name":self.beam_product_id,
                    "type":"product",
                    "categ_id":199,
                    "uom_id":self.uom_id.id,
                    "uom_po_id":self.uom_id.id,
                    "tracking":"lot",
                    "default_code":self.beam_product_id,
                })
                self.benang_id= product.id
                if not self.mrp_ids:
                    mrp_ids = []
                    machine_plan = []
                    bom_id = self.env['mrp.bom'].search([('product_id','=',self.benang_id.id)], limit=1)

                    if bom_id:
                            bom_id.write({
                                "picking_type_id":self.production_type_id.id,
                                "location_id":self.production_type_id.finished_location.id,
                                
                            })
                            
                            # if not bom_id.operation_ids:
                            
                            bom_id.action_set_to_draft()
                            
                            bom_id.action_confirm()
                    
                    else:
                            bom_id = bom_id.create({"product_tmpl_id":self.benang_id.product_tmpl_id.id,
                                                    "product_id":self.benang_id.id,
                                                    "location_id":self.production_type_id.finished_location.id,
                                                    "type":"normal",
                                                    "picking_type_id":self.production_type_id.id,
                                                    "location_id":self.production_type_id.finished_location.id,
                                                    "product_uom_id":self.benang_id.uom_id.id,
                                                })
                            bom_id.action_confirm()
                            
                        
                    jumlah_spk = self.jumlah_spk
                    kode_prod = ''
                    if self.machine_id.id in [1969, 1971]:
                        kode_prod = 'A'
                    elif self.machine_id.id in [2185, 2186, 1970]:
                        kode_prod = 'B'
                    elif self.machine_id.id in [2187, 2184, 1972]:
                        kode_prod = 'D'
                
                    if jumlah_spk > 0:

                        for a in range(jumlah_spk):
                            type_id          = self.env['mrp.type'].browse(self.production_type_id.id)
                            mo_name          = type_id.production_sequence_id.next_by_id()
                            lot_producing_id = self.env['stock.production.lot'].sudo().create({
                                    "name": mo_name,
                                    "inspect_date":self.tanggal,
                                    "tanggal_produksi":self.tanggal,
                                    "location_id":self.mrp_picking_type.default_location_dest_id.id,
                                    "product_id":self.benang_id.id,
                                    "company_id":self.env.user.company_id.id
                                })
                            dt_start = datetime.combine(self.tanggal, datetime.min.time())
                            dt_end = datetime.combine(self.tanggal, datetime.max.time())
                            import logging;
                            _logger = logging.getLogger(__name__)
                            _logger.warning('='*40)
                            _logger.warning('MESSAGE')
                            _logger.warning(dt_start)
                            _logger.warning(dt_end)
                            _logger.warning(fields.Datetime.subtract(dt_start,hours=1))
                            _logger.warning(fields.Datetime.subtract(dt_end,hours=1))
                            _logger.warning('='*40)
                            # start_working = timedelta(hours=6,minutes=30) 
                            # dt_start =  dt_start + start_working 
                            
                            raw_data = []
                            if self.component_type == 'one':
                                raw_data.append(
                                    (0,0,{
                                        "name":self.yarn_id.name,
                                        "product_id":self.yarn_id.id,
                                        "kode_benang":self.yarn_id.default_code,
                                        "product_uom_qty":self.quantity_shrinkage,
                                        "product_uom":self.yarn_id.uom_id.id,
                                        "location_id":self.production_type_id.finished_location.id,
                                        "location_dest_id":15,
                                        })
                                )
                            else:
                                for a in self.component_ids:
                                    raw_data.append(
                                        (0,0,{
                                        "name":a.yarn_id.name,
                                        "product_id":a.yarn_id.id,
                                        "kode_benang":a.yarn_id.default_code,
                                        "product_uom_qty":self.quantity_shrinkage,
                                        "product_uom":a.yarn_id.uom_id.id,
                                        "location_id":self.production_type_id.finished_location.id,
                                        "location_dest_id":15,
                                        })
                                    )
                            
                            mrp_ids.append((0,0,{
                                "name":mo_name,
                                "product_id":self.benang_id.id,
                                "lot_producing_id": lot_producing_id.id,
                                "type_id":self.production_type_id.id,
                                "product_uom_id":self.benang_id.uom_id.id,
                                "date_planned_start": dt_start,
                                "date_planned_finished": dt_end,
                                # "date_planned_start": fields.Datetime.subtract(dt_start,hours=1),
                                # "date_planned_finished": fields.Datetime.subtract(dt_end,hours=1),
                                "bom_id":bom_id.id,
                                "mrp_request_id":self.id,
                                # "greige_name":self.greige_name.id,
                                "quantity_request": self.quantity_shrinkage,
                                "greige_id":self.greige_id.id,
                                "sisir_id":self.sisir_id.id,
                                "total_end":self.total_end,
                                "total_creel":self.total_creel,
                                # "jml_beam_stand":self.jml_beam_stand,
                                # "gramasi_kain_finish":self.gramasi,
                                "lebar_kain_finish":self.lebar,
                                "density_kain_finish":self.density,
                                "qty_yard_kp" :self.quantity_shrinkage,
                                "product_qty" :self.quantity,
                                # "qty_producing":self.quantity_shrinkage,
                                # "sale_line_id":line.order_line_id.id,
                                "origin": self.name,
                                "sale_type":self.sale_type,
                                "machine_id":self.machine_id.id,
                                "location_id":self.production_type_id.finished_location.id,
                                "picking_type_id":self.production_type_id.picking_type_id.id,
                                "location_src_id":self.production_type_id.component_location.id,
                                "location_dest_id":self.production_type_id.finished_location.id,
                                "move_raw_ids": raw_data,
                                "beaming_ids": [(0,0,{
                                        "kode_prod" :kode_prod +'-' + self.env['ir.sequence'].next_by_code('kode.prod.beaming'),
                                        # "te_helai"  :self.total_end,
                                        # "jml_beam"  :self.jml_beam_stand,
                                        })],
                            }))
                        # return{
                            
                        # }
                    else :
                        raise UserError("Jumlah SPK harus lebih dari 0")
                    
                    
                    self.mrp_ids = mrp_ids
                    # _logger.warning('='*40)
                    # _logger.warning('='*40)
                    # _logger.warning('MESSAGE')
                    # _logger.warning(mrp_ids)
                    # _logger.warning('='*40)
                    # _logger.warning('='*40)
                    for mrp in self.mrp_ids:
                        mrp._onchange_bom_id()
                        mrp._onchange_move_raw()
                        # mrp._onchange_move_finished()
                        mrp.update({'product_qty': self.quantity_shrinkage})
                    
                    self.machine_temp_ids = machine_plan
                    
                        # raise UserError('Quantity Request more than outstanding !!!')
                else:
                    for production in self.mrp_ids:
                        # production.write({"move_raw_ids": [(0,0,{
                        #             "name":self.greige_id.name,
                        #             "product_id":self.greige_id.id,
                        #             "product_uom_qty":self.quantity_shrinkage,
                        #             # "mesin_id":self.machine_id.id,
                        #             "product_uom":self.greige_id.uom_id.id,
                        #             "location_id":self.production_type_id.component_location.id,
                        #             "location_dest_id":15,
                        #         })],})
                        production._onchange_bom_id()
                        production._onchange_move_raw()
                        # production._onchange_move_finished()
                        production._onchange_workorder_ids()
                        production.get_parameter_process()
                self.request_material()
                

        elif self.production_type_id.id == 3:    
            if not self.mrp_ids:
                mrp_ids = []
                machine_plan = []
                bom_id = self.env['mrp.bom'].search([('product_id','=',self.greige_id.id)], limit=1)

                if bom_id:
                        bom_id.write({
                            "picking_type_id":self.production_type_id.id,
                            "product_id":self.greige_id.id,
                            "location_id":self.production_type_id.finished_location.id,
                            "bom_line_ids":[(0,0,{"product_id":a.yarn_id.id,
                                                    "product_qty":self.quantity,
                                                    "product_uom_id":a.yarn_id.uom_id.id,
                                                    "location_id":self.production_type_id.component_location.id
                                                    })for a in self.component_ids]
                        })
                        
                        # if not bom_id.operation_ids:
                        
                        bom_id.action_set_to_draft()
                        

                        # bom_id.update({'material_td_ids': False, 'mrp_first_compenent_ids': False, 'bom_line_ids': False}) # delete material Td, lab, operations
                        # bom_id.update({
                        #                     "mrp_first_compenent_ids":[(0,0,{"product_id":self.benang_id.id,
                        #                     "quantity":self.quantity_greige,
                        #                     "quantity_finish":self.quantity_greige,
                        #                     "product_uom_id":self.benang_id.uom_id.id,
                        #                     "location_id":self.production_type_id.finished_location.id
                        #                     # "location_id":self.production_type_id.finished_location.id
                        #                     })],  
                        # })
                        # bom_id.action_get_material_td(self.mrp_picking_type.default_location_dest_id.id)
                        
                        # bom_id.action_get_material_lab(self.mrp_picking_type.default_location_dest_id.id,{
                        #     "qty_kg_greige":qty_kg_greige,
                        # })
                        bom_id.action_confirm()
                
                else:
                        bom_id = bom_id.create({"product_tmpl_id":self.greige_id.product_tmpl_id.id,
                                                "product_id":self.greige_id.id,
                                                "location_id":self.production_type_id.finished_location.id,
                                                "type":"normal",
                                                "picking_type_id":self.production_type_id.id,
                                                "product_uom_id":self.greige_id.uom_id.id,
                                                "bom_line_ids":[(0,0,
                                                    {"product_id":a.yarn_id.id,
                                                    "product_qty":self.quantity,
                                                    "product_uom_id":a.yarn_id.uom_id.id,
                                                    "location_id":self.production_type_id.component_location.id
                                                    })for a in self.component_ids]
                                                
                                                
                                                # "labdip_id":self.sale_id.design_id.labdip_id.id,
                                                # "color_final_id": color_final.id,
                                                # "td_id":self.sale_id.hanger_code.id,
                                                
                                                # "mrp_first_compenent_ids":[(0,0,{"product_id":self.greige_id.id,
                                                #     "quantity":self.quantity_shrinkage,
                                                #     "quantity_finish":self.quantity_shrinkage,
                                                    
                                                #     "product_uom_id":self.greige_id.uom_id.id,
                                                #     "location_id":self.production_type_id.finished_location.id
                                                #     # "location_id":self.production_type_id.finished_location.id
                                                #     })],
                                                
                                            })
                        # bom_id.action_set_to_draft()
                        # bom_id.action_get_material_td(self.mrp_picking_type.default_location_src_id.id)
                        # bom_id.action_get_material_lab(self.mrp_picking_type.default_location_src_id.id,{
                        #     "qty_kg_greige":qty_kg_greige,
                        # })
                        bom_id.action_confirm()
                        
                    
                jumlah_spk = self.jumlah_spk
                if jumlah_spk > 0:

                    for a in range(jumlah_spk):
                        type_id          = self.env['mrp.type'].browse(self.production_type_id.id)
                        mo_name          = type_id.production_sequence_id.next_by_id()
                        lot_producing_id = self.env['stock.production.lot'].sudo().create({
                                "name": mo_name,
                                "inspect_date":self.tanggal,
                                "tanggal_produksi":self.tanggal,
                                "location_id":self.mrp_picking_type.default_location_dest_id.id,
                                "product_id":self.mkt_production_id.product_id.id,
                                "company_id":self.env.user.company_id.id
                            })
                        dt_start = datetime.combine(self.tanggal, datetime.min.time())
                        dt_end = datetime.combine(self.tanggal, datetime.max.time())
                        import logging;
                        _logger = logging.getLogger(__name__)
                        _logger.warning('='*40)
                        _logger.warning('MESSAGE')
                        _logger.warning(dt_start)
                        _logger.warning(dt_end)
                        _logger.warning(fields.Datetime.subtract(dt_start,hours=1))
                        _logger.warning(fields.Datetime.subtract(dt_end,hours=1))
                        _logger.warning('='*40)
                        # start_working = timedelta(hours=6,minutes=30) 
                        # dt_start =  dt_start + start_working 
                        move_raw_ids = []
                        
                        
                        # SEMENTARA DI COMMENT
                        move_raw_ids.append((0,0,{
                                    "name":self.component_ids.yarn_id.name,
                                    "product_id":self.component_ids.yarn_id.id,
                                    # "product_uom_qty":self.quantity_shrinkage,
                                    "product_uom":self.component_ids.yarn_id.uom_id.id,
                                    "location_id":self.production_type_id.finished_location.id,
                                    "location_dest_id":15,
                                    }))
                        # SEMENTARA DI COMMENT
                        
                        
                        mrp_ids.append((0,0,{
                            "name":mo_name,
                            "product_id":self.mkt_production_id.product_id.id,
                            "lot_producing_id": lot_producing_id.id,
                            "type_id":self.production_type_id.id,
                            "product_uom_id":self.uom_id.id,
                            "date_planned_start": dt_start,
                            "date_planned_finished": dt_end,
                            # "date_planned_start": fields.Datetime.subtract(dt_start,hours=1),
                            # "date_planned_finished": fields.Datetime.subtract(dt_end,hours=1),
                            "bom_id":bom_id.id,
                            "mrp_request_id":self.id,
                            "quantity_request": self.quantity_shrinkage,
                            "greige_id":self.greige_id.id,
                            # "sisir_id":self.sisir_id.id,
                            # "total_end":self.total_end,
                            # "total_creel":self.total_creel,
                            # "jml_beam_stand":self.jml_beam_stand,
                            # "gramasi_kain_finish":self.gramasi,
                            "lebar_kain_finish":self.lebar,
                            "density_kain_finish":self.density,
                            "qty_yard_kp" :self.quantity_shrinkage,
                            "product_qty" :self.quantity,
                            # "qty_producing":self.quantity_shrinkage,
                            # "sale_line_id":line.order_line_id.id,
                            "origin": self.name,
                            "sale_type":self.sale_type,
                            # "machine_id":self.machine_id.id,
                            "picking_type_id":self.production_type_id.picking_type_id.id,
                            "location_src_id":self.production_type_id.component_location.id,
                            "location_dest_id":self.production_type_id.finished_location.id,
                            "move_raw_ids": move_raw_ids
                        }))
                
                self.mrp_ids = mrp_ids
                for mrp in self.mrp_ids:
                    mrp._onchange_bom_id()
                    mrp._onchange_move_raw()
                    mrp._onchange_move_finished()
                    mrp.update({'product_qty': self.quantity_shrinkage})
                    # mrp.action_confirm()
                    # for wo in mrp.workorder_ids.filtered(lambda x:x.workcenter_id.is_planning):
                    #     machine_plan.append((0,0,{
                    #         "production_id":wo.production_id.id,
                    #         "workorder_id":wo.id,
                    #     }))
                
                self.machine_temp_ids = machine_plan
                
                    # raise UserError('Quantity Request more than outstanding !!!')
            else:
                for production in self.mrp_ids:
                    # production.write({"move_raw_ids": [(0,0,{
                    #             "name":self.greige_id.name,
                    #             "product_id":self.greige_id.id,
                    #             "product_uom_qty":self.quantity_shrinkage,
                    #             # "mesin_id":self.machine_id.id,
                    #             "product_uom":self.greige_id.uom_id.id,
                    #             "location_id":self.production_type_id.component_location.id,
                    #             "location_dest_id":15,
                    #         })],})
                    production._onchange_bom_id()
                    production._onchange_move_raw()
                    production._onchange_move_finished()
                    # production._onchange_workorder_ids()
                    # production.get_parameter_process()
            # SEMENTARA DI COMMENT
            # self.request_material() 
            # SEMENTARA DI COMMENT
            # for line in self.order_temp_ids.filtered(lambda x: x.remaining_qty < self.quantity):
                
            #         title = _("Warning")
            #         message = _("Quantity Request More Than Outstanding!!")
            #         return {
            #             'type': 'ir.actions.client',
            #             'tag': 'display_notification',
            #             'params': {
            #                 'title': title,
            #                 'message': message,
            #                 'sticky': True,
            #             }
            #         }    
        else:
            # TWISTING
            if self.mrp_ids:
                for mrp in self.mrp_ids:
                    mrp._onchange_move_raw()
                self.request_material()
        self.write({"state": "confirm"})
    

    @api.model
    def create(self, vals):
        production_type_id = self.env['mrp.type'].browse(vals.get('production_type_id'))
        vals['name'] = production_type_id.request_sequence_id.next_by_id()
        return super(ManufacturingRequest, self).create(vals)

    def write(self, vals):
        return super(ManufacturingRequest, self).write(vals)

    @api.depends('sale_id')
    def _compute_greige_mkt_ids(self):
        # greige_mkt_ids = self.env['product.product'].search([('kd_product_tmpl_mkt_id','=',self.sale_id.product_id.id)])
        # self.greige_mkt_ids = greige_mkt_ids.ids
        self.greige_mkt_ids = self.sale_id.greige_id.product_variant_ids.mapped('kd_product_tmpl_mkt_id.id')

    @api.depends('quantity_greige', 'greige_id')
    def _compute_berat_greige(self):
        if self.greige_id and self.quantity_greige > 0:
            self.berat_greige = self.greige_id.gramasi_greige * self.quantity_greige
        else:
            self.berat_greige = 0

    @api.onchange('quantity')
    def _onchange_quantity(self):
        sol = self.order_temp_ids
        if sol and self.production_type_id.name == 'DYEING':
            if self.quantity > min(sol.mapped('remaining_qty')):
                raise ValidationError("Mohon maaf quantity batch melebihi quantity sisa order marketing")
            
    @api.onchange('mkt_production_id')
    def _onchange_greige(self):
        self.greige_id = self.mkt_production_id.product_id.id
        
    @api.model
    def default_get(self, fields):
        res = super(ManufacturingRequest, self).default_get(fields)
        ctx = self._context
        if ctx.get('production_type_id') == 5:
            sizing_id = self.env['mrp.type'].search([('id','=', 5)])
            sequence = sizing_id.sequence.next_by_id()
            res.update({
                'beam_product_id': sequence
            })
        return res


        
    

class ManufacturingRequestDetail(models.Model):
    _name = 'mrp.request.detail'

    name            = fields.Char(string='Name')
    mrp_request_id  = fields.Many2one('mrp.request', string='Mrp Request')
    product_id      = fields.Many2one('product.template', string='Product', related='mrp_request_id.product_id')
    quantity        = fields.Float(string='Quantity')
    uom_id          = fields.Many2one('uom.uom', string='Uom', related='mrp_request_id.uom_id')
    machine_id      = fields.Many2one('mrp.machine', string='Machine')
    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type', related='mrp_request_id.picking_type_id')
    
    

class MrpGreigestockAvailable(models.Model):
    _name = 'mrp.greige.stock'

    name              = fields.Char(string='Name')
    mrp_request_id    = fields.Many2one('mrp.request', string='Mrp Request')
    greige_id         = fields.Many2one('product.product', string='Greige Name',domain=[('categ_id.name', '=', 'GREY')])
    std_potong        = fields.Float(string='Std Potong',related="greige_id.std_potong")
    uom_id            = fields.Many2one('uom.uom', related='greige_id.uom_id', string='Uom')
    quantity          = fields.Float(string='Quantity',compute='_compute_quantities')
    reserved_quantity = fields.Float(compute='_compute_reserved', string='Reserved', store=False)
    
    @api.depends('greige_id')
    def _compute_quantities(self):
        Quant = self.env['stock.quant'].with_context(active_test=False)
        source_location = self.mrp_request_id.production_type_id.component_greige_location.id
        for stock in self:
            domain_quant = [('product_id', '=',stock.greige_id.id),('location_id','=',source_location)]
            quants_res = dict((item['product_id'][0], (item['quantity'], item['reserved_quantity'])) for item in Quant.read_group(domain_quant, ['product_id', 'quantity', 'reserved_quantity'], ['product_id'], orderby='id'))
            reserved_quantity = quants_res.get(stock.greige_id.id, [False, 0.0])[1]
            onhand_quantity = quants_res.get(stock.greige_id.id, [False, 0.0])[0]
            stock.quantity = onhand_quantity
            stock.reserved_quantity = reserved_quantity

    def action_use_greige(self):
        for rec in self:
            if rec.mrp_request_id.state != 'done':
                rec.mrp_request_id.write({'greige_id': rec.greige_id.id})
            else:
                raise UserError('Mohon maaf status dari MOR ini telah done')

class MrpYarnStockAvailable(models.Model):
    _name = 'mrp.yarn.stock'

    name              = fields.Char(string='Name')
    mrp_request_id    = fields.Many2one('mrp.request', string='Mrp Request')
    yarn_id           = fields.Many2one('product.product', string='Yarn',domain=[('categ_id.name', 'ilike', '%benang%')])
    uom_id            = fields.Many2one('uom.uom', related='yarn_id.uom_id', string='Uom')
    quantity          = fields.Float(string='Quantity',compute='_compute_quantities')
    reserved_quantity = fields.Float(compute='_compute_reserved', string='Reserved', store=False)
    
    @api.depends('yarn_id')
    def _compute_quantities(self):
        Quant = self.env['stock.quant'].with_context(active_test=False)
        source_location = self.mrp_request_id.production_type_id.component_greige_location.id
        for stock in self:
            domain_quant = [('product_id', '=',stock.yarn_id.id),('location_id','=',source_location)]
            quants_res = dict((item['product_id'][0], (item['quantity'], item['reserved_quantity'])) for item in Quant.read_group(domain_quant, ['product_id', 'quantity', 'reserved_quantity'], ['product_id'], orderby='id'))
            reserved_quantity = quants_res.get(stock.yarn_id.id, [False, 0.0])[1]
            onhand_quantity = quants_res.get(stock.yarn_id.id, [False, 0.0])[0]
            stock.quantity = onhand_quantity
            stock.reserved_quantity = reserved_quantity


class MrpRequestComponent(models.Model):
    _name = 'mrp.request.component'
    
    mrp_request_id      = fields.Many2one('mrp.request', string='Mrp Request')
    production_type_id  = fields.Many2one(related='mrp_request_id.production_type_id', string='Production Type')
    yarn_id             = fields.Many2one('product.product', string='Yarn',domain=[('categ_id.name', 'ilike', '%benang%')])
    pakan_id            = fields.Many2one('product.product', string='Pakan',domain=[('categ_id.name', 'ilike', '%benang%')])
    sisir_id            = fields.Many2one('master.sisir', string='Sisir')
    # uom_id            = fields.Many2one('uom.uom', related='yarn_id.uom_id', string='Uom')
    
    


class SaleOrderLineTemp(models.Model):
    _name = 'sale.order.line.temp'
    
    sale_id         = fields.Many2one('sale.order', string='Sale')
    product_id      = fields.Many2one('product.product', string='Product')
    product_uom_id  = fields.Many2one(related='product_id.uom_id', string='Uom')
    order_line_id   = fields.Many2one('sale.order.line', string='Order Line')
    process_type_id = fields.Many2one(related='order_line_id.process_type_id', string='Kategori Resep')
    mrp_request_id  = fields.Many2one(comodel_name='mrp.request', string='Mrp Request')
    quantity        = fields.Float(string='Quantity')
    remaining_qty   = fields.Float(string='Outstanding')
    state           = fields.Char(string='State')
    
    
class MachinePlanningTemp(models.Model):
    _name = 'machine.planning.temp'
    
    
    
    mrp_request_id  = fields.Many2one(comodel_name='mrp.request', string='Mrp Request')
    machine_id      = fields.Many2one('mrp.machine', string='Machine', required=True, )
    production_id   = fields.Many2one('mrp.production', string='Production')
    workorder_id    = fields.Many2one('mrp.workorder', string='Work Order')
    workcenter_id   = fields.Many2one('mrp.workcenter', string='Work Center',related="workorder_id.workcenter_id")
    program_id      = fields.Many2one('mrp.program', string='Program')
    date_planned_start = fields.Datetime(
        'Scheduled Date', copy=False,
        help="Date at which you plan to start the production.",
        index=True, required=True)
    date_planned_finished = fields.Datetime(
        'Scheduled End Date',
        help="Date at which you plan to finish the production.",
        copy=False)
    
    
    
        
    def write(self, vals):
        if vals.get('machine_id'):
            if self.workcenter_id.name == 'DYEING':
                self.production_id.write({
                    "mesin_id":vals.get('machine_id'),
                })
            date_start      = self.workorder_id.date_planned_start + timedelta(hours=7)
            no_urut = 1
            query = """
                SELECT nourut_plan FROM mrp_workorder mw 
                left join mrp_workcenter mwcr on mwcr.id = mw.workcenter_id
                WHERE mesin_id = %s
                and mwcr.is_planning = true
                and nourut_plan is not null
                and to_date(to_char(date_planned_start + interval '7 hours', 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD') = '%s'
            """ % (vals.get('machine_id'), date_start.strftime('%Y-%m-%d'))
            self._cr.execute(query)
            list_norut = self._cr.fetchall()
            if len(list_norut) > 0:
                no_urut = max([a[0] for a in list_norut]) + 1
            self.workorder_id.write({
                "mesin_id":vals.get('machine_id'),
                "nourut_plan" : no_urut
            })
            
            
        return super(MachinePlanningTemp, self).write(vals)

    
    def unlink(self):
        for line in self:
            if line.production_id.state in ['done']:
                raise UserError(_("You cannot delete an work order if the state is '%s'."%(line.production_id.state)))
            else:
                line.workorder_id.unlink()
        return super(MachinePlanningTemp, self).unlink()
    
    
    
