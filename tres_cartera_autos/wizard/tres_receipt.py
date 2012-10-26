from osv import osv
from tools.translate import _

class tres_receipt(osv.osv_memory):
    _name = 'tres.receipt'
    _description = 'Tres Cartera Autos receipt'

    def view_init(self, cr, uid, fields_list, context=None):
        order_lst = self. pool.get('tres.cartera').browse(cr, uid, context['active_id'], context=context)

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'tres.receipt',
            'datas': datas,
        }

tres_receipt()
