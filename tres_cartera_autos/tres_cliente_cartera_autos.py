# -*- coding: utf-8 -*-
#import time
#from datetime import datetime
#from dateutil.relativedelta import relativedelta
import logging

#import netsvc
from osv import fields, osv
#from tools.translate import _
#from decimal import Decimal
#import decimal_precision as dp


_logger = logging.getLogger(__name__)


class res_partner(osv.osv):
    
    _name='res.partner'
    _inherit = 'res.partner'
    _order='name'
    
    _columns = {
        'cedula': fields.char('Cedula', size=14),
        'name': fields.char('Description', size=64),
        'profesion': fields.char('Profesion', size=20),
#        'descripcion':fields.char('Institucion',size=128),
        'estcivil': fields.selection( [ ('soltero','Soltero'),('casado','Casado'), ('viudo','Viudo'), ('divorciado','Divorciado'), ('Union','Libre') ],'Estado Civil'),
       
        #REFERENCIAS
        'bancos_ids': fields.one2many('referencia.bancos', 'ref_banco', 'Referencias de Bancos'),
        'inst_ids': fields.one2many('referencia.bancarias', 'ref_inst', 'Referencias Institucionales'),  
        'pers_ids': fields.one2many('referencia.personal', 'ref_pers', 'Referencias Personales'),
#        'egreso_id': fields.one2many('tres.cartera.egreso', 'partner_ide', 'Egresos'),

        #ACTIVIDAD ACTUAL
        'tipo': fields.selection( [ ('independiente','Independiente'),('empleado','Empleado')],'Tipo'), 
        'empresa':fields.char('Empresa',size=120),
        'telf_e': fields.char('Telefono',size=64),   
        'street_e': fields.char('Calle', size=128),
        'cargo': fields.char('Cargo', size=128),
        'anti': fields.integer('Antiguedad'),
        's_mes': fields.integer('Sueldo Mensual'),
        'otrs_ingr': fields.integer('Otros Ingresos'),
        'origen': fields.char('Origen', size=128),
        #    CR: campos add
        'history_ids': fields.one2many('tres.cartera.history', 'partner_id', 'Contratos Historial'),
        'egreso_id': fields.one2many('tres.cartera.egreso', 'res_partner_id', 'Egresos'),
        'contratos_ids': fields.one2many('tres.cartera', 'partner_id', 'Contratos'),
#        'tres_cartera':fields.one2many('tres.cartera.history', 'partener_id', 'Contratos'),
#        'function' : fields.function(_get_cur_function_id, type='many2one', obj="tres.cartera", method=True, string='Funcion Contracto'),
        
        'cliente_check':fields.boolean('Cliente', help='Permite clasificar a los Clientes'),
        'garante_check':fields.boolean('Garante', help='Permite clasificar a los Garantes'),
        'conyuge_check':fields.boolean('Conyuge', help='Permite clasificar a los Conyuges del cliente y del Garante'),
        
        # P.R. Referencias Familiares
        'nombre_familiar': fields.char('Nombre', size=128),
        'parentezco_familiar':fields.char('Parentezco',size=64),
        'telefono_familiar': fields.char('Telefono',size=64),   
        'direccion_familiar': fields.char('Direccion', size=128),
        'property_account_payable': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account Payable",
            view_load=True,
            domain="[('type', '=', 'payable')]",
            help="This account will be used instead of the default one as the payable account for the current partner",
            required=True),
        'property_account_receivable': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            view_load=True,
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as the receivable account for the current partner",
            required=True),
        }
    _default={
        'cliente_check': lambda *a: 1,
        'active': lambda *a: 1,
              }

res_partner()

#class res_partner_address(osv.osv):
#    _name='res.partner.address'
#    _inherit='res.partner.address'
#    
#    _columns={
#        #DOMICILIO
#        'residencia_aux':fields.selection([('arrendada','Arrendada'),('propia','Propia'),('familiar','Familiar'),('Otros','Otros')],'Residencia'), 
#        'otros':fields.char('Especifique',size=120),      
#         #DATOS CONYUGE
#        'nmbr_cnyg': fields.char('Nombre Conyuge',size=128),
#        'prof_cnyg':fields.char('Profesion',size=128),
#        'cargas': fields.integer('Numero de Cargas'),
#        'cd_cnyg':fields.char('Cedula',size=14),
#        'separ':fields.boolean('Separacion de Bienes'),
#        #REFERENCIA
#        'nmbr_comer':fields.char('Nombre',size=64),
#        'telf_comer':fields.integer('Telefono'),
#        
#        'flia_nmbr':fields.char('Nombre',size=64),
#        'flia_parent':fields.char('Parentezco',size=40),
#        'flia_telf':fields.char('Telefono',size=64), 
#        'flia_dir':fields.char('Direccion',size=128),
#        
#        #INFORMACION ADICIONAL
#        'ubicacion':fields.char('Ubicacion',size=40),
#        'hipoteca':fields.boolean('Hipoteca'),
#        'avaluo':fields.integer('Avaluo Comercial'),
#        'marca':fields.char('Marca',size=20),
#        'modelo':fields.char('Modelo',size=20),
#        'anio':fields.integer('Año'),
#        'avaluov':fields.integer('Avaluo Comercial'),
#              }    
#
#res_partner_address()

class referencia_bancos(osv.osv):
    _name = 'referencia.bancos'
    _description = 'Referencias de Bancos'
    _columns = {
                'banco_name':fields.char('Banco',size=128),
                'banco_class':fields.char('Clase',size=64),
                'banco_number':fields.char('Nro. Cuenta',size=64),
                'ref_banco': fields.many2one('res.partner', 'Referencias de Bancos'),
                }

referencia_bancos() 

class referencia_bancarias(osv.osv):
    _name = 'referencia.bancarias'
    _description = 'Referencias Bancarias e Instituciones'
    _columns = {
                'inst':fields.char('Institucion',size=128),
                'inst_monto':fields.integer('Monto'),
                'inst_class':fields.char('Clase',size=64),
                'inst_plazo':fields.integer('Plazo'),
                'descripcion':fields.char('Institucion',size=128),
                'ref_inst': fields.many2one('res.partner', 'Referencia Institucional'),
                }

referencia_bancarias() 

class referencia_personal(osv.osv):
    _name = 'referencia.personal'
    _description = 'Referencias Personales'
    _columns = {
                'pers_nmbr':fields.char('Nombre',size=64),
                'pers_telf':fields.char('Telefono',size=64), 
                'ref_pers': fields.many2one('res.partner', 'Referencia Personal'),
                }

referencia_personal() 


