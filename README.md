# Backend - Members Management API

API REST desarrollada con FastAPI para la gestión de socios de un club.

## Configuración

### Variables de Entorno

Crea un archivo `.env` basado en `.env.example`:

```env
SECRET_KEY=your-secret-key-here-change-this-in-production
CLUB_NAME=Club de Cervezas Demo
FRONTEND_URL=http://localhost:3000
ANNUAL_FEE_AMOUNT=1000
```

### Archivo de Configuración

El sistema lee la configuración desde un archivo `.conf` que puede usar variables de entorno. Copia `.conf.example` a `.conf` y ajusta los valores.

## Desarrollo Local

1. Instala las dependencias:
```bash
pip install -r requirements.txt
```

2. Inicializa la base de datos:
```bash
python init_db.py
```

3. Ejecuta la aplicación:
```bash
uvicorn main:app --reload
```

La API estará disponible en `http://localhost:8000`

## Docker

### Construir la imagen para desarrollo:
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t tinouy/geso-backend:test --target dev -f Dockerfile . --push --no-cache
```

### Construir la imagen para producción:
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t tinouy/geso-backend:stable --target prod -f Dockerfile . --push --no-cache
```

### Construir solo para tu plataforma local (más rápido):
```bash
# Desarrollo
docker build -t tinouy/geso-backend:test --target dev -f Dockerfile .

# Producción
docker build -t tinouy/geso-backend:stable --target prod -f Dockerfile .
```

### Ejecutar el contenedor:
```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/geso_db:/app/data \
  -e DATABASE_URL=sqlite:///./data/geso.db \
  tinouy/geso-backend:test
```

## Endpoints Principales

- `POST /api/auth/login` - Login de usuario
- `GET /api/members` - Lista de socios
- `POST /api/members` - Crear socio
- `PUT /api/members/{id}` - Actualizar socio
- `POST /api/members/bulk-update` - Actualizar múltiples socios
- `GET /api/public/check-benefit?member_number=XXX` - Verificar beneficios (público)
- `GET /api/config` - Obtener configuración
- `PUT /api/config` - Actualizar configuración (solo admin)

