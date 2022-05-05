from odoo import models

class EstateProperty(models.Model):
 # ---------------------------------------- Atributos Privados ---------------------------------

    _inherit = "estate.property"

    # ---------------------------------------- Métodos de Ação -------------------------------------

    def action_sold(self):
        res = super().action_sold()
        journal = self.env["account.move"].with_context(default_move_type="out_invoice")._get_default_journal()
        for prop in self:
            self.env["account.move"].create(
                {
                    "partner_id": prop.buyer_id.id,
                    "move_type": "out_invoice",
                    "journal_id": journal.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": prop.name,
                                "quantity": 1.0,
                                "price_unit": prop.selling_price * 6.0 / 100.0,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": "Taxas administrativas",
                                "quantity": 1.0,
                                "price_unit": 100.0,
                            },
                        ),
                    ],
                }
            )
        return res
