
import time

from osv import osv, fields
from tools.translate import _
import netsvc

class tres_renegociado(osv.osv_memory):
    
    _name = 'tres.renegociado'
    _description = 'Renegociado'
      
    def copy(self, cr, uid, ids, context=None):
        
        obj_solicitud = self.pool.get('tres.cartera')
        obj_history = self.pool.get('tres.cartera.history')
        
        r =  obj_solicitud.browse(cr, uid, context['active_id'])

        result = {
            'cuota_mes': r.cuota_mes,
            'company_id': r.company_id.id,
            'product_id': r.product_id.id,
         #   'entrega': r.entrega,
            'name': r.name,
            'date_order': r.date_order,
            'date_creacion': r.date_creacion,
            'user_id': r.user_id.id,
            'note': r.note,
            'cedula': r.cedula,  
            'partner_id': r.partner_id.id,
            'garante_id': r.garante_id.id,
            'cyg_partner_id': r.cyg_partner_id.id,
            'cyg_garante_id': r.cyg_garante_id.id,
            'price': r.price,
            'pago_l': r.pago_l,
            'financiamiento': r.financiamiento, 
            'interes': r.interes,
            'monto_financiar': r.monto_financiar,
            'total_letras': r.total_letras,
            'total_pagare': r.total_pagare,
            'total_pagare_texto': r.total_pagare_texto,
            'sin_garante': r.sin_garante, 
            'entrada': r.entrada,
            'price_total': r.price_total,
            'state':'renegociar',
            'copy_predio': r.copy_predio,
            'copy_rol': r.copy_rol,
            'copy_ruc': r.copy_ruc,
            'copy_ci': r.copy_ci,
            'copy_papeleta': r.copy_papeleta,
            'copy_pago': r.copy_pago,
            'abono': r.abono, 
            'copy_predio_resultgrt': r.copy_predio_grt,
            'copy_rol_grt': r.copy_rol_grt,
            'copy_ruc_grt': r.copy_ruc_grt,
            'copy_ci_grt': r.copy_ci_grt,
            'copy_papeleta_grt': r.copy_papeleta_grt,
            'copy_pago_grt': r.copy_pago_grt,
            'copy_pago_grt': r.copy_pago_grt,
            'date_history': time.strftime('%Y-%m-%d %H:%M:%S'),                             
            } 

        datos_id = obj_history.create(cr, uid, result, context)
        obj_repo1 = self.pool.get('tres.linea.estado.cuenta')
        lista_ids = obj_repo1.search(cr, uid, [('lineaestado_id', '=', r.id)])
        obj_repo1.write(cr, uid, lista_ids, {'state':'renegociado', 'lineaestado_id': datos_id })
        obj_solicitud.write(cr, uid, r.id, {'state':'renegociar'})       
                           
        return result

tres_renegociado()