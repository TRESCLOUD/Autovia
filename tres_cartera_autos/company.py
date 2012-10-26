from osv import fields, osv

class res_company(osv.osv):
    
    _inherit = 'res.company'

    _columns = {
        'cedula': fields.char('Cedula', size=14),
        'ceo':fields.char('Empresario',size=50),
        }

res_company()