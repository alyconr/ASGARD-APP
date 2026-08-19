from pathlib import Path

import openpyxl

OUTPUT_PATH = Path(__file__).with_name("sample_canonical_programa.xlsx")


def append_rows(sheet, rows):
    for row in rows:
        sheet.append(row)


wb = openpyxl.Workbook()

ws = wb.active
ws.title = "Programa"
append_rows(
    ws,
    [
        [
            "codigo_programa",
            "nombre_programa",
            "version_programa",
            "vigencia",
            "tipo_programa",
            "titulo_obtendra",
            "duracion_lectiva_horas",
            "duracion_productiva_horas",
            "duracion_total_horas",
            "fuente_archivo",
            "observaciones",
        ],
        [
            "25001",
            "Tecnologia en Desarrollo de Software",
            "01",
            "2026",
            "Tecnico",
            "Tecnico",
            "1400",
            "600",
            "2000",
            "Excel canonico",
            "",
        ],
    ],
)

ws = wb.create_sheet("Competencias")
append_rows(
    ws,
    [
        [
            "competencia_id",
            "codigo_competencia",
            "nombre_competencia",
            "duracion_horas",
            "orden",
            "pagina_origen",
            "observaciones",
        ],
        [
            "COMP-001",
            "DSD001",
            "Desarrollar aplicaciones de software",
            "400",
            "1",
            "1",
            "",
        ],
        ["COMP-002", "DSD002", "Gestionar bases de datos", "300", "2", "1", ""],
        [
            "COMP-003",
            "DSD003",
            "Colaborar en equipos de desarrollo",
            "200",
            "3",
            "1",
            "",
        ],
    ],
)

ws = wb.create_sheet("Resultados")
append_rows(
    ws,
    [
        [
            "competencia_id",
            "rap_id",
            "rap_numero",
            "resultado_aprendizaje",
            "orden",
            "pagina_origen",
            "observaciones",
        ],
        [
            "COMP-001",
            "RAP-001",
            "1",
            "Analiza los requerimientos del software",
            "1",
            "2",
            "",
        ],
        [
            "COMP-001",
            "RAP-002",
            "2",
            "Implementa modulos de software segun estandares",
            "2",
            "2",
            "",
        ],
        ["COMP-001", "RAP-003", "3", "Realiza pruebas de software", "3", "2", ""],
        [
            "COMP-002",
            "RAP-004",
            "1",
            "Disena modelos de bases de datos",
            "1",
            "3",
            "",
        ],
        ["COMP-002", "RAP-005", "2", "Implementa consultas SQL", "2", "3", ""],
        [
            "COMP-003",
            "RAP-006",
            "1",
            "Participa en reuniones de equipo",
            "1",
            "4",
            "",
        ],
    ],
)

ws = wb.create_sheet("Conocimientos")
append_rows(
    ws,
    [
        [
            "competencia_id",
            "rap_id",
            "tipo_conocimiento",
            "elemento_numero",
            "descripcion",
            "orden",
            "pagina_origen",
            "observaciones",
        ],
        [
            "COMP-001",
            "RAP-001",
            "SABER",
            "1",
            "Tecnicas de elicitacion de requerimientos",
            "1",
            "5",
            "",
        ],
        [
            "COMP-001",
            "RAP-002",
            "SABER",
            "2",
            "Patrones de diseno de software",
            "2",
            "5",
            "",
        ],
        [
            "COMP-001",
            "RAP-002",
            "PROCESO",
            "3",
            "Uso de IDEs y herramientas",
            "3",
            "5",
            "",
        ],
        [
            "COMP-002",
            "RAP-004",
            "SABER",
            "1",
            "Modelo Entidad-Relacion",
            "1",
            "6",
            "",
        ],
        ["COMP-002", "RAP-005", "SABER", "2", "Lenguaje SQL", "2", "6", ""],
    ],
)

ws = wb.create_sheet("Criterios")
append_rows(
    ws,
    [
        [
            "competencia_id",
            "rap_id",
            "criterio_numero",
            "descripcion",
            "orden",
            "pagina_origen",
            "observaciones",
        ],
        [
            "COMP-001",
            "RAP-001",
            "1",
            "Identifica y documenta requerimientos",
            "1",
            "7",
            "",
        ],
        [
            "COMP-001",
            "RAP-002",
            "2",
            "Implementa modulos con patrones de diseno",
            "2",
            "7",
            "",
        ],
        [
            "COMP-002",
            "RAP-004",
            "1",
            "Modela bases de datos normalizadas",
            "1",
            "8",
            "",
        ],
        [
            "COMP-002",
            "RAP-005",
            "2",
            "Elabora consultas SQL optimizadas",
            "2",
            "8",
            "",
        ],
    ],
)

wb.save(OUTPUT_PATH)
print("Excel creado correctamente")
