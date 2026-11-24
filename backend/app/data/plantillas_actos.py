"""Plantillas paramétricas para generar actos reclamados sintéticos.

Cada plantilla está vinculada a una de las 8 categorías de procedencia y
usa marcadores `{var}` que se llenan con valores aleatorios de los pools
abajo. Esto produce textos plausibles del estilo del foro mexicano sin
depender de un LLM externo — determinístico, auditable, y los textos
generados se marcan con `fuente='sintetico_v1'` para nunca entrar al
training del modelo.

Por categoría hay 3-5 plantillas distintas para evitar overfitting al
patrón si el usuario practica muchas veces.
"""

from __future__ import annotations

import random
from typing import Mapping

# ----------------------------------------------------------------------------
# POOLS de variables paramétricas
# ----------------------------------------------------------------------------

JUZGADOS = [
    "Quinto Civil",
    "Tercero de lo Familiar",
    "Décimo Mercantil",
    "Séptimo Penal",
    "Segundo de Distrito en Materia Civil",
    "Octavo de lo Civil",
    "Primero de lo Familiar",
    "Cuarto Mercantil",
]

TIPOS_JUICIO = [
    "ordinario civil",
    "ejecutivo mercantil",
    "ordinario familiar",
    "sumario hipotecario",
    "ejecutivo cambiario",
    "ordinario mercantil",
    "especial hipotecario",
    "oral mercantil",
    "controversia de orden familiar",
]

MONTOS = [
    "$50,000.00",
    "$120,000.00",
    "$250,000.00",
    "$485,000.00",
    "$750,000.00",
    "$1,200,000.00",
    "$2,300,000.00",
    "$4,800,000.00",
]

AUTORIDADES_ADMIN = [
    "el Servicio de Administración Tributaria (SAT)",
    "la Procuraduría Federal del Consumidor",
    "el Instituto Mexicano del Seguro Social",
    "el Ayuntamiento de Monterrey",
    "el Instituto del Fondo Nacional de la Vivienda para los Trabajadores",
    "la Comisión Nacional Bancaria y de Valores",
    "la Secretaría de Movilidad",
]

CIUDADES = ["Monterrey", "Guadalajara", "Ciudad de México", "Mérida", "Puebla", "Querétaro"]

IMPUESTOS = [
    "impuesto sobre la renta",
    "impuesto al valor agregado",
    "impuesto especial sobre producción y servicios",
    "contribuciones a la seguridad social",
]

LICENCIAS = [
    "licencia de funcionamiento comercial",
    "licencia de construcción",
    "permiso de uso de suelo",
    "licencia de conducir",
]

CONCEPTOS_CONDENA = [
    "suerte principal",
    "daño moral",
    "indemnización constitucional",
    "pensión alimenticia atrasada",
    "responsabilidad civil extracontractual",
    "honorarios profesionales",
]

PARTES = [
    "el demandado",
    "la actora",
    "la acreedora alimentaria",
    "el menor representado",
    "los herederos",
    "la cónyuge supérstite",
]

# ----------------------------------------------------------------------------
# PLANTILLAS por categoría
# ----------------------------------------------------------------------------

Plantillas = list[str]
PLANTILLAS: Mapping[str, Plantillas] = {
    "fuera_juicio": [
        "La autoridad {auth_admin} emitió orden de visita domiciliaria al "
        "quejoso por presunta omisión de pago de {impuesto}, fuera de cualquier "
        "procedimiento judicial seguido en forma de juicio.",

        "La autoridad municipal de {ciudad} dictó el acuerdo administrativo "
        "por el cual niega el otorgamiento de la {licencia} solicitada por el "
        "quejoso, sin que medie procedimiento jurisdiccional.",

        "{auth_admin} ordenó la clausura del establecimiento del quejoso "
        "ubicado en {ciudad}, sin previa audiencia ni procedimiento contencioso.",

        "El acto reclamado consiste en la resolución administrativa emitida por "
        "{auth_admin} que impone al quejoso una sanción económica de {monto}, "
        "fuera del marco de un juicio.",
    ],

    "en_juicio_imposible": [
        "El Juez {juzgado} decretó embargo precautorio sobre las cuentas "
        "bancarias del quejoso por la cantidad de {monto} para garantizar la "
        "reclamación deducida en el juicio {tipo_juicio}.",

        "En el procedimiento {tipo_juicio}, el Juez {juzgado} ordenó alimentos "
        "provisionales por {monto} mensuales en favor de {parte}, afectando "
        "materialmente el patrimonio del quejoso.",

        "El Juez {juzgado} impuso al quejoso multa procesal de {monto} por "
        "supuesto desacato a sus determinaciones durante el juicio {tipo_juicio}.",

        "El Juez {juzgado} decretó orden de arresto por treinta y seis horas en "
        "contra del quejoso por incumplir el requerimiento de comparecencia "
        "dentro del juicio {tipo_juicio}.",

        "El Juez {juzgado} dictó el auto que ordena el aseguramiento de bienes "
        "muebles del quejoso por valor aproximado de {monto} en el juicio "
        "{tipo_juicio}.",
    ],

    "en_juicio_diferida": [
        "El Juez {juzgado} desechó la prueba pericial ofrecida por el quejoso "
        "en el juicio {tipo_juicio}, al considerarla extemporánea.",

        "Durante el juicio {tipo_juicio} seguido ante el Juez {juzgado}, se "
        "tuvo por contestada la demanda en términos no acordes con la "
        "petición planteada por el quejoso.",

        "El Juez {juzgado} admitió las pruebas ofrecidas por la contraparte "
        "en el juicio {tipo_juicio} sin notificar al quejoso para impugnarlas "
        "oportunamente.",

        "En el juicio {tipo_juicio}, el Juez resolvió la cuestión de "
        "personalidad reconociéndole legitimación a quien comparece como "
        "apoderado de la contraparte.",
    ],

    "post_juicio_general": [
        "Concluido el juicio {tipo_juicio}, el Juez {juzgado} emitió el "
        "acuerdo declarando la caducidad de la instancia respecto del quejoso.",

        "Tras finalizar el procedimiento {tipo_juicio}, la autoridad ordenó "
        "el envío del expediente al archivo general sin haber resuelto la "
        "incidencia de costas planteada.",

        "El Juez {juzgado}, después de concluido el juicio {tipo_juicio} y "
        "no estando en fase de ejecución, dictó acuerdo respecto al "
        "desistimiento parcial planteado.",
    ],

    "post_juicio_ejecucion": [
        "El Juez {juzgado} dictó la última resolución que aprueba el "
        "cumplimiento total de la sentencia firme y ordena el archivo "
        "definitivo del expediente del juicio {tipo_juicio}.",

        "En el procedimiento de remate seguido en autos del juicio "
        "{tipo_juicio}, el Juez {juzgado} dictó la resolución que ordena el "
        "otorgamiento de la escritura de adjudicación y la entrega del "
        "inmueble rematado al postor.",

        "La autoridad ejecutora dictó la declaratoria de imposibilidad "
        "material para dar cumplimiento a la sentencia condenatoria firme, "
        "ordenando el archivo definitivo del asunto.",

        "El Juez {juzgado} emitió la resolución final de la ejecución que "
        "reconoce el cumplimiento total de lo sentenciado y libera al "
        "ejecutado de toda obligación derivada del juicio {tipo_juicio}.",
    ],

    "post_juicio_prematuro": [
        "Durante el procedimiento de ejecución de sentencia del juicio "
        "{tipo_juicio}, el Juez {juzgado} designó perito valuador para tasar "
        "los bienes embargados, sin que se haya emitido la última resolución "
        "del procedimiento.",

        "En el procedimiento de remate del juicio {tipo_juicio}, el Juez "
        "{juzgado} ordenó la publicación de edictos para convocar postores; "
        "se trata de un acto intermedio anterior a la resolución que ordena "
        "la escritura de adjudicación.",

        "El Juez {juzgado} emitió acuerdo de fijación de fecha para la "
        "audiencia de remate del bien inmueble embargado, acto procesal "
        "previo a la última resolución del procedimiento ejecutivo.",

        "En la fase de ejecución del juicio {tipo_juicio}, el Juez ordenó "
        "el desahogo de prueba pericial sobre el avalúo de bienes, sin que "
        "haya concluido el procedimiento de ejecución con resolución firme.",
    ],

    "tercero_extrano": [
        "El quejoso, propietario del inmueble embargado, no fue parte ni "
        "fue emplazado al juicio {tipo_juicio} seguido entre tercero "
        "demandante y tercero demandado, y resiente afectación material por "
        "el embargo trabado sobre su propiedad de valor estimado en {monto}.",

        "Persona ajena al juicio {tipo_juicio} que se ostenta como "
        "propietaria de los bienes muebles embargados, sin haber sido "
        "emplazada al procedimiento ni notificada de actuación alguna.",

        "El acto reclamado consiste en la afectación material que sufre el "
        "quejoso, ajeno al juicio {tipo_juicio}, por la orden de "
        "desocupación del inmueble que ocupa en calidad de poseedor de "
        "buena fe.",

        "El quejoso, sin haber sido emplazado al juicio {tipo_juicio} "
        "tramitado ante el Juez {juzgado}, recibió notificación del lanzamiento "
        "del inmueble del que es propietario.",
    ],

    "sentencia_definitiva": [
        "La sentencia definitiva del juicio {tipo_juicio} condena al "
        "quejoso al pago de {monto} por concepto de {concepto}, así como al "
        "pago de intereses moratorios y costas judiciales del juicio.",

        "El laudo dictado en el procedimiento laboral declaró improcedente "
        "la acción de despido injustificado planteada por el quejoso y lo "
        "condena al pago de costas.",

        "La resolución que pone fin al juicio {tipo_juicio} declaró "
        "fundada la acción cambiaria directa intentada por la contraparte "
        "contra el quejoso, condenándolo al pago de {monto}.",

        "Mediante sentencia definitiva del Juez {juzgado}, se decretó "
        "el divorcio entre las partes y se resolvió sobre la guarda y "
        "custodia del menor en favor de {parte}.",

        "La sentencia definitiva dictada en el juicio {tipo_juicio} "
        "absolvió a la parte demandada y condenó al quejoso al pago de "
        "costas en ambas instancias.",
    ],
}


# ----------------------------------------------------------------------------
# Generador
# ----------------------------------------------------------------------------

def generar_acto(categoria: str, rng: random.Random | None = None) -> str:
    """Genera un acto reclamado sintético plausible para la categoría dada.

    Reemplaza los marcadores `{var}` con valores aleatorios de los pools.
    Si la categoría no tiene plantillas, lanza KeyError.
    """
    rng = rng or random.Random()
    plantillas = PLANTILLAS[categoria]
    plantilla = rng.choice(plantillas)
    return plantilla.format(
        juzgado=rng.choice(JUZGADOS),
        tipo_juicio=rng.choice(TIPOS_JUICIO),
        monto=rng.choice(MONTOS),
        auth_admin=rng.choice(AUTORIDADES_ADMIN),
        ciudad=rng.choice(CIUDADES),
        impuesto=rng.choice(IMPUESTOS),
        licencia=rng.choice(LICENCIAS),
        concepto=rng.choice(CONCEPTOS_CONDENA),
        parte=rng.choice(PARTES),
    )


CATEGORIAS_DISPONIBLES = list(PLANTILLAS.keys())
