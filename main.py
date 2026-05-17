from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import Base, engine, SessionLocal
from routers import auth, members, member_types, config, public, maintenance
from config import config as app_config
from models import Member as MemberModel, MemberType
from datetime import date

# Crear las tablas
Base.metadata.create_all(bind=engine)

# Scheduler global
scheduler = AsyncIOScheduler()


def update_member_statuses_job():
    """Tarea programada para actualizar estados de socios."""
    import logging
    logger = logging.getLogger(__name__)
    
    db = SessionLocal()
    try:
        today = date.today()
        active_types = db.query(MemberType).filter(
            MemberType.name.in_(["ACTIVO", "HONORARIO", "ADHERENTE", "REINGRESO"])
        ).all()
        
        active_type_ids = [mt.id for mt in active_types]
        pendiente_type = db.query(MemberType).filter(MemberType.name == "PENDIENTE").first()
        novato_type = db.query(MemberType).filter(MemberType.name == "NOVATO").first()
        
        if not pendiente_type or not novato_type:
            logger.warning("[Auto-update] Tipos de socio no encontrados")
            return
        
        members = db.query(MemberModel).filter(
            MemberModel.member_type_id.in_(active_type_ids),
            MemberModel.last_payment_date.isnot(None)
        ).all()
        
        updated = 0
        for member in members:
            if member.last_payment_date:
                months_since_payment = (today.year - member.last_payment_date.year) * 12 + \
                                      (today.month - member.last_payment_date.month)
                # Si pasaron más de 12 meses y no es NOVATO, cambiar a PENDIENTE
                if months_since_payment > 12 and member.member_type_id != novato_type.id:
                    member.member_type_id = pendiente_type.id
                    updated += 1
        
        if updated > 0:
            db.commit()
            logger.info(f"[Auto-update] Actualizados {updated} socios a PENDIENTE el {today}")
        else:
            logger.debug(f"[Auto-update] No hay socios para actualizar el {today}")
    except Exception as e:
        logger.error(f"[Auto-update] Error: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Configurar tarea programada para ejecutar diariamente a las 2:00 AM
        scheduler.add_job(
            update_member_statuses_job,
            trigger=CronTrigger(hour=2, minute=0),  # Todos los días a las 2:00 AM
            id="update_member_statuses",
            name="Actualizar estados de socios",
            replace_existing=True
        )
        
        # También ejecutar al iniciar la aplicación para verificar estados inmediatamente
        logger.info("[Startup] Ejecutando actualización inicial de estados de socios...")
        update_member_statuses_job()
        
        # Iniciar el scheduler
        scheduler.start()
        logger.info("[Startup] Scheduler iniciado - Actualización diaria a las 2:00 AM")
    except Exception as e:
        logger.error(f"[Startup] Error iniciando scheduler: {e}", exc_info=True)
    
    yield
    
    # Al cerrar, detener el scheduler
    try:
        scheduler.shutdown()
        logger.info("[Shutdown] Scheduler detenido")
    except Exception as e:
        logger.error(f"[Shutdown] Error deteniendo scheduler: {e}")


app = FastAPI(
    title="Members Management API",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS - Permitir todos los orígenes (Cloudflare puede cambiar el origen)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes (Cloudflare maneja la seguridad)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(members.router)
app.include_router(member_types.router)
app.include_router(config.router)
app.include_router(public.router)
app.include_router(maintenance.router)


@app.get("/")
async def root():
    return {
        "message": "Members Management API",
        "version": "1.0.0",
        "club_name": app_config.club_name
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

