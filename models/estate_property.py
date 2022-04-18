from copy import copy
from xml.dom.minidom import ReadOnlySequentialNamedNodeMap
from odoo import fields, models, api
from dateutil.relativedelta import relativedelta

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"

    def _default_date_availability(self):
        return fields.Date.context_today(self) + relativedelta(months=3)

    name = fields.Char(String="name", default="Novo")
    description = fields.Text(String="description")
    last_seen = fields.Datetime("Last Seen", default=lambda self: fields.Datetime.now())
    postcode = fields.Char(String="postcode")
    date_availability = fields.Date(
        "Available From", default=lambda self: self._default_date_availability(), copy=False)
    expected_price = fields.Float(String="Expected Price")
    selling_price = fields.Float(String="Selling Price", copy=False, readonly=True)
    bedrooms = fields.Integer(String="Bedrooms", default=2)
    living_area = fields.Integer(String="Living Area")
    facades = fields.Integer(String="Facades")
    garage = fields.Boolean(String="Garage")
    garden = fields.Boolean(String="Garden")
    garden_area = fields.Integer(String="Garden Area")
    garden_orientation = fields.Selection(string='Garden Orientation',
       selection=[('north', 'North'), ('south', 'South'),  ('east', 'East'),  ('west', 'West')])
    active = fields.Boolean("Active", default=True)
    property_type_id = fields.Many2one("estate.property.type", string="Property Type")
    salesman_id = fields.Many2one('res.users', string='Salesman', default=lambda self: self.env.user)
    buyer_id = fields.Many2one('res.partner', string='Buyer', default=lambda self: self.env['res.partner'])
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many('estate.property.offer','property_id', string="Offers")
    best_price = fields.Float(string='Best Offer', compute='_compute_best_price')

    @api.depends('offer_ids')
    def _compute_best_price(self):
        for rec in self:
            rec.best_price = max(rec.offer_ids.mapped('price'))
    
    state = fields.Selection(
        selection=[
        ("novo", "Novo"),
        ("oferta recebida", "Oferta recebida"),
        ("oferta aceita", "Oferta aceita"),
        ("vendido", "Vendido"),
        ("cancelado", "Cancelado"),
        ],
        string="Status",
        required=True,
        copy=False,
)

    total_area = fields.Float(string='Total Area', compute='_compute_total')
    
    @api.depends('living_area','garden_area')
    def _compute_total(self):
        for rec in self:
            rec.total_area = rec.living_area * rec.garden_area


def action_vendido(self):
    if "cancelado" in self.mapped("state"):
         raise UserError("Propriedades canceladas não podem ser vendido.")
    
    return self.write({"state": "vendido"})


def action_cancel(self):
    if "vendido" in self.mapped("state"):
        raise UserError("Propriedades vendidas não podem ser canceladas.")

    return self.write({"state": "cancelado"})
    

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Estate Property Type"

    name = fields.Char(String="name", default="", required=True)

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Estate Property Tag"

    name = fields.Char(String="name", default="", required=True)

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"
 
    price = fields.Float(String="price")
    state = fields.Selection(
        selection=[
        ("aceito", "Aceito"),
        ("recusado", "Recusado"),
        ],
        string="Status",
        copy=False,
        default="Desconhecido",
   
)
    partner_id=fields.Many2one('res.partner', required=True, string="Id Salesman")
    property_id=fields.Many2one('estate.property', required=True, string="Property Id")
  
