# -*- coding: utf-8 -*-
import time
from datetime import datetime
#from datetime import date
from dateutil.relativedelta import relativedelta
import logging
#from PIL import Image·
#comentario de prueba en xxxxxxx

import netsvc
from osv import fields
from osv import osv
from tools.translate import _
#from decimal import Decimal
#import decimal_precision as dp

_logger = logging.getLogger(__name__)

# funcion general para todas las clases
def redondeo(Valor):
# Funcion que redondea un numero con las siguientes condiciones:
# desde .01 hasta .49, queda el mismo valor
# desde .50 hasta .99, se aproxima la parte entera
    
    # del valor entregado se extrae la parte decimal, con este valor se compara y se trabaja
    resultado=Valor
    resultado=int(resultado)
    # dejo la parte decimal
    parte_decimal=Valor-resultado
    #multiplico por 100 y verifico si es mayor a 50
    parte_decimal=parte_decimal * 100
    # se da algo curioso con un valor :393.50
    # si se extrae la parte entera, da como resultado 49!!!
    #parte_decimal=int(parte_decimal)
    # se genera el texto del numero
    texto_decimal=str(parte_decimal)
    parte_decimal=int(parte_decimal)
    
    if texto_decimal == "50.0":
        # Caso especial: suele aproximar hacia abajo en ciertos casos
        resultado += 1
    
    elif parte_decimal >= 50:
        resultado += 1

    return resultado


class tres_config_journal(osv.osv):
    _name = 'tres.config.journal'
    _description = "Journal Configuration"

    _columns = {
        'name': fields.char('Description', size=64),
        'code': fields.char('Code', size=64),
        'journal_id': fields.many2one('account.journal', "Journal")
    }

# para poder mostrar un estado de cuenta del cliente, debe crearse un objeto base sobre el cual se pueda registrar
# las lineas de cobro al cliente, cada linea tendra campos similares y debera identificar el tipo de cobro
# esto permite hacer un fltrado mas sencillo y registrar los cobros de manera mas homogenea

class tres_linea_estado_cuenta(osv.osv):
    '''
    Modelo que centraliza los haberes del cliente
    '''
    _name = 'tres.linea.estado.cuenta'
    #_description = 'Linea estado de cuenta'
    _table = 'tres_linea_estado_cuenta'


    def onchange_general(self, cr, uid, ids, meses, interes, valor, context=None):
        # se realiza on_change para el adicional para retornar su valor interes
        interes_mens=float(interes)/12/100
        valort=float(valor)*(1+(interes_mens*int(meses)))
        #se realiza la aproximancion, para eliminar los decimales
        valort=redondeo(valort)
        
        result = {'value': {
                            'valor_interes':valort,
                            }
                  }            
        return result
    
    def _dias_interes_mora(self, cr, uid, ids, field_name, arg, context=None):
        
        #DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        DATETIME_FORMAT = "%Y-%m-%d"
        hasta = time.strftime(DATETIME_FORMAT)

        result = {}
        
        #linea_cuenta_obj = self.pool.get('tres.linea.estado.cuenta')
        
        #reviso los id's registrados en las columnas respectivas, gracias a esto puedo extraer la info del cliente
        #esta funcion instancia de acuerdo al objeto, es decir si es cobro o si es cuota
        #for r in self.browse(cr, uid, ids):
        for i in ids:       

            # Agrego el calculo de los dias en mora, para mejorar la eficiencia del sistema
            # se modifica el nombre date_pago por date_vencimiento
            reg_date_vencimiento = self.read(cr, uid, i, ['date_vencimiento', 'state'])
            interes_calculado = 0.0  
            dias_mora = 0
            
            if not reg_date_vencimiento['date_vencimiento'] or reg_date_vencimiento['state'] == 'cancelado':
                interes_calculado = 0.0
                dias_mora = 0
            else:
                desde_dt = datetime.strptime(reg_date_vencimiento['date_vencimiento'], DATETIME_FORMAT)
                hasta_dt = datetime.strptime(hasta, DATETIME_FORMAT)
                timedelta = hasta_dt - desde_dt
    
                #esta parte verifica si han pasado 3 meses y calcula los intereses en mora
                fecha_inicio_mora = desde_dt + relativedelta(months=3)
                    
    
                if fecha_inicio_mora >= hasta_dt:
                    #ha pasado el tiempo necesario, debe calcularse el interes extra
                    #TODO: funcion que calcula el interes actual
                    interes_calculado = 0.0  
                
                
                if int(timedelta.days) > 0:
                    dias_mora = timedelta.days
            
            result[i]={
                   #'nombre_cliente': nombre,
                   #'partner_id': id_cliente,
                   'dias_mora': dias_mora,
                   'interes_mora_calc': interes_calculado,
            # campos agregados al calculo de resultados
                   #'abonado': 0.0,
                   #'cancelado': False,
                       }
            
        return result

    def meses(self, cr, uid, ids, context=None):      
       
        obj_repo = self.pool.get('tres.cartera.history')
        records = self.browse(cr, uid, ids)
        result = {}
        
        for r in records:

            result = {
                'cuota_mes': r.cuota_mes,
                'company_id': r.company_id.id,                             
                }
            saldo = r.total_pagare-r.abono
            self.write(cr, uid, ids, {'price':saldo}, context=context)
            datos_id = obj_repo.create(cr, uid, result, context)            
            obj_repo1 = self.pool.get('tres.linea.estado.cuenta')            
            lista_ids = obj_repo1.search(cr, uid, [('lineaestado_id', '=', r.id)])                         
            obj_repo1.write(cr, uid, lista_ids, {'state':'renegociado', 'lineaestado_id': datos_id })                   
        return self.write(cr, uid, ids, {'state':'renegociar'}, context=context)

    _columns = {
        # Modificado el campo name, ahora es la descripcion del haber
        'name': fields.char('Descripcion', size=256),
        # agregado el campo tipo_cuota para identifcarlo de mejor manera 
        'tipo_haber': fields.selection([
            ('cuota', 'Cuota'),
            ('adicional', 'Adicional'),
            ('entrada', 'Entrada'),
            ('embargo', 'Por embargo'),
            ('otro', 'Otros'),], 'Tipo', readonly=True),    
        'valor': fields.float('Valor'), 
        'meses':fields.integer('Meses'),
        'interes':fields.float('Interes'),
        'valor_interes': fields.float('Valor con Interes', digits=(5,2)), 
        'date_inicio': fields.date('Fecha Inicial'),
        'date_pago': fields.date('Fecha de Cobro'),
        'metodo_pago': fields.char('Metodo de Pago',size=20),
        # modificado date_pago para una mejor comprension del campo
		#ICE
        'date_vencimiento': fields.date('Fecha de Vencimiento', required=True),
        # se modifica el abonado para que se calcule en base alos pagos encontrados y realizados por el cliente
        'abonado': fields.float('Monto Cobrado', digits=(5,2)),
		#ICE store
        'dias_mora': fields.function(_dias_interes_mora, store=True, method=True, type='integer', string='Dias en Mora', multi=True),
        #ICE cambiar partner_id
        'lineaestado_id': fields.many2one('tres.cartera', 'Lineas de cuotas del contrato',ondelete= "restrict"),
        'partner_id': fields.related('lineaestado_id','partner_id',type='many2one',relation='res.partner',string='Cliente',store=True,readonly=True),
        'user_id': fields.many2one('res.users', 'Connected Salesman', help="Person who uses the the cash register. It could be a reliever, a student or an interim employee."),
        #ICE FIN
        'letra_entregada':fields.boolean('Letra Entregada', required=False),
        'letra_permiso':fields.boolean('Entregar letra', required=False,write=['tres_cartera_autos.group_tres_cartera'],read=['tres_cartera_autos.group_tres_cartera_log'] ),
        'state': fields.selection([
            ('espera', 'Esperando Pago'),
            #('en_mora', 'En Mora'),
            ('abonado', 'Abonado'),
            ('pagado', 'Pagado'),
            #('mora', 'En mora'), No se ocupa este estado, depende del tiempo asi que solo se compara con la fecha actual
            ('anulado', 'Anulada'),
            # Se necesita el estado de embargado para facilitar el filtrado
            ('embargo', 'Embargo'),
            # Estado cancelado, para indicar que este haber terminado de pagar, facilita el filtrado
            ('cancelado', 'Cancelado'),
            ('renegociado', 'Renegociado'),], 'State', readonly=True),
        'cancelado': fields.boolean("Cancelado"),
        #'history_id': fields.many2one('tres.cartera.history', 'History'),
        'history_id': fields.many2one('tres.cartera', 'History'),
        'interes_mora_calc': fields.function(_dias_interes_mora, method=True, type='float', string='Interes Por Mora', multi=True),
        'interes_mora_save': fields.float('Interes Pagado Por Mora', digits=(5,2)),

                }
    
    _defaults = {
            'state': 'espera',
            'tipo_haber': 'adicional',
            'name': 'Pago Adicional'
            #'partner_id' : lambda self, cr, uid, context : context['partner_id'] if context and 'partner_id' in context else None,
            #'partner_id':_cliente_ident,
                }   
    
    def _permiso_crear(self, cr, uid, ids, context=None):
        for statement in self.browse(cr, uid, ids, context=context):
            if not statement.partner_id:
                return False
        return True

    _constraints = [
        (_permiso_crear, 'Error! Usted no puede crear sin seleccionar el ciente.', ['partner_id'])
    ]
    
    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
               raise osv.except_osv(_('No se puede Eliminar !'), _('En Estado de Cuenta para borrar una cuota, este deberia ser nuevo o estar cancelado.'))
        return super(tres_linea_estado_cuenta, self).unlink(cr, uid, ids, context=context)
    
tres_linea_estado_cuenta()

class tres_linea_estado_cuenta_cuota(osv.osv):
  
    '''
    Modelo que hereda la clase de haberes general y permite registrar las cuotas respectivas 
    '''
    
    _name = 'tres.linea.estado.cuenta.cuota'
    #_description = 'Cuota'
    _inherit = 'tres.linea.estado.cuenta'
    
    _columns = {
        #'cuota_id': fields.many2one('tres.cartera', 'Cuota', select=True),
                }
   
    _defaults = {
        # modificado el campo name por tipo_haber como default
        'tipo_haber': 'cuota',
          }

tres_linea_estado_cuenta_cuota()

class tres_linea_estado_cuenta_adicional(osv.osv):
  
    '''
    Modelo que hereda la clase de haberes general y permite registrar los Adicionales respectivas 
    '''
    
    _name = 'tres.linea.estado.cuenta.adicional'
    #_description = 'Pago Adicional'
    _inherit = 'tres.linea.estado.cuenta'
    
    def onchange_general(self, cr, uid, ids, meses, interes, valor, context=None):
        # se realiza on_change para el adicional para retornar su valor interes
        interes_mens=float(interes)/12/100
        valort=float(valor)*(1+(interes_mens*int(meses)))
        #se realiza la aproximancion, para eliminar los decimales
        valort=redondeo(valort)
        
        result = {'value': {
                            'valor_interes':valort,
                            }
                  }            
        return result

    _columns = {
            }
   
    _defaults = {
        # modificado el campo name por tipo_haber como default
        # tambien en name va la descripcion del haber
        'tipo_haber': 'adicional',
        'name':'Pago Adicional',
        #'partner_id':_cliente_ident,
            }

tres_linea_estado_cuenta_adicional()

class tres_linea_estado_cuenta_otros(osv.osv):
  
    '''
    Modelo que hereda la clase de haberes general y permite registrar haberes varios 
    '''
    
    _name = 'tres.linea.estado.cuenta.otros'
    #_description = 'Pago Adicional'
    _inherit = 'tres.linea.estado.cuenta'
    
    _columns = {
        #'otros_id': fields.many2one('tres.cartera', 'Otros', select=True),
        'concepto': fields.char(string='Concepto', size=256),
            }
   
    _defaults = {
        # modificado el campo name por tipo_haber como default
        # tambien en name va la descripcion del haber
        'tipo_haber': 'otro',
        'name':'Otros'
      }

tres_linea_estado_cuenta_otros()

class tres_linea_estado_cuenta_entrada(osv.osv):
  
    '''
    Modelo que hereda la clase de haberes general y permite registrar haberes varios 
    '''
    
    _name = 'tres.linea.estado.cuenta.otros'
    #_description = 'Pago Adicional'
    _inherit = 'tres.linea.estado.cuenta'
    
    _columns = {
        #'otros_id': fields.many2one('tres.cartera', 'Otros', select=True),
        #'concepto': fields.char(string='Concepto', size=256),
            }
   
    _defaults = {
        # modificado el campo name por tipo_haber como default
        # tambien en name va la descripcion del haber
        'tipo_haber': 'entrada',
        'name':'Entrada'
      }

tres_linea_estado_cuenta_entrada()

class tres_cartera(osv.osv):
    _name = 'tres.cartera'
    _description = 'Cartera de Autos'
    _order='name'          
    
    def print_report(self, cr, uid, ids, context=None):
       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'reporte_reserva',    # the 'Service Name' from impresion_cheque                                 the report
            'datas' : {
                    'model' : 'tres.cartera',    # Report Model
                    'res_ids' : ids
                    }
                }
    def print_report_pagare(self, cr, uid, ids, context=None):
       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'reporte_pagare',    # the 'Service Name' from impresion_cheque                                 the report
            'datas' : {
                    'model' : 'tres.cartera',    # Report Model
                    'res_ids' : ids
                    }
                }     
        
    def print_report_contrato(self, cr, uid, ids, context=None):
       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'reporte_contrato',    # the 'Service Name' from impresion_cheque                                 the report
            'datas' : {
                    'model' : 'tres.cartera',    # Report Model
                    'res_ids' : ids
                    }
                } 
    def print_report_mutuo(self, cr, uid, ids, context=None):
       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'reporte_mutuo',    # the 'Service Name' from impresion_cheque                                 the report
            'datas' : {
                    'model' : 'tres.cartera',    # Report Model
                    'res_ids' : ids
                    }
                } 
    
    def tres_amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_paid': 0.0,
                'amount_paid_adic':0.0,
            }
#            if not order.adicional_ids:
        for payment in order.statement_ids:
            res[order.id]['amount_paid'] +=  payment.amount
            print payment.amount
        return res
    
    # Funciones que convierten a texto un valor numerico INICIO
        
    """
    Módulo numerals para convertir un número en una cadena literal del número.
    Autor: Chema Cortés - Agosto 1995 (Convertido de clipper a python en
    Septiembre 2001)
    Modificaciones: Infoprimo - Marcelo Zunino (marcelo@infoprimo.com)

    A sugerencia de su autor original, este código está bajo dominio público.
    """
    
    # las constantes permanecen globales para reducir el costo de la recursión.
    _n1 = ( "un","dos","tres","cuatro","cinco","seis","siete","ocho",
            "nueve","diez","once","doce","trece","catorce","quince",
            "dieciséis","diecisiete","dieciocho","diecinueve","veinte")
    
    _n11 =( "un","dós","trés","cuatro","cinco","séis","siete","ocho","nueve")
    
    _n2 = ( "dieci","veinti","treinta","cuarenta","cincuenta","sesenta",
            "setenta","ochenta","noventa")
    
    _n3 = ( "ciento","dosc","tresc","cuatroc","quin","seisc",
            "setec","ochoc","novec")

    def NumeroTextoCompleto(self,num):

        try:
            tmp = '%.2f' % float(num)
            ent = tmp.split(".")[0]
            fra = tmp.split(".")[1]

            enteros = self.numerals(int(ent))
            decimas = self.numerals(int(fra))

            # print "enteros: ", enteros, "decimas :", decimas

            if enteros == 'cero' and decimas != 'cero' :
                letras = " son centavillos, no merece un pagaré "
            else:
                if decimas == 'cero':
                    letras = enteros.upper() + " "
                else:
                    letras = enteros.upper() + " CON " + decimas.upper() + " /100" 
        except:
            letras = "acá hay algo que no me gusta..."

        self.numero = str(num)
        self.largo  = len(letras)
        self.escribir = letras
        return letras

    def numerals(self, nNumero):
        """
        numerals(nNumero) --> cLiteral

        Convierte el número a una cadena literal de caracteres
        P.e.:       201     -->   "doscientos uno"
                   1111     -->   "mil ciento once"

        """
        # función recursiva auxiliar esta es "la" rutina ;)
        def _numerals(n):

            # Localizar los billones
            prim,resto = divmod(n,10L**12)
            if prim!=0:
                if prim==1:
                    cRes = "un billón"
                else:
                    cRes = _numerals(prim)+" billones" # Billones es masculino
                if resto!=0:
                    cRes += " "+_numerals(resto)
            else:
            # Localizar millones
                prim,resto = divmod(n,10**6)
                if prim!=0:
                    if prim==1:
                        cRes = "un millón"
                    else:
                        cRes = _numerals(prim)+" millones" # Millones es masculino
                    if resto!=0:
                        cRes += " " + _numerals(resto)
                else:
            # Localizar los miles
                    prim,resto = divmod(n,10**3)
                    if prim!=0:
                        if prim==1:
                            cRes="mil"
                        else:
                            cRes=_numerals(prim)+" mil"
                        if resto!=0:
                            cRes += " " + _numerals(resto)
                    else:
            # Localizar los cientos
                        prim,resto=divmod(n,100)
                        if prim!=0:
                            if prim==1:
                                if resto==0:
                                    cRes="cien"
                                else:
                                    cRes="ciento"
                            else:
                                cRes=self._n3[prim-1]
                                cRes+="ientos"
                            if resto!=0:
                                cRes+=" "+_numerals(resto)
                        else:
            # Localizar las decenas
                            if n<=20:
                                cRes=self._n1[n-1]
                            else:
                                prim,resto=divmod(n,10)
                                cRes=self._n2[prim-1]
                                if resto!=0:
                                    if prim==2:
                                        cRes+=self._n11[resto-1]
                                    else:
                                        cRes+=" y "+self._n1[resto-1]
            return cRes

        # Nos aseguramos del tipo de <nNumero>
        # se podría adaptar para usar otros tipos (pe: float)
        nNumero = long(nNumero)
        if nNumero < 0:
            # negativos
            cRes = "menos "+_numerals(-nNumero)
        elif nNumero == 0:
            # cero
            cRes = "cero"
        else:
            # positivo
            cRes = _numerals(nNumero)

        # Excepciones a considerar
        if nNumero % 10 == 1 and nNumero % 100 != 11:
            cRes += "o"
        return cRes

# Funciones que convierten a texto un valor numerico FIN

    # cambios realizados en esta definicion de calcula_precio en tres_cartera_auto
    def _calcula_precio(self, cr, uid, ids, field_name, arg, context=None):
    
        records = self.browse(cr, uid, ids)
        result = {}
        if not records:
         return result
        else:    
            for r in records:       
                result[r.id] = {
                        'cuota_mes': 0.0,
                        'total_letras':0.0,
                        'monto_financiar':0.0,
                        'total_pagare':0.0,
                        'total_pagare_texto': '',
                        }
        
                #financiamiento es el numero de meses (plazo de pago)
                plazo=int(r.financiamiento)
                
                if plazo == 0:
                    #division para 0, se envia tal como esta
                    return result
               
                if not r.entrada:
                    return result
                
                if r.entrada>r.price:
                    msg = _('La entrada no puede ser igual a 0 o mayor que el valor de compra')
                    raise osv.except_osv(_('Warning !'), msg)               
 
                if not r.interes:
#                        msg = _('Deberia tener un interes Ejemplo: 12%')
#                        raise osv.except_osv(_('Warning !'), msg)
                    return result
                #se calcula el interes por mes
                interes=float(r.interes)/12/100
                monto=r.price
                entrada=r.entrada
                a_financiar=(monto-entrada)
    
                #inicializo las variables
                monto_financiar=0.0 # el monto que se financiara en cuotas
                cuota_mes=0.0 # si existen cuotas, este sera el valor a pagar, incluido interes
                total_letras=0.0 # valor total usado por las cuotas
                total_pagare=0.0 # el monto total financiado entre Adicionales y cuotas
                            
                # caso 1: Cuotas sin Adicionales
                if not r.adicional_ids:
                    
                    # monto_financiar es el monto (a_financiar) mas el interes acumulado
                    monto_financiar = (a_financiar*(1+(interes*plazo)))
                    cuota_mes=float(monto_financiar)/plazo
                    # redondeo del valor de la cuota, para evitar decimales
                    cuota_mes=redondeo(cuota_mes)                
                    total_pagare=cuota_mes*plazo
                    total_letras=total_pagare
                
                # caso 2: Adicionales
                # TODO: Deberia comprobarse si todo el precio se cubre con los adicioanles
                # asi se evita mostrar o generar las cuotas
                else:
                    # sumo los adicionales, con este valor resto del capital a financiar
                    # y genero el valor de las cuotas (de ser necesario)
                    for adicionales in self.browse(cr, uid, ids, context=context):
                        
                        TotalAdicionales = 0.0
                        TotalAdicionalesInteres = 0.0
                        
                        for adicional in adicionales.adicional_ids:
                            TotalAdicionales += adicional.valor
                            TotalAdicionalesInteres += adicional.valor_interes
                            
                    # Calculo los valores con adicionales
                    # se financia por cuotas lo restante entre del valor del auto con la entrada y los adicionales
                    a_financiar=monto-entrada-TotalAdicionales
                    monto_financiar = (a_financiar*(1+(interes*plazo)))
                    cuota_mes=float(monto_financiar)/plazo
                    # redondeo del valor de la cuota, para evitar decimales
                    cuota_mes=redondeo(cuota_mes)                
                    total_letras=cuota_mes*plazo
                    total_pagare=total_letras+TotalAdicionalesInteres
                    
                # genero el resultado para actualizar la vista
                result[r.id]['monto_financiar']=a_financiar
                result[r.id]['cuota_mes']=cuota_mes
                result[r.id]['total_letras']=total_letras
                result[r.id]['total_pagare']=total_pagare
                result[r.id]['total_pagare_texto']= self.NumeroTextoCompleto(total_pagare)
         #   self._estado_mora(cr, uid, ids,field_name, arg,context)    
                return result
        
    def _estado_mora(self,cr,uid,ids,field_name,arg,context):       
        result = {}
        for r in ids:       
            tres_line_obj=self.pool.get('tres.linea.estado.cuenta')
            tres_line=tres_line_obj.search(cr,uid,[('lineaestado_id','=',r),
                                                   ('state','=','espera'),
                                                   ('date_vencimiento','>',time.strftime('%Y-%m-%d'))])   
            if len(tres_line) != 0:
                result[r]=1
            else:
                result[r]=0
        return result
          
    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):

        if not part:
            return {'value': {}}
        pricelist = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_product_pricelist.id
        return {'value': {'pricelist_id': pricelist}}
    
    def onchange_product_id(self, cr, uid, ids, product_id):
        # se realiza on_change para el producto para retornar su precio
        #p_obj=self.pool.get('product.product')

        if product_id:
            product=self.pool.get('product.product.auto').browse(cr, uid, product_id)           
           
            result = {'value': {
                    'price': product.list_price,
                    }
                }

                        
        return result

    
    _columns = {

        # se modifico el nombre del campo name1 a name, debido a problemas y por que es obligatorio tener
        # SIEMPRE el campo name
        'name': fields.char('Codigo', size=64, states={'draft': [('readonly', False)]}, readonly=True, select=True),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        'date_order': fields.datetime('Fecha de pago', select=True,states={'cartera': [('readonly', True)]},readonly=False),
        'date_creacion': fields.datetime('Fecha de Creacion', select=False),
        'user_id': fields.many2one('res.users', 'Connected Salesman', help="Person who uses the the cash register. It could be a reliever, a student or an interim employee."),
        'note': fields.text('Notas para Gerencia'),
        'cedula': fields.char('Cedula', size=14),  
        'partner_id': fields.many2one('res.partner', 'Customer', change_default=True,select=1,readonly=False, states={'cartera':[('readonly',True)]}),
        'garante_id': fields.many2one('res.partner', 'Garante', change_default=True, select=0,readonly=False, states={'cartera': [('readonly', True)]}),
        'cyg_partner_id': fields.many2one('res.partner', 'Conyuge Cliente', change_default=True, select=1, readonly=False, states={'cartera':[('readonly',True)]}),
        'cyg_garante_id': fields.many2one('res.partner', 'Conyuge Garante', change_default=True, select=1, readonly=False, states={'cartera':[('readonly',True)]}),
        'entrada':fields.integer('Entrada',states={'cartera': [('readonly', True)]},readonly=False),
        'product_id': fields.many2one('product.product.auto', 'Product', required=True, states={'cartera':[('readonly',True)]}, domain=[('vendido','=',False)]), 
        #'product_id': fields.many2one('product.product.auto', 'Product'),
        'price': fields.float('Precio',states={'cartera': [('readonly', True)]}),
        'pago_l':fields.float('Pago'),
        'financiamiento':fields.char('Financiamiento (En meses)', size=3,states={'cartera': [('readonly', True)]},readonly=False),         
        'interes':fields.float('Interes Anual',digits=(5,2),states={'cartera': [('readonly', True)]},readonly=False,required=True),
        'cuota_mes': fields.function(_calcula_precio, type="float", digits=(5,2),string="Valor Letra",multi='precio'),
        'monto_financiar': fields.function(_calcula_precio, type="float", digits=(5,2),string="A Financiar",multi='precio'),
        'total_letras': fields.function(_calcula_precio, type="float", digits=(5,2),string="Total Letras",multi='precio'),
        'total_pagare': fields.function(_calcula_precio, type="float", digits=(5,2),string="Total Pagare",multi='precio'),
        'total_pagare_texto': fields.function(_calcula_precio, type="text",string="Total Pagare (Texto)",multi='precio'),
        'sin_garante':fields.boolean('Sin Garante', help='Permite crear una solicitud de credito sin informacion de garantes',readonly=False, states={'cartera':[('readonly',True)]}), 
#        'entrega': fields.boolean('Contrato Entregado', required=True),
        'price_total':fields.float('preciofinal'),
        'state': fields.selection([
            ('draft', 'Borrador'),
            ('confirm', 'Esperando Aprobacion'),
            ('accepted', 'Aprobado'),
            ('refused', 'No Aprobado'),#?
            ('cartera', 'En cartera'),
            ('pagado', 'Pagado'),
            ('renegociar', 'Renegociado'),
            ('pre_embargo', 'Pre-Embargo'),
            ('embargo', 'Embargado'),
            ('cancelada', 'Cancelado')],
            'State', readonly=True),
        'mora': fields.function(_estado_mora, string='Mora',method=True,type='integer',store=True),
        #ICE inicio de bloque a Comentar
        #relacion a trescartera
        'egreso_id': fields.one2many('tres.cartera.egreso', 'tres_cartera_id', 'Egreso'),
        'lineaestado_ids': fields.one2many('tres.linea.estado.cuenta', 'lineaestado_id', 'lineas de estado cuenta',domain=[('state','!=','renegociado')]),
        'cuota_ids': fields.one2many('tres.linea.estado.cuenta.cuota', 'lineaestado_id', 'Cuotas',  domain=[('tipo_haber','=','cuota')]),
        'adicional_ids': fields.one2many('tres.linea.estado.cuenta.adicional', 'lineaestado_id', 'Adicionales',readonly=False, states={'cartera':[('readonly',True)]}, domain=[('tipo_haber','=','adicional')]),
        #ICE Fin de bloque a Comentar
        #documentos
        'copy_predio': fields.boolean('Predio'),
        'copy_rol': fields.boolean('Copia Rol de Pagos'),
        'copy_ruc': fields.boolean('Copia RUC'),
        'copy_ci': fields.boolean('Copia Cedula'),
        'copy_papeleta': fields.boolean('Copia Papeleta'),
        'copy_pago': fields.boolean('Copia pago agua, luz, telefono'),
        
        #CR: campos agregados
        'abono': fields.float('Abono'), 
        'copy_predio_grt': fields.boolean('Predio garante'),
        'copy_rol_grt': fields.boolean('Copia Rol de Pagos garante'),
        'copy_ruc_grt': fields.boolean('Copia RUC garante'),
        'copy_ci_grt': fields.boolean('Copia Cedula garante'),
        'copy_papeleta_grt': fields.boolean('Copia Papeleta garante'),
        'copy_pago_grt': fields.boolean('Copia pago agua, luz, telefono garante'),
        #relacion con cobros
        'cobro_id': fields.many2one('tres.cartera.cobro', 'Cobro'),          
     }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'state': 'draft',
        #cambio el nombre de name a name
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'tres.cartera'),
        #'nb_print': 0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'financiamiento': 3,
        #'mora':_estado_mora,
        'date_creacion': lambda self,cr,uid,context: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_order': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }
       
    
    def confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'confirm',
            'date_confirm': time.strftime('%Y-%m-%d')
        })
        return True
    
    def val_cliente(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'confirm',
            'date_confirm': time.strftime('%Y-%m-%d')
        })
        return True
    
    def accept(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'accepted',
            'date_valid':time.strftime('%Y-%m-%d'),
            'user_valid': uid,
            })
        tresc=self.browse(cr,uid,ids[0])
        obj_product = self.pool.get('product.product.auto')
        obj_product.write(cr, uid, tresc.product_id.id, {'vendido':True,})         
        return True
    
    def action_pago(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        inv_ref = self.pool.get('tres.cartera.cobro')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')
        tres_linea_estado=self.pool.get('tres.linea.estado.cuenta')
        partner_ids = []
        inv_ids = []   
        ids1 = product_obj.search(cr, uid, [('income_pdt', '=', True)], order='id', context=context)
        if not ids1:
            raise osv.except_osv(_('Error'), _('You must have Cash in product.'))
                        
        for order in self.pool.get('tres.cartera').browse(cr, uid, ids, context=context):
            if order.cobro_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                raise osv.except_osv(_('Error'), _('Please provide a partner for the sale.'))
            
            product = product_obj.browse(cr, uid, ids1[0])
            
            acc = product.property_account_income or product.categ_id.property_account_income_categ
            #acc = order.partner_id.property_account_receivable.id
            partner_ids.append(order.partner_id.id)
            inv = {
                'name': "Entrada " + order.name,
                'partner_id': order.partner_id.id,
            }
            if not inv.get('account_id', None):
                inv['account_id'] = acc
       
            if not context:
                context={}

            context['partner_ids'] = partner_ids
            context['interes_mora']= 0.0
            context['fecha']=order.date_order
            inv_id = inv_ref.create(cr, uid, inv, context=context) 
            if not inv_id:
                print hello       
            self.write(cr, uid, [order.id], {'cobro_id': inv_id, 'state': 'cartera'}, context=context)
            inv_ids.append(inv_id)
            #esta funcion sirve para llamar al worflow por lo tanto entra a la funcion que este llamando esta
            wf_service.trg_validate(uid, 'tres.cartera', order.id, 'cartera', cr)
        #    inv_ref.onchange_cliente_interes(cr, uid, [inv_id], order.partner_id.id, 0.3,order.date_order)
        # inv.update({'customer': True})
        id_line_estado = tres_linea_estado.search(cr, uid, [('lineaestado_id', '=', ids),('tipo_haber', '=', 'entrada')])
        #FILTRADO por cliente, estado del haber
        linea_cobro = tres_linea_estado.read(cr, uid, id_line_estado[0])
        
        rs={
                'name': linea_cobro['name'],
                'estado_cuenta_id': linea_cobro['id'],
                'valor_abonado': linea_cobro['abonado'],
                'valor_interes': linea_cobro['valor_interes'],
                'date_vencimiento': linea_cobro['date_vencimiento'],
                'cancelado': False,
                'interes':linea_cobro['interes'],
                'valor_pago': 0.0,#valor_pago,
                'interes_mora': 0.0, 
            }
        #inv_ref.llamar_onchange(cr,uid,inv['partner_id'],context['fecha'],rs)
        if not inv_ids: return {}
        # codigo para ir a otra vista por medio de un boton este siempre debe ser object
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'tres_cartera_autos', 'tres_cartera_cobro_form_view')
        res_id = res and res[1] or False
            
        return {
            'name': _('Cuentas por pagar'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'tres.cartera.cobro',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }
        

    def refused(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'refused'})
        return True
    
    def cartera(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cartera'}, context=context)

    def renegociar(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'renegociar'}, context=context)
    
    def pre_embargo(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'pre_embargo'}, context=context)  
    
    def embargo(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'embargo'}, context=context) 
    
    def cancelada(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancelada'}, context=context) 
    
    def embargo_haberes(self, cr, uid, ids, context=None):
       
#        haber_obj = self.pool.get('tres.linea.estado.cuenta')                        
        obj_solicitud = self.pool.get('tres.linea.estado.cuenta')
 
        lista_ids = obj_solicitud.search(cr, uid, [('lineaestado_id', '=', ids)])
        obj_solicitud.write(cr, uid, lista_ids, {'state':'embargo',})         
        return self.write(cr, uid, ids, {'state':'embargo'}, context=context)
    
    def cancel_contrato(self, cr, uid, ids, context=None):
        res = {
            'state':'cancelada',
            'move_id':False,
        }
        self.write(cr, uid, ids, res)
        tresc=self.browse(cr,uid,ids[0])
        obj_product = self.pool.get('product.product.auto')
        obj_product.write(cr, uid, tresc.product_id.id, {'vendido':False,})
        obj_solicitud = self.pool.get('tres.linea.estado.cuenta')
        lista_ids = obj_solicitud.search(cr, uid, [('lineaestado_id', '=', ids)])
        obj_solicitud.write(cr, uid, lista_ids, {'state':'cancelado',})         
 
        #for()
        return True
    
    def respaldo(self, cr, uid, ids, context=None):      
       
        obj_repo = self.pool.get('tres.cartera.history')
        records = self.browse(cr, uid, ids)
        result = {}
        
        for r in records:

            result = {
                'cuota_mes': r.cuota_mes,
                'company_id': r.company_id.id,
                'product_id': r.product_id.id,
    #            'entrega': r.entrega,
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
                'copy_predio_grt': r.copy_predio_grt,
                'copy_rol_grt': r.copy_rol_grt,
                'copy_ruc_grt': r.copy_ruc_grt,
                'copy_ci_grt': r.copy_ci_grt,
                'copy_papeleta_grt': r.copy_papeleta_grt,
                'copy_pago_grt': r.copy_pago_grt,
                'copy_pago_grt': r.copy_pago_grt,
                'date_history': time.strftime('%Y-%m-%d %H:%M:%S'),                              
                }
            saldo = r.total_pagare-r.abono

            self.write(cr, uid, ids, {'price':saldo}, context=context)
            datos_id = obj_repo.create(cr, uid, result, context)            
            obj_repo1 = self.pool.get('tres.linea.estado.cuenta')            
            lista_ids = obj_repo1.search(cr, uid, [('lineaestado_id', '=', r.id)])                         
            obj_repo1.write(cr, uid, lista_ids, {'state':'renegociado', 'lineaestado_id': datos_id }) 
            
            c=0
            m=0
            
            for h in obj_repo1.browse(cr, uid, lista_ids):
                print "entro for"
                print h.cancelado
                c = c+1
                if h.cancelado == True:
                    m = m + 1
                    print m
                else: 
                    print "no hay datos" 
                
            
#            valor_meses = r.financiamiento
            valor_meses = c-m
                     
            self.write(cr, uid, ids, {'financiamiento':valor_meses}, context=context)               
        return self.write(cr, uid, ids, {'state':'renegociar'}, context=context)
    
    def create_letras(self, cr, uid, ids, context=None):    
            
        cuota_obj = self.pool.get('tres.linea.estado.cuenta')        
        self.cartera(cr, uid, ids, context)
        
        for fy in self.browse(cr, uid, ids, context=context):   
            # Creacion de la linea de Entrada
            fecha_inicial_e = datetime.strptime(fy.date_order, '%Y-%m-%d %H:%M:%S')
            fecha_pago_entrada = fecha_inicial_e
            entrada={ 'tipo_haber': 'entrada',
                     'valor_interes': fy.entrada,
                     'partner_id': fy.partner_id.id,
                     'lineaestado_id':fy.id,
                     'date_vencimiento': fecha_pago_entrada.strftime('%Y-%m-%d'),
                     'name': 'Pago Entrada'}
            cuota_obj.create(cr, uid, entrada )         
            # antes de crear las cuotas verifico si se ha seleccionado el cliente
            if not fy.partner_id:
                msg = _('Debe crear o seleccionar el cliente para poder generar las cuotas respectivas')
                raise osv.except_osv(_('Warning !'), msg) 
    
        #    Falta crear cuotas
            if not fy.cuota_ids or fy.cuota_ids[0].state=='renegociado':
                fecha_inicial = datetime.strptime(fy.date_order, '%Y-%m-%d %H:%M:%S')
                fecha_pago_cuota = fecha_inicial
                
                i=0
    
                while i < int(fy.financiamiento):
            
                    cuota = {
                        # EL name se ocupa como descripcion, el tipo_haber es para identificar el tipo 
                        'tipo_haber': 'cuota',
                        'name': 'Cuota {0} de {1}'.format(i+1, fy.financiamiento),
                        #'name': 'cuota',
                        #'descripcion': 'Cuota {0} de {1}'.format(i+1, fy.financiamiento),
                        'partner_id': fy.partner_id.id,
                        'valor': fy.cuota_mes, 
                        'meses': fy.financiamiento,
                        'interes': fy.interes,
                        'valor_interes': fy.cuota_mes, 
                        'date_vencimiento': fecha_pago_cuota.strftime('%Y-%m-%d'),
                        'lineaestado_id':fy.id
                         } 
            
                    cuota_obj.create(cr, uid, cuota)
                    fecha_pago_cuota = fecha_pago_cuota + relativedelta(months=1)
            
                    i += 1
            
            #caso 2: Ya se han creado las cuotas
            else:
                msg = _('Las letras de pago para esta solicitud ya han sido generadas, no se pueden volver a generar!')
                raise osv.except_osv(_('Warning !'), msg)
        
        
        return True 
        
    def test_paid_letras(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
                if (not order.cuota_ids) or (not order.statement_ids) or \
                    (abs(order.total_pagare-order.amount_paid) > 0.01):
                    return False
        return True
    
    def test_paid(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if not order.adicional_ids:
                if order.cuota_ids and not order.total_pagare:
                    return True
                if (not order.cuota_ids) or (not order.statement_ids) or \
                    (abs(order.total_pagare-order.amount_paid) > 0.01):
                    return False
            else:
                if order.cuota_ids and not order.total_letras:
                    return True
                if (not order.cuota_ids) or (not order.statement_ids) or \
                    (abs(order.total_letras-order.amount_paid) > 0.01) or (abs(order.total_pagare-order.amount_paid) > 0.01):
                    return False
        return True
        
#A.G 12/09/2012 SE CREO FUNCION UNLINK PARA QUE NO SE PUEDAN ELIMINAR LOS CONTRATOS POR ERROR    
    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
                if rec.state not in ('draft','cancelada'):
                    raise osv.except_osv(_('No se puede Eliminar !'), _('En Solicitud de Credito para borrar un contrato, este deberia ser nuevo o estar cancelado.'))
        return super(tres_cartera, self).unlink(cr, uid, ids, context=context)


    
tres_cartera()

#CR: Objeto creado
class tres_cartera_history(osv.osv):
    _name = 'tres.cartera.history'
    _description = 'Historial de cartera de Autos'
    
    _columns = {
        # se modifico el nombre del campo name1 a name, debido a problemas y por que es obligatorio tener
        # SIEMPRE el campo name
        'name': fields.char('Codigo', size=64, states={'draft': [('readonly', False)]}, readonly=True),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        'date_order': fields.datetime('Fecha de pago', select=True),
        'date_creacion': fields.datetime('Fecha de Creacion', select=False),
        'user_id': fields.many2one('res.users', 'Connected Salesman', help="Person who uses the the cash register. It could be a reliever, a student or an interim employee."),
        'note': fields.text('Notas para Gerencia'),
        #'nb_print': fields.integer('Number of Print', readonly=True),
        'cedula': fields.char('Cedula', size=14), 
        'partner_id': fields.many2one('res.partner', 'Customer', change_default=True,select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),
        'garante_id': fields.many2one('res.partner', 'Garante', change_default=True, select=0, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),
        'cyg_partner_id': fields.many2one('res.partner', 'Conyuge Cliente', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),
        'cyg_garante_id': fields.many2one('res.partner', 'Conyuge Garante', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),
        'entrada':fields.integer('Entrada'),
        'product_id': fields.many2one('product.product.auto', 'Product', required=True), 
        #'price':fields.related('list_price', relation='product.product', type='function'),
        'price': fields.float('Precio'),
        'lineaestado_ids': fields.one2many('tres.linea.estado.cuenta', 'lineaestado_id', 'Cuotas Estado',ondelete="restrict"),
#ice
        'cuota_ids': fields.one2many('tres.linea.estado.cuenta.cuota', 'lineaestado_id', 'Cuotas'),
        'pago_l':fields.float('Pago'),
        'financiamiento':fields.char('Financiamiento (En meses)', size=3),         
        'interes':fields.float('Interes Anual',digits=(5,2)),
        'cuota_mes': fields.float('Valor Letra', digits=(5,2)),
        'monto_financiar': fields.float('A Financiar', digits=(5,2)),
        'total_letras': fields.float('Total Letras', digits=(5,2)),
        'total_pagare': fields.float('Total Pagare', digits=(5,2)),
        'total_pagare_texto': fields.text('Total Pagare'),
        
        'sin_garante':fields.boolean('Sin Garante'), 
 #       'entrega': fields.boolean('Contrato Entregado', required=True),
        'price_total':fields.float('Precio Final'),
        'state': fields.selection([
            ('draft', 'Nuevo'),
            ('confirm', 'Esperando Aprobacion'),
            ('accepted', 'Aprobado'),
            ('cancelled', 'Refused'),
            ('cartera', 'En cartera'),
            ('pagado', 'Pagado'),
            ('renegociar', 'Renegociado'),
            ('pre_embargo', 'Pre-embargo'),
            ('embargo', 'Embargado'),
            ('cancelada', 'Cancelado')],
            'State', readonly=True),
        'detalle_historial':fields.char('Descripción de Historial', size=64, readonly=False),
        'date_history':fields.datetime('Fecha de Historial'),
        'history_ids': fields.one2many('tres.linea.estado.cuenta', 'history_id', 'Historial de contratos', domain=[('state','=','renegociado')]),
        #ICE
        'adicional_ids': fields.one2many('tres.linea.estado.cuenta.adicional', 'lineaestado_id', 'Adicionales'),
#        'amount_paid': fields.function(tres_amount_all, digits=(5,2),string='Paid', states={'draft': [('readonly', False)]}, readonly=True,multi='precio1'),
#        'amount_paid_adic': fields.function(tres_amount_all, digits=(5,2),string='Paid', states={'draft': [('readonly', False)]}, readonly=True,multi='precio1'),

        #documentos
        'copy_predio': fields.boolean('Predio'),
        'copy_rol': fields.boolean('Copia Rol de Pagos'),
        'copy_ruc': fields.boolean('Copia RUC'),
        'copy_ci': fields.boolean('Copia Cedula'),
        'copy_papeleta': fields.boolean('Copia Papeleta'),
        'copy_pago': fields.boolean('Copia pago agua, luz, telefono'),
        
#CR: campos agregados
        'abono': fields.float('Abono'), 
        
        'copy_predio_grt': fields.boolean('Predio garante'),
        'copy_rol_grt': fields.boolean('Copia Rol de Pagos garante'),
        'copy_ruc_grt': fields.boolean('Copia RUC garante'),
        'copy_ci_grt': fields.boolean('Copia Cedula garante'),
        'copy_papeleta_grt': fields.boolean('Copia Papeleta garante'),
        'copy_pago_grt': fields.boolean('Copia pago agua, luz, telefono garante'),

      }
    
tres_cartera_history()

class tres_category(osv.osv):
    
    _name = 'tres.category'
    _description = "Tres Category"
    _order = "sequence, name"

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from pos_category where id IN %s',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'parent_id': fields.many2one('tres.category','Parent Category', select=True),
        'child_id': fields.one2many('tres.category', 'parent_id', string='Children Categories'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of product categories."),
    }
tres_category()
