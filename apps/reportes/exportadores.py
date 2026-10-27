"""Exportación del reporte de progreso a Excel (openpyxl) y PDF (ReportLab)."""
from io import BytesIO
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL_MARINO = "1A365D"
AZUL = "1E5BB8"
GRIS_FILA = "F3F6FA"

# ---------------------------------------------------------------- Excel
_FUENTE = Font(name="Arial", size=10)
_FUENTE_ENCABEZADO = Font(name="Arial", size=10, bold=True, color="FFFFFF")
_RELLENO_ENCABEZADO = PatternFill("solid", fgColor=AZUL_MARINO)
_RELLENO_ZEBRA = PatternFill("solid", fgColor=GRIS_FILA)
_BORDE = Border(bottom=Side(style="thin", color="DCE4EF"))


def _tabla(hoja, fila_inicio: int, encabezados: list[str], filas: list[list], anchos: list[int]) -> int:
    """Escribe una tabla con estilo y devuelve la última fila usada."""
    for col, texto in enumerate(encabezados, start=1):
        celda = hoja.cell(row=fila_inicio, column=col, value=texto)
        celda.font, celda.fill = _FUENTE_ENCABEZADO, _RELLENO_ENCABEZADO
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, valores in enumerate(filas, start=1):
        for col, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila_inicio + i, column=col, value=valor)
            celda.font, celda.border = _FUENTE, _BORDE
            if i % 2 == 0:
                celda.fill = _RELLENO_ZEBRA
    for col, ancho in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(col)].width = ancho
    return fila_inicio + len(filas)


def _formato_columna(hoja, letra: str, desde: int, hasta: int, formato: str) -> None:
    for fila in range(desde, hasta + 1):
        hoja[f"{letra}{fila}"].number_format = formato


def generar_excel(reporte: dict) -> bytes:
    libro = Workbook()
    filtros, resumen = reporte["filtros"], reporte["resumen"]

    # Hoja 1: resumen
    hoja = libro.active
    hoja.title = "Resumen"
    hoja["A1"] = "Net Bean · Reporte de progreso"
    hoja["A1"].font = Font(name="Arial", size=14, bold=True, color=AZUL_MARINO)
    hoja["A2"] = filtros.descripcion
    hoja["A3"] = f"Generado el {reporte['generado']:%d/%m/%Y %H:%M}"
    for celda in ("A2", "A3"):
        hoja[celda].font = Font(name="Arial", size=10, color="5B6B82")
    indicadores = [
        ["Estudiantes registrados", resumen["estudiantes_registrados"]],
        ["Estudiantes activos en el periodo", resumen["estudiantes_activos"]],
        ["Intentos de práctica", resumen["intentos"]],
        ["Aciertos", resumen["aciertos"]],
        ["Tasa de acierto", "=IF(B8=0,0,B9/B8)"],
        ["XP otorgado", resumen["xp_otorgado"]],
        ["Señas dominadas (acumulado)", resumen["senas_dominadas"]],
        ["Lecciones completadas en el periodo", resumen["lecciones_completadas"]],
    ]
    _tabla(hoja, 5, ["Indicador", "Valor"], indicadores, [38, 16])
    hoja["B10"].number_format = "0.0%"
    hoja["A15"] = "La tasa de acierto se calcula como aciertos / intentos. Un acierto es una práctica con la letra correcta y el porcentaje mínimo de la seña."
    hoja["A15"].font = Font(name="Arial", size=9, italic=True, color="5B6B82")

    # Hoja 2: por día, con gráfico de líneas
    dias = libro.create_sheet("Por día")
    filas = [[f["dia"], f["intentos"], f["aciertos"], f"=IF(B{i}=0,0,C{i}/B{i})"]
             for i, f in enumerate(reporte["por_dia"], start=2)]
    ultima = _tabla(dias, 1, ["Fecha", "Intentos", "Aciertos", "Tasa de acierto"], filas, [14, 12, 12, 16])
    _formato_columna(dias, "A", 2, ultima, "DD/MM/YYYY")
    _formato_columna(dias, "D", 2, ultima, "0.0%")
    dias.freeze_panes = "A2"
    if filas:
        grafico = LineChart()
        grafico.title, grafico.y_axis.title, grafico.height, grafico.width = "Prácticas por día", "Cantidad", 8, 18
        grafico.add_data(Reference(dias, min_col=2, max_col=3, min_row=1, max_row=ultima), titles_from_data=True)
        grafico.set_categories(Reference(dias, min_col=1, min_row=2, max_row=ultima))
        dias.add_chart(grafico, "F2")

    # Hoja 3: por seña, con gráfico de barras
    senas = libro.create_sheet("Por seña")
    filas = [[f["sena"], f["modulo"], f["intentos"], f["aciertos"], f"=IF(C{i}=0,0,D{i}/C{i})",
              f["puntaje_promedio"] / 100, f["estudiantes"]]
             for i, f in enumerate(reporte["por_sena"], start=2)]
    ultima = _tabla(senas, 1, ["Seña", "Módulo", "Intentos", "Aciertos", "Tasa de acierto",
                               "Puntaje promedio", "Estudiantes"], filas, [10, 22, 11, 11, 15, 16, 12])
    _formato_columna(senas, "E", 2, ultima, "0.0%")
    _formato_columna(senas, "F", 2, ultima, "0.0%")
    senas.freeze_panes, senas.auto_filter.ref = "A2", f"A1:G{max(ultima, 1)}"
    if filas:
        barras = BarChart()
        barras.type, barras.title, barras.height, barras.width = "bar", "Tasa de acierto por seña", 10, 18
        barras.add_data(Reference(senas, min_col=5, min_row=1, max_row=min(ultima, 16)), titles_from_data=True)
        barras.set_categories(Reference(senas, min_col=1, min_row=2, max_row=min(ultima, 16)))
        barras.y_axis.number_format, barras.legend = "0%", None
        senas.add_chart(barras, "I2")

    # Hoja 4: por estudiante
    est = libro.create_sheet("Por estudiante")
    filas = [[f["nombre"], f["correo"], f["intentos"], f["aciertos"], f"=IF(C{i}=0,0,D{i}/C{i})",
              f["xp_periodo"], f["xp_total"], f["racha"], f["dominadas"],
              f["ultima"].replace(tzinfo=None) if f["ultima"] else None]
             for i, f in enumerate(reporte["por_estudiante"], start=2)]
    ultima = _tabla(est, 1, ["Estudiante", "Correo", "Intentos", "Aciertos", "Tasa de acierto", "XP del periodo",
                             "XP total", "Racha (días)", "Señas dominadas", "Última práctica"],
                    filas, [26, 30, 10, 10, 15, 14, 10, 12, 15, 18])
    _formato_columna(est, "E", 2, ultima, "0.0%")
    _formato_columna(est, "J", 2, ultima, "DD/MM/YYYY HH:MM")
    est.freeze_panes, est.auto_filter.ref = "A2", f"A1:J{max(ultima, 1)}"

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# ---------------------------------------------------------------- PDF
def _estilo_tabla() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{AZUL_MARINO}")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(f"#{GRIS_FILA}")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DCE4EF")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def _grafico_senas(senas: list[dict]) -> Drawing:
    alto = 22 * len(senas) + 40
    dibujo = Drawing(16 * cm, alto)
    grafico = HorizontalBarChart()
    grafico.x, grafico.y, grafico.width, grafico.height = 50, 20, 14 * cm - 50, alto - 35
    ordenadas = list(reversed(senas))  # la de menor acierto queda arriba
    grafico.data = [[f["tasa"] for f in ordenadas]]
    grafico.categoryAxis.categoryNames = [f["sena"] for f in ordenadas]
    grafico.categoryAxis.labels.fontName = "Helvetica-Bold"
    grafico.valueAxis.valueMin, grafico.valueAxis.valueMax, grafico.valueAxis.valueStep = 0, 100, 20
    grafico.valueAxis.labelTextFormat = "%d %%"
    grafico.valueAxis.labels.fontName = "Helvetica"
    grafico.valueAxis.labels.fontSize = 7
    grafico.barLabels.fontName = "Helvetica"
    grafico.bars[0].fillColor = colors.HexColor(f"#{AZUL}")
    grafico.barLabelFormat, grafico.barLabels.nudge = "%.1f %%", 14
    grafico.barLabels.fontSize = 7
    dibujo.add(grafico)
    return dibujo


def _pie_de_pagina(lienzo, documento) -> None:
    lienzo.saveState()
    lienzo.setFont("Helvetica", 8)
    lienzo.setFillColor(colors.HexColor("#5B6B82"))
    lienzo.drawCentredString(A4[0] / 2, 1.2 * cm, f"Net Bean · Reporte de progreso · Página {documento.page}")
    lienzo.restoreState()


def generar_pdf(reporte: dict) -> bytes:
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                                  topMargin=1.6 * cm, bottomMargin=2 * cm, title="Reporte de progreso Net Bean",
                                  author="Net Bean")
    base = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18,
                            textColor=colors.HexColor(f"#{AZUL_MARINO}"), spaceAfter=4)
    subtitulo = ParagraphStyle("sub", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#5B6B82"),
                               alignment=TA_CENTER, spaceAfter=12)
    seccion = ParagraphStyle("sec", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12,
                             textColor=colors.HexColor(f"#{AZUL_MARINO}"), spaceBefore=10, spaceAfter=6)
    nota = ParagraphStyle("nota", parent=base["Normal"], fontSize=8.5, textColor=colors.HexColor("#5B6B82"))
    resumen, filtros = reporte["resumen"], reporte["filtros"]

    historia = [
        Paragraph("Reporte de progreso", titulo),
        Paragraph(f"{escape(filtros.descripcion)} · Generado el {reporte['generado']:%d/%m/%Y %H:%M}", subtitulo),
        Paragraph("Indicadores del periodo", seccion),
    ]
    indicadores = [
        ["Estudiantes activos", "Intentos", "Tasa de acierto", "XP otorgado"],
        [f"{resumen['estudiantes_activos']} de {resumen['estudiantes_registrados']}", resumen["intentos"],
         f"{resumen['tasa_acierto']} %", resumen["xp_otorgado"]],
        ["Aciertos", "Señas dominadas", "Lecciones completadas", ""],
        [resumen["aciertos"], resumen["senas_dominadas"], resumen["lecciones_completadas"], ""],
    ]
    tabla = Table(indicadores, colWidths=[4.35 * cm] * 4)
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 8), ("FONTSIZE", (0, 2), (-1, 2), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5B6B82")),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#5B6B82")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 15),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"), ("FONTSIZE", (0, 3), (-1, 3), 15),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE4EF")),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10), ("BOTTOMPADDING", (0, 3), (-1, 3), 8),
    ]))
    historia.append(tabla)

    historia.append(Paragraph("Señas que necesitan refuerzo", seccion))
    senas = reporte["por_sena"]
    if senas:
        historia.append(_grafico_senas(senas[:10]))
        filas = [["Seña", "Módulo", "Intentos", "Aciertos", "Acierto", "Puntaje prom.", "Estudiantes"]] + [
            [f["sena"], escape(f["modulo"]), f["intentos"], f["aciertos"], f"{f['tasa']} %",
             f"{f['puntaje_promedio']} %", f["estudiantes"]] for f in senas[:15]]
        tabla = Table(filas, colWidths=[1.6 * cm, 4.2 * cm, 1.8 * cm, 1.8 * cm, 2 * cm, 2.4 * cm, 2 * cm], repeatRows=1)
        tabla.setStyle(_estilo_tabla())
        historia += [Spacer(1, 6), tabla]
    else:
        historia.append(Paragraph("No hay prácticas en el periodo seleccionado.", nota))

    historia.append(Paragraph("Estudiantes", seccion))
    estudiantes = reporte["por_estudiante"]
    if estudiantes:
        filas = [["Estudiante", "Intentos", "Acierto", "XP periodo", "XP total", "Racha", "Dominadas"]] + [
            [Paragraph(escape(f["nombre"]), nota), f["intentos"], f"{f['tasa']} %", f["xp_periodo"],
             f["xp_total"], f["racha"], f["dominadas"]] for f in estudiantes[:30]]
        tabla = Table(filas, colWidths=[5 * cm, 1.8 * cm, 1.9 * cm, 2 * cm, 1.9 * cm, 1.6 * cm, 1.8 * cm], repeatRows=1)
        tabla.setStyle(_estilo_tabla())
        historia.append(tabla)
    else:
        historia.append(Paragraph("Ningún estudiante practicó en el periodo seleccionado.", nota))

    historia += [Spacer(1, 10), Paragraph(
        "Acierto: práctica con la letra correcta y al menos el porcentaje mínimo de la seña. "
        "Las señas aparecen de menor a mayor acierto para priorizar qué reforzar.", nota)]
    documento.build(historia, onFirstPage=_pie_de_pagina, onLaterPages=_pie_de_pagina)
    return salida.getvalue()
