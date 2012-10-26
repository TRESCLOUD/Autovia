import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from osv import osv, fields
from tools.translate import _
from point_of_sale.wizard import pos_box_entries
#import pos_box_entries

class tres_cartera_egreso(osv.osv):
    _name = 'tres.cartera.egreso'
    _description = 'Tres Cartera Egreso'
    
    
    def _get_selection(self, cursor, user_id, context=None):
        return (
           ('cliente', 'Haberes clientes'),
           ('empresa', 'Gastos de la empresa'))

    
    _columns = {
        'name': fields.char('Description / Reason', size=32),
        'tipo_egreso': fields.selection((('cliente', 'Haberes clientes'), ('empresa', 'Gastos de la empresa')), "Tipo egreso"),
        'tipo_gasto': fields.selection((('embargo', 'Embargo'),('otro', 'Otros')), "Tipo de gasto"),
        'tres_cartera_id': fields.many2one('tres.cartera', 'Contrato'),
        'res_partner_id': fields.many2one('res.partner', 'Cliente'),
        'date': fields.datetime('Fecha de Creacion', select=False),
        'amount': fields.float('Monto', digits=(16, 2)),
        'detalle':fields.char('Detalle', size=128, readonly=False),
        'journal_id': fields.selection(pos_box_entries.get_journal, "Cash Register", size=-1),
    }
    _defaults = {
         'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
         'amount':0.0,
         'tipo_egreso':0,
         'tipo_gasto':0,
    }

    def update(self, cr, uid, ids, context={}):

        obj_contrato = self.pool.get('tres.linea.estado.cuenta')
        
        result={}
        valorState=''
        
        if context['tipo_gasto'] =='embargo':
            valorState = 'embargo'
            name = 'Pago embargo'
        else: 
            valorState = 'espera'
            name = 'Otro'     
            
                     
        for r in  self.browse(cr, uid, ids):
            
            result = {
                'tipo_haber':context['tipo_gasto'],
                'state': valorState,      
                'name':  name,
                'valor': r.amount,
                'lineaestado_id': r.tres_cartera_id.id,
                'partner_id': r.res_partner_id.id,  
                'date_vencimiento': r.date,                              
            } 
            datos_id = obj_contrato.create(cr, uid, result, context)         
            self.get_out(cr, uid, ids, context)
        return result
    
    def get_out(self, cr, uid, ids, context=None):

        print "entro"
        vals = {}
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        product_obj = self.pool.get('product.product')
        res_obj = self.pool.get('res.users')
        ids1 = product_obj.search(cr, uid, [('expense_pdt', '=', True)], order='id', context=context)
        
        if not ids1:
            raise osv.except_osv(_('Error !'), _('Necesita un producto para usarce como entrada de caja!!'))

        for data in  self.read(cr, uid, ids, context=context):
            curr_company = res_obj.browse(cr, uid, uid, context=context).company_id.id
            statement_ids = statement_obj.search(cr, uid, [('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid), ('state', '=', 'open')], context=context)
            monday = (datetime.today() + relativedelta(weekday=0)).strftime('%Y-%m-%d')
            sunday = (datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d')
            done_statmt = statement_obj.search(cr, uid, [('date', '>=', monday+' 00:00:00'), ('date', '<=', sunday+' 23:59:59'), ('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid)], context=context)
            stat_done = statement_obj.browse(cr, uid, done_statmt, context=context)
            am = 0.0
            
            product = product_obj.browse(cr, uid, ids1[0])
            acc_id = product.property_account_expense or product.categ_id.property_account_expense_categ
            if not acc_id:
                raise osv.except_osv(_('Error !'), _('please check that account is set to %s')%(product.name))
            if not statement_ids:
                raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))
            vals['statement_id'] = statement_ids[0]
            vals['journal_id'] = data['journal_id']
            vals['account_id'] = acc_id.id
            amount = data['amount'] or 0.0
            if data['amount'] > 0:
                amount = -data['amount']
            vals['amount'] = amount
            vals['name'] = "%s: %s " % (product.name, data['name'])
            statement_line_obj.create(cr, uid, vals, context=context)
        return {}
tres_cartera_egreso()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
