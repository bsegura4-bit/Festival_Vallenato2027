# Sistema Web de Votaciones · Festival de la Leyenda Vallenata 2027

Proyecto académico de **Desarrollo Web** (Fundación Universitaria del Área Andina), **Entrega 3**:
módulo de votaciones, validaciones y API GET, construido con **Python, Django 5.2 (patrón MVT) y MySQL 8**.
Continúa el proyecto de la Entrega 2 (ediciones, categorías, votaciones, opciones y cuentas de usuario).

> Los datos que se cargan son **de prueba**. Las categorías se inspiran en los concursos del Festival,
> pero los participantes y usuarios son ficticios y no representan decisiones de la Fundación (RN-09).

**Regla central:** cada usuario puede elegir una sola opción por categoría y edición. Puede votar en otras
categorías, pero no emitir un segundo voto en la misma categoría, aunque esta tenga varios subeventos (votaciones).

## Qué incluye la Entrega 3

| Funcionalidad | Dónde está |
|---|---|
| Modelo `Voto` vinculado a usuario, edición, categoría, votación y opción | `festival/models.py` (clase `Voto`) |
| Migración que agrega edición/categoría al voto y la restricción única | `festival/migrations/0002_voto_categoria_edicion_unico.py` |
| **Control de unicidad** (Django + restricción `UNIQUE` en MySQL + bloqueo de concurrencia) | `festival/votos.py` (`registrar_voto`) y `Voto.Meta.constraints` |
| Votar: seleccionar opción → confirmar → validar → guardar (POST con CSRF) | `festival/views.py` (`votar`), `templates/festival/votacion_detalle.html`, `confirmar_voto.html` |
| Categorías votadas por el usuario y pendientes | `/mis-votos/` → `festival/views.py` (`mis_votos`) |
| Consulta administrativa de votos | `/admin/festival/voto/` (solo lectura) y `/reporte-votos/` (conteo por opción) |
| **API GET** de categorías y opciones en JSON | `/api/categorias/` → `festival/views.py` (`api_categorias`) |
| Prueba de solicitudes simultáneas | `python manage.py probar_concurrencia --usuario votante2` |
| Pruebas automáticas CP-01 a CP-10 | `festival/tests_votos.py` |

### Validaciones del voto (en el servidor)

1. El usuario debe haber iniciado sesión (`@login_required`); el formulario usa POST y token CSRF.
2. La votación debe estar publicada, en estado **abierta** y dentro de su periodo de apertura y cierre.
3. La opción debe existir, estar activa y pertenecer a esa votación (se rechaza una opción de otra categoría).
4. El usuario no debe tener un voto previo en la misma categoría y edición.
5. Concurrencia: la operación corre en una transacción que bloquea la fila del usuario (`select_for_update`),
   y si aun así llegan dos inserciones, la restricción `voto_unico_usuario_categoria_edicion` de MySQL rechaza la
   segunda (`IntegrityError`), que se muestra como "Ya registraste un voto en esta categoría".

### Modelo de datos

```
Edición 1 ── N Categoría 1 ── N Votación 1 ── N Opción
   │              │                │              │
   └──────────────┴──── N Voto N ──┴──────────────┘
                          │
                     N ── 1 Usuario
UNIQUE (usuario, edicion, categoria)
```

## Requisitos

- Python 3.10 o superior (probado con Python 3.12 y Django 5.2.18)
- MySQL 8 (probado con MySQL 8.4)
- En Windows, `mysqlclient` se instala con `pip` sin pasos extra. En Linux necesitas `default-libmysqlclient-dev` y `pkg-config`.

## Instalación y ejecución

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone https://github.com/bsegura4-bit/Festival_Vallenato2027.git
cd Festival_Vallenato2027

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
# 6. Crear las tablas en MySQL (aplica 0001 y 0002)
python manage.py migrate

# 7. Cargar datos de prueba y dos votantes ficticios (votante1 y votante2)
python manage.py cargar_datos_prueba --usuarios

# 8. Crear el usuario administrador
python manage.py createsuperuser

# 9. Ejecutar el servidor
python manage.py runserver
```

Abrir <http://127.0.0.1:8000/> (sitio), <http://127.0.0.1:8000/api/categorias/> (API) y
<http://127.0.0.1:8000/admin/> (administración). Los votantes de prueba usan la clave de demostración
que imprime el comando del paso 7; es una cuenta ficticia solo para pruebas locales.

### Pruebas automáticas

```bash
python manage.py test
```

Crea la base temporal `test_festival_votaciones` en MySQL y ejecuta 38 pruebas: las 25 de la Entrega 2 y
13 nuevas del módulo de votos (CP-01 a CP-10, CSRF, método GET y la restricción única en la base de datos).
La prueba CP-09 lanza varios hilos con conexiones distintas a MySQL al mismo tiempo.

### Prueba manual de concurrencia (CP-09)

```bash
python manage.py probar_concurrencia --usuario votante2 --hilos 6
```

Envía 6 votos simultáneos del mismo usuario en una categoría con dos subeventos y muestra cuántos quedaron
guardados en MySQL (debe ser 1).

## API GET `/api/categorias/`

Responde JSON (UTF-8) con la edición publicada más reciente; con `?edicion=2026` se consulta otra edición.
Solo acepta GET (otro método responde 405). No es necesario iniciar sesión.

```json
{
  "edicion": {"anio": 2027, "nombre": "60.º Festival de la Leyenda Vallenata", "lugar": "Valledupar, Cesar"},
  "total_categorias": 6,
  "categorias": [
    {
      "id": 1, "nombre": "Acordeón Profesional", "descripcion": "...",
      "votaciones": [
        {"id": 1, "titulo": "Votación del público · Acordeonero profesional favorito", "estado": "abierta",
         "acepta_votos": true, "cierre": "2027-05-02T23:59:00-05:00",
         "opciones": [{"id": 1, "nombre": "Concursante de prueba 1", "descripcion": "..."}]}
      ]
    }
  ]
}
```

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Inicio con la edición actual, votaciones abiertas y categorías |
| `/ediciones/`, `/categorias/`, `/votaciones/` | Consultas públicas (Entrega 2) |
| `/votaciones/<id>/` | Detalle con las opciones; si la votación está abierta, formulario de voto |
| `/votaciones/<id>/votar/` | POST: confirmación y registro del voto |
| `/mis-votos/` | Categorías votadas y pendientes del usuario |
| `/reporte-votos/` | Conteo de votos por votación y opción (solo administradores) |
| `/api/categorias/` | API GET en JSON |
| `/cuentas/registro/`, `/cuentas/ingresar/`, `/cuentas/salir/`, `/cuentas/perfil/` | Autenticación |
| `/admin/` | Django Admin |

## Estructura

```
├── config/            # settings (MySQL, autenticación, idioma), urls raíz
├── festival/          # modelos, admin, vistas, votos.py (reglas del voto), API, urls, pruebas, comandos
├── cuentas/           # formularios, backend de ingreso con correo, vistas de registro/login/logout
├── templates/         # plantillas (base.html + festival/ + cuentas/)
├── static/            # estilos.css, app.js y Bootstrap 5.3.3 local
├── manage.py
├── requirements.txt
└── .env.example
```

## Equipo

- Brandon Esteban Segura Riveros
- Kelly Dayanna Gonzalez Sarmiento
- Rubian Medina Duran
