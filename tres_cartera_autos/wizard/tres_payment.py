import time

from osv import osv, fields
from tools.translate import _
import pos_box_entries
import netsvc


class tres_make_payment(osv.osv_memory):
    _name = 'tres.make.payment'
    _description = 'tres Payment'
    def check(self, cr, uid, ids, context=None):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        context = context or {}
        order_obj = self.pool.get('tres.cartera')
        obj_partner = self.pool.get('res.partner')
        active_id = context and context.get('active_id', False)

        order = order_obj.browse(cr, uid, active_id, context=context)
        amount = order.amount_total - pago_obj.monto
        data = self.read(cr, uid, ids, context=context)[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        #data['journal'] = data['journal'][0]

        if amount != 0.0:
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        if order_obj.test_paid(cr, uid, [active_id]):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'tres.cartera', active_id, 'paid', cr)
            return self.print_report(cr, uid, ids, context=context)

        return self.launch_payment(cr, uid, ids, context=context)

    def launch_payment(self, cr, uid, ids, context=None):
        return {
            'name': _('Paiement'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tres.make.payment',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
        }

#    def _default_journal(self, cr, uid, context=None):
#        res = pos_box_entries.get_journal(self, cr, uid, context=context)
#        return len(res)>1 and res[1][0] or False

    def _default_amount(self, cr, uid, context=None):
        order_obj = self.pool.get('tres.cartera')
        pago_obj =self.pool.get('tres.make.payment')
        active_id = context and context.get('active_id', False)
        if active_id:
            order = order_obj.browse(cr, uid, active_id, context=context)
            return order.price - pago_obj.monto 
        return False

    _columns = {
        'journal': fields.selection(pos_box_entries.get_journal, "Payment Mode", required=True),
        'amount': fields.float('Amount', digits=(16,2), required= True),
        'payment_name': fields.char('Payment Reference', size=32),
        'payment_date': fields.date('Payment Date', required=True),
    }
    _defaults = {
        'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'amount': _default_amount,
        'journal': _default_journal
    }

tres_make_payment()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
