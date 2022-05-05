# -*- coding: utf-8 -*-

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class EstateProperty(models.Model):
# ---------------------------------------- Atributos Privados ---------------------------------

    _name = "estate.property"
    _description = "Real Estate Property"
    _order = "id desc"
    _sql_constraints = [
        ("check_expected_price", "CHECK(expected_price > 0)", "O Preço esperado precisa ser estritamente positivo"),
        ("check_selling_price", "CHECK(selling_price >= 0)", "O preço de venda precisa ser positivo."),
    ]
# ---------------------------------------- Métodos Default ------------------------------------

    def _default_date_availability(self):
        return fields.Date.context_today(self) + relativedelta(months=3)

# --------------------------------------- Declaração de Campos ----------------------------------
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
            if rec.offer_ids:
                rec.best_price = max(rec.offer_ids.mapped('price'))
            else:
                rec.best_price = 0
    
    # Básicos
    name = fields.Char("Nome", required=True)
    description = fields.Text("Descrição")
    postcode = fields.Char("Código Postal")
    date_availability = fields.Date("Disponíbilidade", default=lambda self: self._default_date_availability(), copy=False)
    expected_price = fields.Float("Preço Esperado", required=True)
    selling_price = fields.Float("Preço de Venda", copy=False, readonly=True)
    bedrooms = fields.Integer("Quartos", default=2)
    living_area = fields.Integer("Área de serviço(sqm)")
    facades = fields.Integer("Fachadas")
    garage = fields.Boolean("Garagem")
    garden = fields.Boolean("Jardim")
    garden_area = fields.Integer("Área do Jardim (sqm)")
    garden_orientation = fields.Selection(string='Orientação do Jardim',
       selection=[('north', 'North'), ('south', 'South'),  ('east', 'East'),  ('west', 'West')])
    
    # Especiais
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
        default='novo'
)
    active = fields.Boolean("Ativo", default=True)

    # Relacionais
    property_type_id = fields.Many2one("estate.property.type", string="Tipo de propriedade")
    user_id = fields.Many2one("res.users", string="Vendedor", default=lambda self: self.env.user)
    buyer_id = fields.Many2one("res.partner", string="Comprador", readonly=True, copy=False)
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Ofertas")

    # Computados
    total_area = fields.Integer(
        "Área total (sqm)",
        compute="_compute_total",
        help="Área total computada somando a área de serviço e a área do jardim.",
    )
    best_price = fields.Float("Melhor oferta", compute="_compute_best_price", help="Melhor oferta recebida")

# ---------------------------------------- Métodos Computados ------------------------------------

    @api.depends('offer_ids')
    def _compute_best_price(self):
        for rec in self:
            if rec.offer_ids:
                rec.best_price = max(rec.offer_ids.mapped('price'))
            else:
                rec.best_price = 0

    @api.depends('living_area','garden_area')
    def _compute_total(self):
        for rec in self:
            rec.total_area = rec.living_area * rec.garden_area

# ----------------------------------- Constrains e Onchanges --------------------------------

    @api.onchange('garden','garden_area','garden_orientation')
    def _onchange_(self):
        for r in self:
                if r.garden == True:
                    r.garden_area = 10
                    r.garden_orientation = 'north'
                else:
                    self.garden_area = 0
                    self.garden_orientation = False

    @api.constrains("expected_price", "selling_price")
    def _check_price_difference(self):
        for prop in self:
            if (
                not float_is_zero(prop.selling_price, precision_rounding=0.01)
                and float_compare(prop.selling_price, prop.expected_price * 90.0 / 100.0, precision_rounding=0.01) < 0
            ):
                raise ValidationError(
                    "O preço de venda precisa ser pelo menos 90% do preço esperado. "
                    + "Você precisa reduzir o preço esperado se quiser aceitar esta oferta."
                )

# ------------------------------------------ Métodos CRUD -------------------------------------
    def unlink(self):
        if not set(self.mapped("state")) <= {"novo", "cancelado"}:
            raise UserError("Apenas propriedades novas e canceladas podem ser deletadas.")
        return super().unlink()

 # ---------------------------------------- Métodos de Ação -------------------------------------
    
    def action_sold(self):
        if "cancelado" in self.mapped("state"):
            raise UserError("Propriedades canceladas não podem ser vendidas.")
        
        return self.write({"state": "vendido"})

    def action_cancel(self):
        if "vendido" in self.mapped("state"):
            raise UserError("Propriedades vendidas não podem ser canceladas.")

        return self.write({"state": "cancelado"})

# ---------------------------------------- CLASSE ESTATE PROPERTY TYPE -------------------------------------
class EstatePropertyType(models.Model):
# ---------------------------------------- Atributos Privados ---------------------------------

    _name = "estate.property.type"
    _description = "Real Estate Property Type"
    _order = "sequence, name"
    _sql_constraints = [
        ("check_name", "UNIQUE(name)", "O nome precisa ser único."),
    ]
# --------------------------------------- Declaração de Campos ----------------------------------
    
    # Básicos
    name = fields.Char(String="Nome", default="", required=True)
    sequence = fields.Integer("Sequência", default=10)

    # Relacional (para visualização em linha)
    property_ids = fields.One2many("estate.property", "property_type_id", string="Propriedades")

    #Computados
    offer_count = fields.Integer(string="Contador de Ofertas", compute="_compute_offer")
    offer_ids = fields.Many2many("estate.property.offer", string="Ofertas", compute="_compute_offer")

# ---------------------------------------- Métodos Computados ------------------------------------
    def _compute_offer(self):
        data = self.env["estate.property.offer"].read_group(
            [("property_id.state", "!=", "canceled"), ("property_type_id", "!=", False)],
            ["ids:array_agg(id)", "property_type_id"],
            ["property_type_id"],
        )
        mapped_count = {d["property_type_id"][0]: d["property_type_id_count"] for d in data}
        mapped_ids = {d["property_type_id"][0]: d["ids"] for d in data}
        for prop_type in self:
            prop_type.offer_count = mapped_count.get(prop_type.id, 0)
            prop_type.offer_ids = mapped_ids.get(prop_type.id, [])

# ---------------------------------------- Métodos de Ação -------------------------------------

    def action_view_offers(self):
        res = self.env.ref("estate.estate_property_offer_action").read()[0]
        res["domain"] = [("id", "in", self.offer_ids.ids)]
        return res

# ---------------------------------------- CLASSE ESTATE PROPERTY TAG -------------------------------------
class EstatePropertyTag(models.Model):
# ---------------------------------------- Atributos Privados ---------------------------------
   
    _name = "estate.property.tag"
    _description = "Estate Property Tag"
    _order = "name"
    _sql_constraints = [
        ("check_name", "UNIQUE(name)", "O nome precisa ser único."),
    ]

# --------------------------------------- Declaração de Campos ----------------------------------
    
    name = fields.Char(String="Nome", default="", required=True)
    color = fields.Integer("Color Index")

# ---------------------------------------- CLASSE ESTATE PROPERTY OFFER -------------------------------------
class EstatePropertyOffer(models.Model):
# ---------------------------------------- Atributos Privados ---------------------------------
    
    _name = "estate.property.offer"
    _description = "Estate Property Offer"
    _order = "price desc"
    _sql_constraints = [
        ("check_price", "CHECK(price > 0)", "O preço precisa ser estritamente positivo."),
    ]

# --------------------------------------- Declaração de Campos ----------------------------------
    # Básicos
    price = fields.Float(String="Preço")
    validity=fields.Integer(default=7, string="Validade (dias)")

    #Especiais
    state = fields.Selection(
        selection=[
        ("aceito", "Aceito"),
        ("recusado", "Recusado"),
        ],
        string="Status",
        copy=False,
        default=False
   
)
    #Relacionais
    partner_id=fields.Many2one('res.partner', required=True, string="Comprador")
    property_id=fields.Many2one('estate.property', required=True, string="Propriedade")
    property_type_id = fields.Many2one(
        "estate.property.type", related="property_id.property_type_id", string="Tipo de propriedade", store=True
    )
    
    #Computado
    date_deadline=fields.Date(string="Data de Vencimento", store=True, compute="_compute_deadline", inverse="_inverse_deadline", default=lambda self: fields.Datetime.today().date())
 
 # ---------------------------------------- Métodos Computados ------------------------------------
   

    partner_id=fields.Many2one('res.partner', required=True, string="Id Salesman")
    property_id=fields.Many2one('estate.property', required=True, string="Property Id")
    validity=fields.Integer(default=7, string="Validity")
    date_deadline=fields.Date(string="Date Deadline", store=True, compute="_compute_deadline", inverse="_inverse_deadline", default=lambda self: fields.Datetime.today().date())

    @api.depends('validity', 'create_date')
    def _compute_deadline(self):
        for rec in self:
            if rec.create_date:
                rec.date_deadline=rec.create_date + relativedelta(days=rec.validity)
            else:
                rec.date_deadline=date.today() + relativedelta(days=rec.validity)

    def _inverse_deadline(self):
        for rec in self:
            if not (rec.create_date and rec.date_deadline): continue
            else:
                rec.validity = int ((rec.date_deadline - (rec.create_date).date()).days)

# ------------------------------------------ Métodos CRUD -------------------------------------
    @api.model
    def create(self, vals):
        if vals.get("property_id") and vals.get("price"):
            prop = self.env["estate.property"].browse(vals["property_id"])
            
            # Nós checamos se a oferta é maior que outras ofertas existentes
            if prop.offer_ids:
                max_offer = max(prop.mapped("offer_ids.price"))
                
                if float_compare(vals["price"], max_offer, precision_rounding=0.01) <= 0:
                    raise UserError("A oferta precisa ser maior que %.2f" % max_offer)
            prop.state = "oferta recebida"
        
        return super().create(vals)

# ------------------------------------------ Métodos de Ação -------------------------------------
    def action_aceitar(self):
        if "aceito" in self.mapped("property_id.offer_ids.state"):
            raise UserError("Uma oferta já foi aceita.")
        self.write({"state": "aceito",})

        return self.mapped("property_id").write(
            {
                "state": "oferta aceita",
                "selling_price": self.price,
                "buyer_id": self.partner_id.id,
            }
        )

    def action_recusar(self):
        return self.write({"state": "recusado"})


        