# Sistema Web de Votaciones · Festival de la Leyenda Vallenata 2027

Proyecto académico de **Desarrollo Web** (Fundación Universitaria del Área Andina), Entrega 2:
primera versión funcional del sistema de votaciones construida con **Python, Django (patrón MVT) y MySQL**.

> Los datos que se cargan son **de prueba**. Las categorías se inspiran en los concursos de la edición 58,
> pero los participantes son ficticios y no representan decisiones de la Fundación (RN-09).

## Qué incluye esta entrega

| Requisito | Dónde está |
|---|---|
| Proyecto Django con aplicaciones, rutas, vistas y plantillas | `config/`, `festival/`, `cuentas/`, `templates/` |
| Conexión a MySQL, modelos relacionados y migraciones | `config/settings.py`, `festival/models.py`, `festival/migrations/` |
| Registro, inicio y cierre de sesión | `cuentas/` (usa `django.contrib.auth`) |
| Ediciones, categorías, votaciones y opciones administrables | Django Admin (`festival/admin.py`) |
| Interfaz pública con datos reales de MySQL | `festival/views.py` + `templates/festival/` |
| Datos de prueba | `python manage.py cargar_datos_prueba` |
| Pruebas automáticas (25) | `festival/tests.py`, `cuentas/tests.py` |

### Modelo de datos

```
Edición 1 ── N Categoría 1 ── N Votación 1 ── N Opción
                                   │              │
Usuario 1 ── N Voto N ─────────────┘──────────────┘
```

- `Edicion`: año único, número, lugar, fechas y visibilidad.
- `Categoria`: pertenece a una edición; nombre único dentro de la edición.
- `Votacion`: pertenece a una categoría; estado (borrador, abierta, cerrada), modalidad, periodo de apertura y cierre,
  límite de votos por usuario y publicación de resultados (reglas pendientes de validación).
- `Opcion`: participante u opción de una votación.
- `Voto`: modelo listo para la siguiente entrega (el registro de votos desde la interfaz aún no está habilitado).

Reglas aplicadas: el cierre debe ser posterior a la apertura (validación y restricción `CHECK` en MySQL), no se puede
borrar una edición o categoría con datos asociados (`PROTECT`), y una votación solo se abre con al menos dos opciones
activas (RN-02). Los borradores no se muestran en el sitio público.

## Requisitos

- Python 3.10 o superior
- MySQL 8 (o MariaDB 10.6+)
- En Windows, `mysqlclient` se instala con `pip` sin pasos extra. En Linux necesitas `default-libmysqlclient-dev` y `pkg-config`.

## Instalación y ejecución

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone <URL-del-repositorio>
cd festival_votaciones

# 2. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

# 3. Instalar dependencias
pip install -r requirements.txt
```

4. Crear la base de datos y un usuario en MySQL (desde MySQL Workbench o la consola `mysql -u root -p`):

```sql
CREATE DATABASE festival_votaciones CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'festival'@'localhost' IDENTIFIED BY 'escribe_aqui_tu_clave';
GRANT ALL PRIVILEGES ON festival_votaciones.* TO 'festival'@'localhost';
-- Solo para ejecutar las pruebas automáticas:
GRANT ALL PRIVILEGES ON test_festival_votaciones.* TO 'festival'@'localhost';
FLUSH PRIVILEGES;
```

5. Copiar `.env.example` como `.env` y escribir la clave de MySQL y una `DJANGO_SECRET_KEY` propia.
   El archivo `.env` no se sube al repositorio.

```bash
# 6. Crear las tablas en MySQL
python manage.py migrate

# 7. Cargar datos de prueba (ediciones, categorías, votaciones y opciones)
python manage.py cargar_datos_prueba

# 8. Crear el usuario administrador
python manage.py createsuperuser

# 9. Ejecutar el servidor
python manage.py runserver
```

Abrir <http://127.0.0.1:8000/> para el sitio público y <http://127.0.0.1:8000/admin/> para la administración.

### Pruebas automáticas

```bash
python manage.py test
```

Crea una base de datos temporal `test_festival_votaciones` en MySQL, ejecuta 25 pruebas (modelos, restricciones,
vistas públicas, administración, registro, inicio y cierre de sesión) y la elimina al terminar.

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Inicio con la edición actual, votaciones abiertas y categorías |
| `/ediciones/` y `/ediciones/<año>/` | Ediciones del Festival y sus categorías |
| `/categorias/` y `/categorias/<id>/` | Categorías (filtro `?edicion=AAAA`) y sus votaciones |
| `/votaciones/` y `/votaciones/<id>/` | Votaciones (filtro `?estado=abierta|cerrada`) y su detalle con opciones |
| `/cuentas/registro/`, `/cuentas/ingresar/`, `/cuentas/salir/`, `/cuentas/perfil/` | Autenticación |
| `/admin/` | Django Admin |

## Estructura

```
festival_votaciones/
├── config/            # settings (MySQL, autenticación, idioma), urls raíz
├── festival/          # modelos, admin, vistas públicas, urls, pruebas, comando de datos de prueba
├── cuentas/           # formularios, backend de ingreso con correo, vistas de registro/login/logout
├── templates/         # plantillas (base.html + festival/ + cuentas/)
├── static/            # estilos.css, app.js y Bootstrap 5.3.3 local
├── manage.py
├── requirements.txt
└── .env.example
```

## Pendiente para la siguiente entrega

Registro definitivo de votos, control avanzado de duplicados, reglas de elegibilidad, publicación de resultados,
auditoría avanzada, pruebas de carga y despliegue.

## Equipo

- Brandon Esteban Segura Riveros
- Kelly Dayanna Gonzalez Sarmiento
- Rubian Medina Duran
