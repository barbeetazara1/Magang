from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class MrpBeaming(models.Model):
    _name = 'mrp.beaming'

    kode_prod               = fields.Char(string='Kode Prod')
    te_helai                = fields.Float(string='TE (Helai)', related='production_id.total_end')
    qty_beam                = fields.Float(string='Pjg/Beam')
    jml_beam                = fields.Float(string='Jumlah beam')
    type_beam_id            = fields.Many2one('type.beam', string='Type beam')
    lebar_beam              = fields.Float(string='Lebar Beam')
    total_panjang           = fields.Float(string='Total Panjang', compute='_compute_total')
    unit_wv                 = fields.Char(string='Unit WV')
    date                    = fields.Date(string='Date')
    production_id           = fields.Many2one('mrp.production', string='MO')
    state                   = fields.Boolean(string='State')
    beaming_details_ids     = fields.One2many('mrp.beaming.details', 'beaming_id', string="Beaming Details")
    index_benang            = fields.Float('Index',help="Index Benang per 30 cm")
    spu                     = fields.Float('Tot Draff')


    def name_get(self):
        res = []
        for beaming in self:
            res.append((beaming.id,beaming.kode_prod))
        return res
    
    @api.depends('qty_beam', 'jml_beam')
    def _compute_total(self):
        for rec in self:
            if rec.qty_beam > 0 and rec.jml_beam > 0:
                rec.total_panjang = rec.qty_beam * rec.jml_beam
            else : 
                rec.total_panjang = 0
                
                
    def open_beaming_details(self):
        _logger.warning('='*40)
        _logger.warning('='*40)
        _logger.warning("Open Beaming Details")
        _logger.warning('='*40)
        _logger.warning('='*40)
        view_id = self.env.ref('inherit_mrp.open_beaming_details_view').id
        return {
            'type'      : 'ir.actions.act_window',
            'name'      : 'Open Beaming Details',
            'res_model' : 'mrp.beaming',
            'view_mode' : 'form',
            'res_id'    : self.id,
            'target'    : 'new',
            'views'     : [[view_id, 'form']]
        }
        
    def generate_beam(self):
        _logger.warning('='*40)
        _logger.warning('='*40)
        _logger.warning('GENERATE BEAM')
        _logger.warning('='*40)
        _logger.warning('='*40)
        beaming_detail_ids = []
        for a in range(int(self.jml_beam)):
            lot_id = self.env['stock.production.lot'].create({
                'production_id': self.production_id.id,
                'production_type_id': 5,
                'product_id' : self.production_id.product_id.id,
                'product_uom_id' : self.production_id.product_id.uom_id.id,
                'location_id' : self.production_id.location_id.id,
                'beam_type_id': self.type_beam_id.id,
                'index_benang': self.index_benang,
                'spu': self.spu
            })
            beaming_detail_ids += [(0,0,{
                'lot_id':lot_id.id,
                'product_id':lot_id.product_id.id,
                'index_benang': lot_id.index_benang,
                'spu': lot_id.spu,
                'quantity': self.qty_beam,
                'uom_id':lot_id.product_id.uom_id.id,
            })]
        self.write({
            'beaming_details_ids': beaming_detail_ids,
            })
        
                
class MrpBeamingDetails(models.Model):
    _name = 'mrp.beaming.details'
    
    beaming_id      = fields.Many2one('mrp.beaming', string='Beaming')
    production_id   = fields.Many2one('mrp.production', string='MO')
    lot_id          = fields.Many2one('stock.production.lot', string='Lot')
    product_id      = fields.Many2one(related='lot_id.product_id', string='Product')
    uom_id          = fields.Many2one(related="product_id.uom_id", string='UOM')
    quantity        = fields.Float(string='Quantity')
    index_benang    = fields.Float('Index',help="Index Benang per 30 cm")
    spu             = fields.Float('Tot Draff')
    date            = fields.Date(string='Date')
    shift           = fields.Selection([("A","A"),("B","B"),("C","C"),("D","D")], string='Shift', store=True)
    unit            = fields.Many2one('mrp.machine', string="Unit")
    bruto           = fields.Float(string='Bruto (KG)')
    tarra           = fields.Float(string='Tarra (KG)')
    netto           = fields.Float(string='Netto (KG)')
    panjang         = fields.Float(string='Panjang (Yard)')
    jml_loss_awal   = fields.Float(string='Jml Loss Awal')
    meter_loss_awal = fields.Float(string='Meter Loss Awal')
    jml_loss_akhir  = fields.Float(string='Jml Loss Akhir')
    meter_loss_akhir = fields.Float(string='Meter Loss Akhir')
    
    
    
    def name_get(self):
        result = []
        for a in self:
            result.append((a.id, a.lot_id.name))
        return result
    
    # @api.model
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     res_search = False
    #     res = self.search([ '|',('lot_id.name',operator,name)] + args, limit=limit)
    #     res_search = res.name_get()
    #     return res_search


class PersiapanBeaming(models.Model):
    _name = 'persiapan.beaming'

    production_id   = fields.Many2one('mrp.production',string='Production')
    tgl_sizing      = fields.Date('Rencana Sizing',default=fields.Date.today())
    tgl_beaming     = fields.Date('Rencanan Beaming',default=fields.Date.today())
    beaming_id      = fields.Many2one('mrp.beaming',string='Kode Prod')
    request_id      = fields.Many2one('mrp.request', string='Request')
    jml_creel       = fields.Float('Jml Creel')
    tot_lusi        = fields.Float('Total Lusi')
    no_param_proses = fields.Float('Param Obat')
    param_id        = fields.Many2one('master.parameter.obat', string="Parameter Obat")
    jenis_obat      = fields.Float(related="param_id.jenis_obat",string="Jenis Obat (%)")
    speed           = fields.Float('Speed')
    tekanan_im      = fields.Float('Tekanan IM')
    tekanan_sq      = fields.Float('Tekanan SQ')
    tot_draff       = fields.Char('Tot Draff')
    spu             = fields.Char(string='Standar SPU')
    aktual          = fields.Char(string='Aktual')
    creel           = fields.Char(string='Creel')
    chamber         = fields.Char(string='Chamber')
    winding         = fields.Char(string='Winding')
    hardnes         = fields.Char(string='Hardnes')
    param_proses    = fields.Char(string='Param Proses')
    tension_stand   = fields.Char(string='Tension Beam Stand')
    tension_winding = fields.Char(string='Tension Beam Winding')
    tension_harned  = fields.Char(string='Tension Beam Harned')
    shift           = fields.Selection([("A","A"),("B","B"),("C","C"),("D","D")], string='Shift', store=True,)
    index_benang    = fields.Float('Index',help="Index Benang per 30 cm")
    act_denier      = fields.Float('Aktual Denier',help="Aktual Denier")
    jenis_obat      = fields.Char('Jenis Obat')
    type_beam_id    = fields.Many2one('type.beam', string='Type')
    lebar           = fields.Float(string='Lebar')
    panjang         = fields.Float(related="beaming_id.qty_beam", string='Panjang (Yard)')
    jmlh_beam       = fields.Float(related="beaming_id.jml_beam", string='Jumlah beam')
    # panjang_mtr     = fields.Float(string='Panjang (Meter)', compute="_compute_panjang_mtr")
    panjang_mtr     = fields.Float(string='Panjang (Meter)')
    catatan         = fields.Text(string='Catatan')

    # @api.depends('panjang_mtr')
    # def _compute_panjang_mtr(self):
    #     for pjg in self:
    #         pjg.panjang = 0
    
    @api.onchange('param_id')
    def onchange_param_id(self):
        _logger.warning('='*40)
        _logger.warning('='*40)
        _logger.warning('ONCHANGE PARAM')
        _logger.warning('='*40)
        _logger.warning('='*40)
        self.jenis_obat = self.param_id.jenis_obat
    

    @api.onchange('beaming_id')
    def onchange_kd_prod(self):
        _logger.warning('='*40)
        _logger.warning('='*40)
        _logger.warning('ONCHANGE KODE PROD BERHASIL')
        _logger.warning('='*40)
        _logger.warning('='*40)
        #ONCHANGE KODE PROD 
        self.tot_lusi       = self.beaming_id.te_helai
        self.jml_creel      = self.request_id.total_creel
        self.tgl_beaming    = self.beaming_id.date
        self.lebar          = self.beaming_id.lebar_beam
        
    @api.onchange('production_id')
    def get_price(self):
        self.tgl_sizing     = self.production_id.date_planned_start
    
        
        



class BeamType(models.Model):
    _inherit = 'type.beam'
    
    berat = fields.Float(string='Berat')
    lebar = fields.Float(string='Lebar')

