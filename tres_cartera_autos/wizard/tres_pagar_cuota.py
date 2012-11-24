
import time

from osv import osv, fields
from tools.translate import _
from point_of_sale.wizard import pos_box_entries
import netsvc

class tres_pagar_cuota(osv.osv_memory):
    _name = 'tres.pagar.cuota'
    _description = 'Point of Sale Payment'
   
    def check_tres(self, cr, uid, ids, context=None):
        context = context or {}
        order_obj = self.pool.get('tres.cartera')
        obj_partner = self.pool.get('res.partner')
        #analizar funcion con explicacion
        active_id = context and context.get('active_id', False)
        order = order_obj.browse(cr, uid, active_id, context=context)
        if not order.adicional_ids:
            amount = order.total_pagare - order.amount_paid
        else:
            amount = order.total_letras - order.amount_paid
    #            amountp =order.total_pagare - order.amount_paid_adic
        data = self.read(cr, uid, ids, context=context)[0]
    
        if amount != 0.0:
            order_obj.add_payment(cr, uid, active_id, data, context=context)
    
    #        if order_obj.test_paid_letras(cr, uid, [active_id]):
    #            print "entratesle"
    #            wf_service = netsvc.LocalService("workflow")
    #            wf_service.trg_validate(uid, 'tres.line.letras', active_id, 'pagados', cr)  
    #            return self.print_report(cr, uid, ids, context=context)         
        
        if order_obj.test_paid(cr, uid, [active_id]):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'tres.cartera', active_id, 'cancelada', cr)  
            return self.print_report(cr, uid, ids, context=context)  
        
    
        return self.launch_payment(cr, uid, ids, context=context)
    
    def launch_payment(self, cr, uid, ids, context=None):
        return {
            'name': _('Pagos'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tres.pagar.cuota',
            'view_id': False,
            'target': 'new',
            'views': False,
    #            'type': 'ir.actions.act_window',
        }
    
    def print_report(self, cr, uid, ids, context=None):
        active_id = context.get('active_id', [])
        datas = {'ids' : [active_id]}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'tres.receipt',
            'datas': datas,
        }
    #    def print_report(self, cr, uid, ids, context=None):
    #        msg = _('Cuota excede el Precio ')
    #        raise osv.except_osv(_('Configuration Error !'), msg)
    
    def _default_journal(self, cr, uid, context=None):
        res = pos_box_entries.get_journal(self, cr, uid, context=context)
        return len(res)>1 and res[1][0] or False
    
    def _default_amount(self, cr, uid, context=None):
        order_obj = self.pool.get('tres.cartera')
        add_obj = self.pool.get('tres.cartera.adicionales')
        active_id = context and context.get('active_id', False)
        if active_id:
            order = order_obj.browse(cr, uid, active_id, context=context)
    #            if not order.adicional_ids:
            return order.cuota_mes
    #            else:
    #                    for adi in add_obj.browse(cr, uid,active_id, context=context): 
    #                        if adi.adicional_id==active_id:
    #                            print "adiciona"
    #                            print add.adicional_id
    #                            print "active"
    #                            print active_id
    #                            return adi.valor_interes         
        return False
        
    _columns = {
        'journal': fields.selection(pos_box_entries.get_journal, "Payment Mode", required=True),
        'amount': fields.float('Amount', digits=(16,2), required= True),
    #        'amountp': fields.float('AmountP', digits=(16,2), required= True),
        'payment_name': fields.char('Payment Reference', size=32),
        'payment_date': fields.date('Payment Date', required=True),
    }
    _defaults = {
        'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'amount': _default_amount,
    #        'amountp':_default_amount,
        'journal': _default_journal
    }

tres_pagar_cuota()
