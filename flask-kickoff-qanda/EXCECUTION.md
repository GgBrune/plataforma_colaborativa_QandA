# Ejecución de la Aplicación
## Plataforma Colaborativa de Preguntas y Respuestas (Q&A)
Plataforma de preguntas y respuestas destinada a estudiantes universitarios.
-----
## Comandos para usuarios WINDOWS
### 1. Preparación (desde la raíz del repositorio)
```cd flask-kickoff-qanda

ren pyproyect.toml pyproject.toml
copy ..\README.md .\README.md

uv python install 3.10
uv sync
```

### 2. Variables de entorno (en cada terminal nueva)
```$env:SECRET_KEY = "cambiar-por-una-clave-aleatoria-larga"
$env:FORCE_HTTPS = "0"
$env:DATABASE_URL = "sqlite:///app.db"
$env:LLM_PROVIDER = "local"
```

Opcional, con proveedor real:
```$env:OPENAI_API_KEY = "tu-clave"
$env:GEMINI_API_KEY = "tu-clave"
```

### 3. Crear tablas y un administrador
```uv run python -c "from qanda import create_app; from qanda.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
uv run flask --app qanda create-admin admin@ejemplo.com
```
> El comando create-admin te va a pedir la contraseña por prompt; mínimo 8 caracteres.

### 4. Ejecutar la app
`uv run flask --app qanda run --debug`
- Abrir (en el navegador web): http://127.0.0.1:5000

Accesibilidad desde otra máquina de la red:
`uv run flask --app qanda run --debug --host 0.0.0.0 --port 5000`

### 5. Verificación
`uv run pytest -q`

-----
## Comandos para usuarios LINUX
### 1. Preparación (desde la raíz del repositorio)
```cd flask-kickoff-qanda
uv python install 3.10
uv sync
```

### 2. Variables de entorno
```export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export FORCE_HTTPS=0
export DATABASE_URL="sqlite:///app.db"
export LLM_PROVIDER=local
```

### 3. Crear tablas y administrador
```uv run python -c 'from qanda import create_app; from qanda.extensions import db; app = create_app(); app.app_context().push(); db.create_all()'
uv run flask --app qanda create-admin admin@ejemplo.com
```
> Te pide contraseña por prompt; mínimo 8 caracteres.

### 4. Ejecutar
`uv run flask --app qanda run --debug`
- Abrir (en el navegador web): http://127.0.0.1:5000

Para escuchar en todas las interfaces:
`uv run flask --app qanda run --debug --host 0.0.0.0 --port 5000`

### 5. Verificar
`uv run pytest -q`
