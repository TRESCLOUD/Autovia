# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import netsvc
from osv import fields, osv
from tools.translate import _
from decimal import Decimal
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class product_product_auto(osv.osv):
    _name = 'product.product.auto'
    _inherit = 'product.product'
    
  #A.G AUMENTO DE LA FUNCION NAME_GET  
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name', 'modelo','color','year','cae'], context=context)
        res = []

        for record in reads:
            if not record['name']=="Cash in":
                if not record['name']=="Cash out":
                    mensaje=[]        
                    mensaje.append(str(record['name']))
                    if record['modelo']:
                        mensaje.append(str(record['modelo']))
                    else:
                        mensaje.append("-")
                    if record['color']!=0:
                        mensaje.append(str(record['color']))
                    else:
                        mensaje.append("-")  
                    if record['year']:
                        mensaje.append(str(record['year']))
                    else:
                        mensaje.append("-")               
                    if record['cae']:
                        mensaje.append(str(record['cae']))
                    else:
                        mensaje.append("-") 
                
                    res.append((record['id'], mensaje))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)
    
    _columns = {
        'motor': fields.char('No. Motor', size=64),
        'chasis': fields.char('No. Chasis', size=64),
        'color': fields.char('Color', size=64),
        'clase': fields.char('Clase', size=64),
        'modelo': fields.char('Modelo', size=64),
        'cae': fields.char('CAE (Placa)', size=64),
        'matriculado': fields.char('Matriculado', size=64),
        'numero': fields.char('Numero', size=64),
        'year': fields.integer('Año de Fabricación', size=4),
        'propietario': fields.char('Propietario', size=64),
        'vendido':fields.boolean('vendido', help='Permite bloquear los autos vendidos',readonly=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'year_matricula': fields.integer('Año Matriculación', size=4),

    }
  
    _defaults = {
          'type' : lambda *a: 'consu',
    }
            #linea_cuenta_obj = self.pool.get('tres.linea.estado.cuenta')
        
        #reviso los id's registrados en las columnas respectivas, gracias a esto puedo extraer la info del cliente
        #esta funcion instancia de acuerdo al objeto, es decir si es cobro o si es cuota
        #for r in self.browse(cr, uid, ids):

    def _upper(self, valor):
        if valor:
            return valor.upper()
        else:
            return valor 

    def onchange_motor(self, cr, uid, ids, valor):
      v = {}
      v={'motor': self._upper(valor)}
      return {'value': v}
    
    def onchange_chasis(self, cr, uid, ids, valor):
      v = {}
      v={'chasis': self._upper(valor)}
      return {'value': v}

    def onchange_clase(self, cr, uid, ids, valor):
      v = {}
      v={'clase': self._upper(valor)}
      return {'value': v}
    
    def onchange_modelo(self, cr, uid, ids, valor):
      v = {}
      v={'modelo': self._upper(valor)}
      return {'value': v}
    
    def onchange_cae(self, cr, uid, ids, valor):
      v = {}
      v={'cae': self._upper(valor)}
      return {'value': v}
    
    def onchange_matriculado(self, cr, uid, ids, valor):
      v = {}
      v={'matriculado': self._upper(valor)}
      return {'value': v}
        
    def onchange_propietario(self, cr, uid, ids, valor):
      v = {}
      v={'propietario': self._upper(valor)}
      return {'value': v}
        
    def onchange_numero(self, cr, uid, ids, valor):
      v = {}
      v={'numero': self._upper(valor)}
      return {'value': v}

    def onchange_name(self, cr, uid, ids, valor):
      v = {}
      v={'name': self._upper(valor)}
      return {'value': v}

    def onchange_color(self, cr, uid, ids, valor):
      v = {}
      v={'color': self._upper(valor)}
      return {'value': v}

product_product_auto()

