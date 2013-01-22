{
    "name" : "AUTOPOLO",
    "author" : "TRESCloud Cia. Ltda.",
    "maintainer": 'TRESCloud Cia. Ltda.',
    "website": 'http://www.trescloud.com',
    "description": """Sistema de gestion y control de CARTERA DE AUTOS
    
    Este sistema permite controlar la venta de autos usados a credito,
    calcular interes en caso de mora de mas de 3 meses, registrar pagos
    a travez de caja, recibos bancarios, sin necesiadad de utilizar el 
    sistema contable
      
    Desarrolladores:
    
    Andrea Garcia
    Ruth Hidalgo
    David Romero
    Patricio Rangles
    
    """,
    "version" : "1.0",
    "depends" : ["base","crm","sale","point_of_sale","account_accountant","hr","jasper_reports"],
    "init_xml" : [],
    "update_xml" : [
                #"security/ir.model.access.csv",
                "security/tres_cartera_autos_security.xml",
                "security/ir.model.access.csv",
                "report/report_tres_cartera_autos_imprimir.xml",
                "wizard/tres_pagar_cuota.xml",
                "wizard/tres_receipt_view.xml",
                "wizard/tres_renegociado_view.xml",          
                "tres_cartera_autos_view.xml",
                "tres_cartera_cobro_view.xml",
                "tres_cartera_egreso_view.xml",
                "tres_cartera_board.xml",
                "tres_cartera_autos_sequence.xml",
                "tres_cartera_autos_workflow.xml",
                "tres_cliente_cartera_autos_view.xml",
                "tres_productos_cartera_autos_view.xml",
                "company_view.xml",
                #"report_tres_cartera_autos_contrato.xml",
    ],
    "category" : "TRESCloud",
    "active": False,
    "installable": True
}

