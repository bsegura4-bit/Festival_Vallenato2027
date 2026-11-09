"""Registro de votos y reglas de la entrega 3."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from .models import Votacion, Voto


class VotoRechazado(Exception):
    pass


def voto_en_categoria(usuario, categoria):
    """Voto que el usuario ya tiene en esa categoría (o None)."""
    if not usuario.is_authenticated:
        return None
    return (
        Voto.objects.filter(usuario=usuario, categoria=categoria, edicion=categoria.edicion_id)
        .select_related("opcion", "votacion")
        .first()
    )


def validar_opcion(votacion, opcion_id):
    """La opción debe existir, estar activa y pertenecer a esta votación."""
    if not str(opcion_id or "").isdigit():
        raise VotoRechazado("Selecciona una de las opciones de la lista.")
    opcion = votacion.opciones.filter(pk=opcion_id, activa=True).first()
    if opcion is None:
        raise VotoRechazado("La opción enviada no pertenece a esta votación.")
    return opcion


def registrar_voto(usuario, votacion_id, opcion_id):
    if not usuario.is_authenticated:
        raise VotoRechazado("Debes iniciar sesión para votar.")

    try:
        with transaction.atomic():
            # bloquea la fila del usuario: dos envíos al mismo tiempo se atienden en fila
            get_user_model().objects.select_for_update().get(pk=usuario.pk)

            votacion = (
                Votacion.objects.publicas().select_related("categoria__edicion")
                .filter(pk=votacion_id).first()
            )
            if votacion is None:
                raise VotoRechazado("La votación no existe o no está publicada.")
            if not votacion.acepta_votos:
                raise VotoRechazado("Esta votación no está habilitada para recibir votos.")

            opcion = validar_opcion(votacion, opcion_id)

            previo = voto_en_categoria(usuario, votacion.categoria)
            if previo:
                raise VotoRechazado(
                    f"Ya votaste en la categoría {votacion.categoria.nombre} "
                    f"(elegiste {previo.opcion} en «{previo.votacion}»). Solo se permite un voto por categoría."
                )

            return Voto.objects.create(usuario=usuario, opcion=opcion)
    except IntegrityError:
        # la restricción única de MySQL es la última barrera
        raise VotoRechazado("Ya registraste un voto en esta categoría.")
