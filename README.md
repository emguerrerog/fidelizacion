# Cumbre Café - Sistema de Fidelización

pyhton + HTML

## Módulos

### Cliente
- Registro de persona.
- Inicio de sesión.
- Consulta de puntos disponibles, utilizados y totales.
- Consulta de premios reclamados.
- Actualización de datos de contacto.

### Negocio
- Inicio de sesión con rol NEGOCIO.
- Búsqueda de clientes.
- Edición de datos de clientes.
- Asignación de puntos.
- Administración del catálogo de premios.
- Redención de premios usando puntos disponibles.
- Historial de redenciones.

## Instalación

1. Crear una base PostgreSQL llamada `cumbre_fidelizacion`.
2. Copiar `.env.example` como `.env` y ajustar `DATABASE_URL` y `JWT_SECRET`.
3. Ejecutar `schema.sql` en PostgreSQL.
4. Instalar dependencias:

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic
python -m pip install -r requirements.txt
```

6. Iniciar:

```bash
uvicorn main:app --reload --port 8000
python -m uvicorn main:app --reload --port 8000
```

Abrir `http://localhost:3000`.

## Seguridad

Este proyecto es un MVP. Antes de publicarlo en Internet se recomienda añadir HTTPS, rate limiting, recuperación de contraseña, validación más estricta, auditoría de operaciones, CSRF si se usan cookies, políticas de contraseñas, bloqueo de intentos y separación de permisos por operación.
