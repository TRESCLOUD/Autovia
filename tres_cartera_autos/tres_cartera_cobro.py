# Modelo que permite realizar los pagos de los haberes pendientes de los clientes
# EL formulario dependera del lugar donde se abra, pero permitira pagar mas de un haber a la vez,
# Para lograrlo, se busca en el objeto tres_linea_estado_cuenta y se identifica por nombre del cliente,
# pasando necesariamente por el objeto solicitud de credito
# Autor: Patricio Rangles

from osv import osv
from osv import fields
import time
# uso de datetime
from datetime import datetime
# uso de relativedelta
from dateutil.relativedelta import relativedelta
# si se quiere usar mensajes de error del sistema, esta linea debe usarse!!!
from tools.translate import _
from point_of_sale.wizard import pos_box_entries

class tres_linea_estado_cuenta_abono(osv.osv):

    '''
    objeto que ayuda a la relacion entre el estado de cuenta y el cobro respectivo, permitiendo asignar varios haberes
    a un cobro 
    '''
    
    _name = 'tres.linea.estado.cuenta.abono'
    
    def onchange_cancelado(self, cr, uid, ids, valor_abonado, valor_interes , context=None):
        
        #cuando cambia el estado del cancelado, debe evitarse que puede editarse el valor a pagar (Vista)
        #debe setearse el valor total restante a cancelar
        
        por_cancelar = float(valor_interes - valor_abonado)
        
        result = {'value':{
                            'valor_pago': por_cancelar,
                            }
                  }
        
        return result

    
    
    _columns = {
        'name': fields.char(string='Nombre', size=32),
        'estado_cuenta_id': fields.many2one('tres.linea.estado.cuenta', 'Pendiente de Pago'),
        'cobro_id': fields.many2one('tres.cartera.cobro', 'Cobro'),
        'valor_abonado': fields.float('Abonado', digits=(5,2)),
        'date_pago': fields.date('Fecha de Pago'),
        'date_vencimiento': fields.date('Fecha de Vencimiento'),
        'cancelado': fields.boolean('Cancelado'),
        'valor_interes':fields.float('Valor a Pagar', digits=(5,2)),
        'partner_id': fields.related('estado_cuenta_id','partner_id',type='many2one',relation='res.partner',string='Cliente',store=True),
        'valor_pago': fields.float(string="A Pagar", digits=(5,2)),
        'interes_mora': fields.float(string="Interes Por Mora", digits=(5,2)),
                }
    
tres_linea_estado_cuenta_abono()


class tres_cartera_cobro(osv.osv):

    '''
    Objeto que contiene la lista de cobros realizados a los clientes, este objeto debe permitir registrar el cobro
    respectivo a travez de caja, tambien debera permitir asignar depositos realizados y asignar a cada haber
    como abono o pago
    
    Metodos de pago:
    - Efectivo
    - Cheque
    - Deposito (papeleta de deposito, transferencia bancaria o cualquier otro tipo de movimiento bancario)
    
    Para los 2 primeros metodos deben registrarse a travez de caja, los depositos simplemente deben cotejarse con los haberes
     
    '''
    
    _name = 'tres.cartera.cobro'
    
    def _default_journal(self, cr, uid, context=None):
        res = pos_box_entries.get_journal(self, cr, uid, context=context)
        return len(res)>1 and res[1][0] or False


    def _suma_total(self, cr, r, context=None):

        # variable con el valor total a pagar
        total_pago = 0.0
        #analizo las lineas de cobro que tengo
        for r_l in r.detalle_pago_ids:
            
            #verifico si se va o no a cancelar un valor
            if r_l.cancelado:
                # se esta cancelando este haber, se suma completo lo que falta abonar
                # ademas se suma el interes acumulado por mora
                if r_l.interes_mora < 0:
                    # no se puede calcular, el interes no puede ser negativo
                    raise osv.except_osv(_('Error !'), _('Existe un valor negativo como valor de interes!!'))
                    
                total_pago = total_pago + float(r_l.valor_interes - r_l.valor_abonado) + r_l.interes_mora
                
            else:
                # caso contrario, debe sumarse el valor asignado en el pago
                # se verifica que el valor sea mayor a 0
                if r_l.valor_pago >= 0.0:
                    
                    if r_l.interes_mora < 0:
                        # no se puede calcular, el interes no puede ser negativo
                        raise osv.except_osv(_('Error !'), _('Existe un valor negativo como valor de interes!!'))

                    total_pago = total_pago + r_l.valor_pago#  + r_l.interes_mora
                     
                else:
                    # no se puede calcular, hay un valor negativo
                    raise osv.except_osv(_('Error !'), _('Existe un valor negativo como pago!!'))
            
        return total_pago
    
    def pagar(self, cr, uid, ids, context=None):
        # Primero: Verificamos que este correcto el pago(sume igual)
        # Segundo: borramos las lineas que no tengan pago asignado
        # Tercero: Guardar en la respectiva linea de estado de cuenta el abono respectivo (estado cancelado)
        
        # CUarto: guardar los valores pagados (automatico)
        # Quinto: Una vez que el pago es acreditado, verificar si se ha finalizado el pago del contrato
        # y setearlo como cancelado
                        
        #Verificando los pagos asignados
        # de la lista que esta asignada se verifica que tenga marcado el campo cancelar o que tenga puesto un valor
        # diferente de 0.0
        records = self.browse(cr,uid,ids)
        estado_cuenta = self.pool.get('tres.linea.estado.cuenta')
        estado_abono = self.pool.get('tres.linea.estado.cuenta.abono')
        
        for r in records:
                 
            total_pago = self._suma_total(cr, r, context=context)
            
            #Una vez sumado todos los valores, verifico que sean iguales al pago general
            #ya que se usan 2 decimales, el aproximado sera sobre +/- 1 centavo
            diferencia = int((total_pago - r.amount) * 100)
            
            if diferencia == 0:
                #el amount total coincide, se asigna el pago

                #Borrado de lineas en blanco
                for r_l in r.detalle_pago_ids:
                    # analizo cada linea y verifico si sera cancelada o no
                    if not r_l.cancelado:
                        # se verifica que el valor sea mayor a 0
                        if not (r_l.valor_pago > 0.0):
                            #no hay ningun valor a cancelar, se elimina de la linea
                            #r.unlink(cr, uid, r_l.id)
                            estado_abono.unlink(cr, uid, r_l.id)
                            continue
               
                    #Si se llega a este punto, se trabaja sobre a linea efectuando el pago
                    linea_abonada = estado_cuenta.read(cr, uid, r_l.estado_cuenta_id.id)
                    
                    # la mejor manera de cancelar un haber es seteando la opcion de cancelar
                    if r_l.cancelado:
                        # se pone abonado = al total del haber
                        linea_abonada['abonado'] = linea_abonada['valor_interes'] + r_l.interes_mora
                        # se cancela el haber
                        linea_abonada['state'] = 'cancelado'
                        linea_abonada['date_pago']=r.fecha
                        linea_abonada['metodo_pago']=r.metodo_pago
                    else:
                        # se aumenta lo abonado
                        nuevo_abono = linea_abonada['abonado'] + r_l.valor_pago
                        linea_abonada['state'] = 'abonado'
                        # se verifica que el nuevo abono no exeda el valor total
                        if nuevo_abono > (linea_abonada['valor_interes'] + r_l.interes_mora):
                            #es preferible usar la opcion de cancelar, se informa al usuario
                            raise osv.except_osv(_('Error !'), _('Existe un pago que exede el valor pendiente, si desea cancelar un haber, seleccione la opcion "Cancelar"!!'))
                        
                        elif nuevo_abono == (linea_abonada['valor_interes'] + r_l.interes_mora):
                            #no se uso la opcion de cancelar, pero coincide el valor
                            # se cancela el haber
                            linea_abonada['state'] = 'cancelado'
                            linea_abonada['date_pago']=r.fecha
                            linea_abonada['metodo_pago']=r.metodo_pago
                        # el abono es valido, lo seteo
                        linea_abonada['abonado'] = linea_abonada['abonado'] + + r_l.valor_pago
                        linea_abonada['date_pago']=r.fecha
                        linea_abonada['metodo_pago']=r.metodo_pago
                    estado_cuenta.write(cr, uid, r_l.estado_cuenta_id.id, {'abonado': linea_abonada['abonado'],
                                                                           'state': linea_abonada['state'],
                                                                           'date_pago':linea_abonada['date_pago'],
                                                                           'metodo_pago':linea_abonada['metodo_pago'],})

                # Manejo del PAGO: 
                # depende del tipo de pago, si es efectivo o cheque debe usarse un journal
                # y reflejarse en la respectiva caja, si es otro tipo, solo se asigna el pago
                # Se registra en el journal respectivo para que se refleje el ingreso en la respectiva caja,
                # esto depende del tipo de pago
                if r.metodo_pago == 'efectivo' or r.metodo_pago == 'cheque':
                    self.get_in(cr, uid, ids, context)
                                    
                #Cambio de estado a "pagado"
                self.write(cr, uid, r.id, {'state':'pagado'})
                
                # Indicar si el contrato esta o no cancelado
                # verifico que contratos pudieron haberse cancelado para cambiar su estado
                # 1: en base al cliente busco que contratos tiene en cartera
                tres_cartera_obj = self.pool.get('tres.cartera')
                tres_lec_obj = self.pool.get('tres.linea.estado.cuenta')
                
                contratos = tres_cartera_obj.search(cr, uid, [('partner_id', '=', r.partner_id.id),
                                                              ('state', '=', 'cartera')])
                # 2:para cada contrato verifico si tiene o no haberes pendientes
                for contrato in contratos:
                    # Busco el numero de haberes pendientes, es decir No cancelados
                    haberes = tres_lec_obj.search(cr, uid, [('lineaestado_id', '=', contrato),
                                                            ('state','not in', ('cancelado',))])
                    if len(haberes) == 0:
                        # debo marcar este contrato como cancelado!!!
                        if tres_cartera_obj.cancelada(cr, uid, contrato):
                            #Contrato cancelado!!
                            info_contrato = tres_cartera_obj.read(cr, uid, contrato, ['name', 'partner_id'])
                            mensaje = []
                            mensaje.append('El contrato')
                            mensaje.append(info_contrato['name'])
                            mensaje.append('del cliente')
                            mensaje.append(info_contrato['partner_id'][1]) 
                            mensaje.append('ha sido Cancelado')
                            mensaje = ' '.join(mensaje)
                            #TODO: Mostrar un mensaje al usuario que l indique cuales son los contratos
                            #Cancelados
                            #raise osv.except_osv(_('Aviso:'), _(mensaje))
                
            else:
                #hay diferencia!!
                raise osv.except_osv(_('Warning !'), _('El amount pagado difiere de los pagos efectuados!!'))
        # Depende del tipo de pago, no siempre va hacia caja 
        #self.get_in(cr, uid, ids, context) 
        return True


    def _total_pagar(self, cr, uid, ids, field_name, args, context=None):

        result = {}

        for r in self.browse(cr, uid, ids):
        
            total_pago = self._suma_total(cr, r, context=context)
        
            result[r.id] = {
                'suma_total': total_pago,
                    }
        
        return result

    def onchange_cliente_interes(self, cr, uid, ids, cliente, interes_mora ,fecha, context=None):

        # A cambiar de cliente se recalcula las lineas a mostrar y tambien se eliminan las lineas existentes
        
        #set default values
        #default = {}

        # Eliminar lineas existentes
        lineas_cobro = self.pool.get('tres.linea.estado.cuenta.abono')

        #drop existing lines
        line_ids = ids and lineas_cobro.search(cr, uid, [('cobro_id', '=', ids[0])]) or False
        if line_ids:
            lineas_cobro.unlink(cr, uid, line_ids)

        # Buscando nuevas lineas
        res = self.recalcular_lineas_cobro(cr, uid, cliente, interes_mora,fecha)
        
        #asignando las nuevas lineas
        default = {'value': {
            'detalle_pago_ids': res,
            #'cliente': cliente,
            }
        }
        
        #no se puede agregar por este metodo debido a que no hay un id para el cobro aun
        #for detalle in res:
            # agrego al tree las lineas nuevas
            #lineas_cobro.create(cr, uid, detalle)
        
        return default

    def recalcular_lineas_cobro(self, cr, uid, partner_id, interes_mora,fecha):
        # funcion que genera las lineas a pagar asociadas al cliente, debe buscar en la tabla de cartera
        # los contratos relacionados al cliente en estado "cartera", de ahi extraer los pagos pendientes o
        # "en espera", debe ordenarse por fecha de pago

        #inicializo la variable
        DATETIME_FORMAT = "%Y-%m-%d"
        hasta = fecha
        default = []

        #objeto general del estado de cuenta
        estado_cuenta_obj = self.pool.get('tres.linea.estado.cuenta')
        #FILTRADO por cliente, estado del haber
        lineas_estado_cuenta_por_cliente = estado_cuenta_obj.search(cr, uid, [('partner_id','=',partner_id),
                                                                              ('state','not in',('cancelado','anulado', 'renegociado','embargado')),])
        
        # genero la linea para cada id encontrado
        for linea in lineas_estado_cuenta_por_cliente:
            
            id_solicitud = False
            codigo_solicitud = False
            
            #creo la linea de cobro en base a la linea encontrada
            linea_cobro = estado_cuenta_obj.read(cr, uid, linea)

            try:
                #Obtengo el id del tres.cartera
                #hay un problema al sacar este valor, sale una tupla que tiene un numero y un unicode
                id_solicitud = linea_cobro['lineaestado_id'][0]
            except:
                id_solicitud = False

            if id_solicitud:
                # Tengo la solicitud id, leo el valor del codigo de contrato
                solicitud_read = self.pool.get('tres.cartera').read(cr, uid, id_solicitud, ['name'])
                codigo_solicitud = solicitud_read['name']
                
            if not codigo_solicitud:
                codigo_solicitud = ''

            #Se transforma la fecha de vencimiento del pago
            #TODO,  bug en caso de no existir fecha de vencimiento
            desde_dt = datetime.strptime(linea_cobro['date_vencimiento'], DATETIME_FORMAT)
          #  hasta_dt = datetime.strptime(hasta, DATETIME_FORMAT)
            hasta_dt = datetime.strptime(hasta, '%Y-%m-%d %H:%M:%S')   
            #esta parte verifica si han pasado 3 meses y calcula los intereses en mora
            fecha_inicio_mora = desde_dt + relativedelta(months=3)
                
            interes_calculado = 0.0  

            if fecha_inicio_mora <= hasta_dt:
                #ha pasado el tiempo necesario, debe calcularse el interes extra
                #Se determina los meses completos que esta el cliente en mora
                
                # Se calcula en base a los pagos el interes que se debe ir acumulando
                # filtramos todos los pagos o abonos hechos a este haber
                #objeto general de las lineas de pago
                pagos_cuenta_obj = self.pool.get('tres.linea.estado.cuenta.abono')
                #objeto que contiene la asignacion de cada pago
                cobro_obj = self.pool.get('tres.cartera.cobro')
                
                # FILTRADO por haberes, mostramos los pagos de este haber
                # se debe excluir aquellos que su pago este como Borrador o Anulado
                # Primero se buscan los pagos asignados a este haber
                pagos_estado_cuenta_por_haber = pagos_cuenta_obj.search(cr, uid, [('estado_cuenta_id', '=', linea),])
                
                # Segundo se filtran los pagos que efectivamete se hayan efectuado
                for pago in pagos_estado_cuenta_por_haber:
                    # leo el pago para extraer el id del cobro que lo contiena
                    info_pago = pagos_cuenta_obj.read(cr, uid, pago)
                    # Con el id anterior leo y verifico si esta efectuado el pago
                    info_cobro = cobro_obj.read(cr, uid, info_pago['cobro_id'][0])
                    # verifico si esta en el estado de "pagado" 
                    if info_cobro['state'] == 'pagado':
                        # esta pagado, calculo su posible interes

                        # Con cada id de cobro encontrado calculo el interes y lo acumulo de manera general
                        # Para calcular el interes se sigue la siguiente logica
                        # Se usa la fecha de vencimiento del haber y la fecha de pago, con esto obtengo el numero de meses
                        # el interes lo obtengo del formulario y el valor sobre el cual se calcula esta basado en el monto pagado
                        #for pago in pagos_estado_cuenta_por_haber:
    
                        #creo la linea de cobro en base a la linea encontrada
                        linea_pago = pagos_cuenta_obj.read(cr, uid, pago)
                        
                        # usando la fecha de vencimiento general desde_dt, calculo el interes de este pago
                        # la fecha desde la cual se cobra interes es desde_dt + 3 meses = fecha_inicio_mora
                        # Notese que la fecha de pago debe obtenerse desde el cobro general 
                        #linea_pago['date_pago'] es desde el pago, no desde el cobro
                        fecha_pagado = info_cobro['fecha']
                        # Elimino el texto estra existente en este valor de fecha
                        fecha_pagado = fecha_pagado[:fecha_pagado.rindex(" ")]
                        fecha_pago_dt = datetime.strptime(fecha_pagado, DATETIME_FORMAT) 
                        
                        if fecha_inicio_mora <= fecha_pago_dt:
                            # para este pago ya existio interes, se lo calcula
                            # Se determina los meses completos que esta el cliente en mora
                            # numero de meses en mora
                            meses = 0
                            temp_inicio = desde_dt
                            
                            while temp_inicio < fecha_pago_dt:
                                #sumo un mes mas
                                temp_inicio = temp_inicio + relativedelta(months=1)
                                meses = meses + 1 
                            
                            # Tengo los meses en mora, el interes y el pago, calculo el interes
                            interes_calculado = interes_calculado + float((linea_pago['valor_pago'] * interes_mora * meses)/100)
                
                #Tengo el interes acumulado, ahora calculo el interes del saldo
                saldo =  linea_cobro['valor_interes'] - linea_cobro['abonado']
                
                # numero de meses en mora
                meses = 0
                temp_inicio = desde_dt
                
                while temp_inicio < hasta_dt:
                    #sumo un mes mas
                    temp_inicio = temp_inicio + relativedelta(months=1)
                    meses = meses + 1 
            
                #calculo el interes:
                interes_calculado = interes_calculado + float((saldo * interes_mora * meses)/100)
            
                            
            rs = {
                'name': linea_cobro['name'],
                'estado_cuenta_id': linea_cobro['id'],
                #'cobro_id': self.id,
                'valor_abonado': linea_cobro['abonado'],
                'valor_interes': linea_cobro['valor_interes'],
                'date_vencimiento': linea_cobro['date_vencimiento'],
                'cancelado': False,
                'interes':linea_cobro['interes'],
                'valor_pago': 0.0,#valor_pago,
                'interes_mora': interes_calculado, 
            }
            
            default.append(rs)

        return default
 
    
    _columns = {
        # modificaciones Ruth: se altera elcampo que debe ser seleccion que es el metodo de pago 
        'name': fields.char('Descripcion', size=64, translate=True),
        'amount': fields.float('Monto', digits=(16, 2)),
        'fecha': fields.datetime('Fecha', select=True),
        'fecha_creacion': fields.datetime('Fecha de Creacion', select=True),
        'ref_pago': fields.char('Referencia de pago', size=64),
        'metodo_pago': fields.selection([
            ('efectivo', 'Efectivo'),
            ('cheque', 'Cheque'),
            ('deposito', 'Deposito')],'Tipo de Pago'),
        # fin modificaciones
        #'partner_id': fields.related('detalle_pago_ids','partner_id',type='many2one',relation='tres.cartera', string='Cliente', store=True),
        'partner_id': fields.many2one('res.partner', 'Cliente'),
        'detalle_pago_ids': fields.one2many('tres.linea.estado.cuenta.abono', 'cobro_id', 'Asignacion Pago'),
        #
        'journal_id': fields.selection(pos_box_entries.get_journal, "Caja Registradora", size=-1),
        'ref': fields.char('Ref', size=32),
        #'suma_total': fields.float(string='Suma Total', digits=(5,2)),
        'suma_total': fields.function(_total_pagar, method=True, type='float', digits=(5,2), string='Total a Pagar', multi=True),
        'note': fields.text('Notas de Pago'),
        'state': fields.selection([
            ('draft', 'Nuevo'),
            ('pagado', 'Pagado'),
            ('anulado', 'Anulado'),],
            'State', readonly=True),
        'interes_mora': fields.float(string="Interes Por Mora", digits=(5,2)),
        'user_id': fields.many2one('res.users', 'Usuario', readonly=True),
                }

    _defaults = {
        # modifico el default para setearlo en los campos correspondientes
        #'name': 'efectivo',
        'metodo_pago': 'efectivo',
        'fecha': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'fecha_creacion': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'partner_id': lambda self, cr, uid, context : context['partner_id'] if context and 'partner_id' in context else None,
        'state': 'draft',
        'interes_mora': 3, 
        'journal_id': _default_journal,
        'user_id': lambda self, cr, uid, context: uid,
                }
    
    def get_in(self, cr, uid, ids, context=None):
        """
             Create the entry of statement in journal.
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return :Return of operation of product
        """
        statement_obj = self.pool.get('account.bank.statement')
        res_obj = self.pool.get('res.users')
        product_obj = self.pool.get('product.product')
        bank_statement = self.pool.get('account.bank.statement.line')
        property_obj = self.pool.get('ir.property') 
        tres=self.pool.get('tres.cartera.cobro')

        ids1 = product_obj.search(cr, uid, [('income_pdt', '=', True)], order='id', context=context)
        
        if not ids1:
            raise osv.except_osv(_('Error !'), _('Necesita un producto para usarce como entrada de caja!!'))
            
        #res = product_obj.read(cr, uid, ids[0], ['id', 'name'], context=context)
        
        for data in  self.read(cr, uid, ids, context=context):
            vals = {}
            curr_company = res_obj.browse(cr, uid, uid, context=context).company_id.id
            statement_id = statement_obj.search(cr, uid, [('journal_id', '=', int(data['journal_id'])), ('company_id', '=', curr_company), ('user_id', '=', uid), ('state', '=', 'open')], context=context)
            if not statement_id:
                raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))

            #product = product_obj.browse(cr, uid, int(data['product_id']))
            product = product_obj.browse(cr, uid, ids1[0])
            acc_id = product.property_account_income or product.categ_id.property_account_income_categ
            if not acc_id:
                raise osv.except_osv(_('Error !'), _('Please check that income account is set to %s')%(product_obj.browse(cr, uid, ids1[0]).name))
            if statement_id:
                statement_id = statement_id[0]
            if not statement_id:
                statement_id = statement_obj.create(cr, uid, {
                                    'date': time.strftime('%Y-%m-%d 00:00:00'),
                                    'journal_id': data['journal_id'],
                                    'company_id': curr_company,
                                    'user_id': uid,
                                }, context=context)

            vals['statement_id'] = statement_id
            vals['journal_id'] = data['journal_id']
            if acc_id:
                vals['account_id'] = acc_id.id
            vals['amount'] = data['amount'] or 0.0
            vals['partner_id']= data['partner_id'][0]
            vals['ref'] = "%s: %s " %  ("Cobro",data['id'] )
            vals['name'] = "%s: %s " % ("Cobro", data['name'])
            bank_statement.create(cr, uid, vals, context=context)
        return {}
    #A.G 12/09/2012 SE 
    #CREO FUNCION UNLINK PARA QUE NO SE 
    #PUEDAN ELIMINAR LOS PAGOS POR ERROR    
    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
                if rec.state not in ('draft'):
                    raise osv.except_osv(_('No se puede Eliminar !'), _('En Pagos para borrar un pago, este deberia ser nuevo'))
        return super(tres_cartera_cobro, self).unlink(cr, uid, ids, context=context)

tres_cartera_cobro()
