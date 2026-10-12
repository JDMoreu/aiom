# -*- coding: utf-8 -*-
"""Genera pqr.txt y pqr.pdf (2 paginas) para la demo de AIOM.

Un solo origen de datos: la lista EST. De ahi salen el .txt (texto plano) y el .pdf
(reportlab). Asi el texto extraido del PDF y el .txt no pueden divergir.

Se escribe a un temporal con nombre unico y luego os.replace, porque en esta maquina el
terminal lanza cada comando dos veces y dos escrituras al mismo fichero chocan.
"""
import os
import time

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, HRFlowable)

AQUI = os.path.dirname(os.path.abspath(__file__))
RADICADO = "PQR-2026-0048217"

# (estilo, texto). Estilos: titulo, sub, h, p, firma
EST = [
    ("titulo", "TELECOMUNICACIONES DEL NORTE S.A. E.S.P."),
    ("sub", "Oficina de Atención al Usuario - Sede Principal, Barranquilla"),
    ("sub", "NIT: 900.123.456-7   |   Linea de atencion: 01 8000 555 010"),

    ("h", "PQR - Peticion, Queja o Reclamo"),
    ("p", "Radicado: " + RADICADO),
    ("p", "Fecha de radicacion: 9 de marzo de 2026"),
    ("p", "Canal: Presencial - Oficina de Atencion al Usuario, Barranquilla"),

    ("h", "DATOS DEL PETICIONARIO"),
    ("p", "Nombre completo: Julian Andres Villalba Ospina"),
    ("p", "Cedula de ciudadania: 1.098.765.432"),
    ("p", "Direccion: Calle 54 # 12-34, Barrio Alto Prado, Barranquilla"),
    ("p", "Telefono: 300 555 0147"),
    ("p", "Correo electronico: julian.villalba@correo-ficticio.com"),
    ("p", "Contrato No.: 4-2019-778541"),
    ("p", "Plan contratado: Internet Hogar 300 Mbps + Telefonia Movil 40 GB"),

    ("h", "HECHOS"),
    ("p", "1. El 2 de febrero de 2026, a las 6:40 p. m., el servicio de internet de mi hogar dejo de funcionar por completo. Desde esa fecha el servicio presenta fallas intermitentes: se cae varias veces al dia y en varias jornadas quedo sin servicio durante horas."),
    ("p", "2. El 5 de febrero de 2026 llame a la linea de soporte y me asignaron el radicado de llamada 90045112. El asesor me pidio reiniciar el modem, lo hice, y el problema continuo."),
    ("p", "3. El 11 de febrero de 2026 llame de nuevo (radicado 90058837) y me programaron una visita tecnica para el 15 de febrero de 2026. El tecnico NO acudio a la cita y nadie me aviso de la cancelacion."),
    ("p", "4. El 18 de febrero de 2026 llame una tercera vez (radicado 90067420) para reportar la visita fallida. Ese mismo dia, sin que yo lo solicitara, la empresa registro un cobro por 'reconexion de linea' de $98.700 y el servicio seguia sin funcionar de forma estable."),
    ("p", "5. El 24 de febrero de 2026 llame una cuarta vez (radicado 90075503) y me informaron que 'el caso estaba en revision'."),
    ("p", "6. El 2 de marzo de 2026 llame una quinta vez (radicado 90084210) y me dijeron que el descuento por los dias sin servicio quedaba 'pendiente de aprobacion'."),
    ("p", "7. El 6 de marzo de 2026 llame una sexta vez (radicado 90091874) y no obtuve una solucion concreta. En total he realizado 6 llamadas al soporte sin que la falla se haya resuelto."),
    ("p", "8. El 28 de febrero de 2026 la empresa expidio la factura FE-2026-02-4471 por valor de $288.600. Esa factura incluye el valor del plan mensual ($189.900) y un cobro de $98.700 por 'reconexion de linea' que NUNCA solicite ni autorice. Ademas, se cobro el periodo completo pese a que estuve 17 dias sin servicio, del 2 al 18 de febrero de 2026."),
    ("p", "9. La falla del servicio no se ha corregido. A la fecha de esta PQR, 9 de marzo de 2026, el servicio continua presentando cortes intermitentes."),
    ("p", "10. El motivo principal de esta PQR es el cobro indebido de $98.700 por reconexion de linea, sin perjuicio de la queja por la falla reiterada del servicio y la atencion deficiente."),

    ("h", "PETICIONES"),
    ("p", "1. La devolucion del cobro indebido por 'reconexion de linea' por valor de $98.700, que nunca solicite ni autorice."),
    ("p", "2. El descuento proporcional por los 17 dias sin servicio, del 2 al 18 de febrero de 2026, equivalente a $107.610."),
    ("p", "3. La reparacion definitiva de la falla del servicio de internet, que a la fecha continua."),
    ("p", "4. Una respuesta de fondo a esta PQR dentro de los terminos legales."),
    ("p", "En total, el valor que reclamo es de $206.310: los $98.700 de la reconexion indebida mas los $107.610 del descuento por los dias sin servicio."),
    ("p", "El peticionario NO solicita la cancelacion del contrato: desea conservar el servicio una vez reparado."),

    ("firma", "Firma del peticionario:"),
    ("firma", ""),
    ("firma", "_______________________________"),
    ("firma", "Julian Andres Villalba Ospina"),
    ("firma", "C.C. 1.098.765.432"),
]


def texto_plano():
    partes = []
    for est, txt in EST:
        if est == "h":
            partes.append(txt)
        elif est in ("titulo", "sub"):
            partes.append(txt)
        elif est == "firma":
            if txt:
                partes.append(txt)
        else:
            partes.append(txt)
    return "\n\n".join(partes).strip() + "\n"


def estilos():
    return {
        "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=13.5,
                                 leading=16, alignment=TA_CENTER, spaceAfter=1),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=8.7, leading=11,
                              alignment=TA_CENTER, textColor="#333333"),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5, leading=13,
                            spaceBefore=9, spaceAfter=3),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.3, leading=11.8,
                            alignment=TA_JUSTIFY, spaceAfter=2.5),
        "firma": ParagraphStyle("firma", fontName="Helvetica", fontSize=9.3, leading=12,
                                spaceAfter=1),
    }


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor("#555555")
    canvas.drawCentredString(A4[0] / 2.0, 1.15 * cm,
                             "%s   -   Pagina %d de 2" % (RADICADO, doc.page))
    canvas.setStrokeColor("#999999")
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.55 * cm, A4[0] - 2 * cm, 1.55 * cm)
    canvas.restoreState()


def generar_pdf(ruta):
    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.6 * cm, bottomMargin=2.1 * cm,
                            title="PQR " + RADICADO, author="AIOM demo")
    E = estilos()
    fl = []
    for i, (est, txt) in enumerate(EST):
        if est == "titulo":
            fl.append(Paragraph(txt, E["titulo"]))
            fl.append(HRFlowable(width="100%", thickness=1.1, color="#1a3d6d",
                                 spaceBefore=3, spaceAfter=5))
        elif est == "h":
            fl.append(Paragraph(txt, E["h"]))
        else:
            fl.append(Paragraph(txt if txt else "&nbsp;", E[est]))
    doc.build(fl, onFirstPage=pie, onLaterPages=pie)


def escribir(ruta, texto, binario=None):
    tmp = "%s.tmp%d" % (ruta, os.getpid())
    if binario is None:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
    else:
        with open(tmp, "wb") as f:
            f.write(binario)
    for _ in range(40):
        try:
            os.replace(tmp, ruta)
            return
        except OSError:
            time.sleep(0.15)
    os.replace(tmp, ruta)


def main():
    txt = texto_plano()
    escribir(os.path.join(AQUI, "pqr.txt"), txt)

    pdf_tmp = os.path.join(AQUI, "pqr.pdf.tmp%d" % os.getpid())
    generar_pdf(pdf_tmp)
    with open(pdf_tmp, "rb") as f:
        datos = f.read()
    os.remove(pdf_tmp)
    escribir(os.path.join(AQUI, "pqr.pdf"), None, binario=datos)

    print("pqr.txt:", len(txt), "caracteres")
    print("pqr.pdf:", len(datos), "bytes")


if __name__ == "__main__":
    main()
