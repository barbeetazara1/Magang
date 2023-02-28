from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    
    
    def compute_gsm_greige(self):
        for line in self:
            if line.product_id.categ_id.id in (127,124,44):
                line.gramasi_greige = line.product_id.gramasi_greige
                line.lebar_greige = line.product_id.lebar_greige
                line.std_potong = line.product_id.std_potong
            if line.product_id.categ_id.id in (142,45):
                line.gramasi_greige = line.production_id.greige_id.gramasi_greige
                line.lebar_greige = line.production_id.greige_id.lebar_greige
                line.std_potong = line.production_id.greige_id.std_potong
            else:
                line.gramasi_greige = 0
                line.lebar_greige = 0
                line.std_potong = 0
    
    
    production_id        = fields.Many2one('mrp.production', string='Production')
    production_type_id   = fields.Many2one('mrp.type', related='production_id.type_id' ,string='Production Type')
    gramasi_finish       = fields.Float(string='Gramasi',related="production_id.gramasi_kain_finish")
    lebar_finish         = fields.Float(string='Lebar',related="production_id.lebar_kain_finish")
    qty                  = fields.Float(string='Qty', related='product_qty', store=True,)
    color_id             = fields.Many2one(related='product_id.color_id', string='Color')
    design_id            = fields.Many2one(related='product_id.design_id', string='Design')
    gramasi_greige       = fields.Float(string='Gramasi Greige',compute="compute_gsm_greige")
    lebar_greige         = fields.Float(string='Lebar Greige',compute="compute_gsm_greige")
    std_potong           = fields.Float(string='Std Potong',compute="compute_gsm_greige")
    kd_product_tmpl_mkt_id = fields.Many2one('product.template', string='Product MKT', related='product_id.kd_product_tmpl_mkt_id')
    
    sale_id              = fields.Many2one(related='production_id.sale_id', string='Sake Order')
    beam_id              = fields.Many2one('mrp.production.beam', string='Beam')
    beam_type_id         = fields.Many2one('type.beam', string='Beam Type')
    location_id          = fields.Many2one('stock.location', string='Location')
    product_category     = fields.Many2one('product.category', string='Product Category', related='product_id.categ_id', store=True,)
    picking_ids          = fields.Many2many(
        comodel_name='stock.picking', 
        relation='stock_production_picking_history_rel',
        string='Transfer History'
        )
    
    
    shift                = fields.Char(string='Shift')
    keterangan           = fields.Char(string='Keterangan')
    quantity_kanji       = fields.Float(string='Quantity Kanji')
    quantity_murni       = fields.Float(string='Quantity Murni')
    quantity_brutto      = fields.Float(string='Quantity Brutto')
    quantity_tarra       = fields.Float(string='Quantity Tarra')
    panjang_awal         = fields.Float(string='Panjang Awal')
    panjang_sisa         = fields.Float(string='Panjang Sisa')
    sisa_actual_beam     = fields.Float(string='Sisa Actual Beam')
    tanggal_beam         = fields.Date(string='Tanggal Beam')
    state                = fields.Selection([("available","Available"),("sold","Sold"),("released","Released"),("return","Returned")], string='Status')
   
    #todo fixme
    harga                = fields.Float(string='Harga')
    no_warna             = fields.Char(string='Warna')
    pic                  = fields.Float(string='Pic')
    lebar                = fields.Float(string='Lebar')
    grade_id             = fields.Many2one('makloon.grade', string='Grade')
    tanggal_produksi     = fields.Date(string='Tanggal Masuk')
    rack_id              = fields.Many2one('master.rack', string='Rack')
    no_om                = fields.Char(string='No Om')
    kelompok             = fields.Char(string='Kelompok')
    cone                 = fields.Char(string='Cone')
    no_mesin             = fields.Char(string='No Mesin')
    
    
    move_line_ids        = fields.One2many('stock.move.line.before', 'lot_id', string='History')
    # move_line_ids         = fields.Many2many('stock.move.line.before', 'moveline_rel','lot_prepare_id',string='History' )

    product_age          = fields.Integer('Age', compute='ProductAgeLot', store=True, readonly=True)
    category_age         = fields.Char('Category Age', compute='_get_category_age', store=True, readonly=True)
    is_scanned           = fields.Boolean(string='Is Scanned ?', default=False)
    created_picking_grade_non_a = fields.Boolean(string='Created Picking Grade Non A ?')
    partner_id           = fields.Many2one('res.partner', string='Customer')
    beaming_ids          = fields.One2many(related='production_id.beaming_ids', string='Beaming',)
    greige_name          = fields.Many2one('product.product',string='Nama Greige/Corak',default=84746, domain=[('categ_id.name', 'in', ('greige', 'GREY'))])
    status_cucuk         = fields.Boolean(string="Status Cucuk", default=False)
    history_weaving      = fields.One2many('history.weaving','lot_id',string="History Weaving")
    
    #WEAVING related mrp.prod
    sisir_id             = fields.Many2one(related='production_id.sisir_id', string='Sisir')
    total_end            = fields.Float(string='Total End', related='production_id.total_end')

    is_cucukan           = fields.Boolean(string='Cucukan ?', default=False)
    tgl_cucukan          = fields.Date(string='Tanggal Cucukan')
    operator_cucukan_id  = fields.Many2one('hr.employee', string='Operator Cucukan')
    hasil_weaving        = fields.Float(string='Hasil Weaving')
    sisa_weaving         = fields.Float(string='Sisa Weaving')
    tanggal_habis        = fields.Date(string='Tanggal Habis Beam')
    index_benang         = fields.Float('Index',help="Index Benang per 30 cm")
    spu                  = fields.Float('Tot Draff')


    def ProductAgeLot(self):
        self.env.cr.execute("""update stock_production_lot set product_age = current_date - tanggal_produksi""")
        
    @api.depends('product_age')
    def _get_category_age(self):
        for rec in self:
            if rec.product_age >= 0 and rec.product_age <= 90:
                rec.category_age = 'HIJAU'
            elif rec.product_age >= 90 and rec.product_age <= 180:
                rec.category_age = 'ORANGE'
            elif rec.product_age >= 180 and rec.product_age <= 365:
                rec.category_age = 'MERAH'
            elif rec.product_age > 365:
                rec.category_age = 'HITAM'
    
    
    
    
    def open_split_barcode_wizard_form(self):
        warehouse_id = self.env['stock.warehouse'].sudo().search([('lot_stock_id','=',self.location_id.id)],limit=1).id  if self.location_id else False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Split Barcode',
            'res_model': 'split.barcode.wizard',
            'view_mode': 'form',
            'context': {'default_lot_id':self.id,"split_at_spl":1,"default_quantity":self.product_qty,"default_location_id":self.location_id.id,"default_warehouse_id":warehouse_id,"model":self._name},
            'target': 'new',
        }
    
    
    def _create_moveline(self,lots =[]):
        moveline_ids = []
        move_ids = []
        #note
        # warehouse_id = self.env.user.default_warehouse_ids
        # if warehouse_id:
        for lot in lots:
            moveline_template = {
                    'product_id': lot.product_id.id,
                    'lot_id': lot.id,
                    'lot_name': lot.name,
                    'product_uom_id': lot.product_id.uom_id.id,
                    'qty_done': lot.product_qty,
                    'company_id':self.env.company.id,
                    # 'location_id': warehouse_id[0].out_type_id.default_location_src_id.id,
                    # 'location_dest_id': warehouse_id[0].out_type_id.default_location_dest_id.id,
                    'location_id': lot.production_id.type_id.inspect_location_dest_id.id,
                    'location_dest_id': lot.production_id.type_id.delivery_location_id.id,
            }
            
            moveline_ids.append((0,0,moveline_template))
            
            move_template = {
                    'name': lot.product_id.name,
                    'date':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'product_id': lot.product_id.id,
                    'product_uom': lot.product_id.uom_id.id,
                    'product_uom_qty': lot.product_qty,
                    'company_id': self.env.company.id,
                    # 'location_id': warehouse_id[0].out_type_id.default_location_src_id.id,
                    # 'location_dest_id': warehouse_id[0].out_type_id.default_location_dest_id.id,
                    'location_id': lot.production_id.type_id.inspect_location_dest_id.id,
                    'location_dest_id': lot.production_id.type_id.delivery_location_id.id,
                }
            move_ids.append((0,0,move_template))
            lot.write({'created_picking_grade_non_a': True})
            
        
        
        
        picking_template = {
            'picking_type_id': 620, # GD. PACKING KAIN: Internal Transfers
            'date': fields.Date.today(),
            'scheduled_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'location_id': lot.production_id.type_id.inspect_location_dest_id.id,
            'location_dest_id': lot.production_id.type_id.delivery_location_id.id,
            'immediate_transfer': False,
            'move_line_nosuggest_ids': moveline_ids,
            'move_lines':move_ids,
            
        }
        
        picking = self.env['stock.picking'].create(picking_template)
        return picking
        # else:
        #     raise UserError("You Don't Have Default Warehouse")
            
    
    
    def _create_picking(self):
        active_ids = self.browse(self._context.get('active_ids'))
        picking = self._create_moveline(active_ids)
        # picking.action_confirm()
        # picking.action_assign()
        
        return {
            'name': 'Delivery Orders',
            'view_mode': "form",
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': picking.id,
        }

    @api.model
    def create(self, vals):
        ctx = self.env.context
        vals['company_id'] = ctx.get('allowed_company_ids', [1])[0]
        res = super(StockProductionLot, self).create(vals)

        return res

    def _create_picking_send_gd_bs(self, lots =[]):
        print('_create_picking_send_gd_bs')
        picking_type_obj = self.env['stock.picking.type'].browse(620) #GD. BS: Delivery Orders
        picking_type_id = picking_type_obj.id 
        location_id = picking_type_obj.default_location_src_id.id
        location_dest_id = 349
        data = []
        ctx = self.env.context
        for lot in self.env['stock.production.lot'].browse(ctx.get('active_ids', [])):
            print('lottsss', lot.id)
            data.append((0, 0, {
                'product_id': lot.product_id.id,
                'lot_id': lot.id,
                'grade_id': lot.grade_id.id,
                'product_uom_id': lot.product_id.uom_id.id,
                'qty_done': lot.product_qty,
                'company_id':self.env.company.id,
                'location_id': location_id,
                "location_dest_id": location_dest_id,
            }))
            lot.write({'created_picking_grade_non_a': True})

        picking_obj = self.env['stock.picking'].sudo().create({
                "picking_type_id": picking_type_id,
                "location_id": location_id,
                "location_dest_id": location_dest_id,
                "origin": '-',
                "scheduled_date": fields.Date.today(),
                "move_line_ids_without_package": data
            })
        
        return {
            'name': 'Internal Transfer packing',
            'view_mode': "form",
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': picking_obj.id,
        }


class Stock(models.Model):
    _inherit = 'mrp.production'
    
    
    lot_id          = fields.Many2one('stock.production.lot', string='Kartu Beam')
    beam_id         = fields.Many2one('mrp.production.beam', related='lot_id.beam_id')
    beaming_id      = fields.Many2one('mrp.beaming',string='No Beam')
    # beam_id         = fields.Many2one('mrp.beaming',string='No Beam')
    # beaming_id      = fields.Many2one('mrp.production.beam', related='lot_id.beam_id')
    beam_type_id    = fields.Many2one('mrp.production.beam.type', string='Beam Type', related='beam_id.type_id')
    prod_sizing_id  = fields.Many2one(related='lot_id.production_id', store=True)

    
    
    
    


    
