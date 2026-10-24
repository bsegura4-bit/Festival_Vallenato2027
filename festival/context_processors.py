from .models import Edicion


def edicion_actual(request):
    return {"edicion_actual": Edicion.objects.filter(activa=True).first()}
