from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta ,datetime
import logging
import json
from odoo.tools import float_compare, float_round, float_is_zero
_logger = logging.getLogger(__name__)

class PostInventoryWeaving(models.TransientModel):
    _name = 'post.inventory.weaving'

    name = fields.Char(string='Post Inventory Weaving')
