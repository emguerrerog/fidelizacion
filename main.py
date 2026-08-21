import os
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

load_dotenv("/etc/secrets/.env") # solo en local

DATABASE_URL = os.getenv("DATABASE_URL")
BUSINESS_PASSWORD = os.getenv("ADMIN_PASSWORD")

#DATABASE_URL = os.environ.get("DATABASE_URL")
#BUSINESS_PASSWORD = os.environ.get("ADMIN_PASSWORD")

if not DATABASE_URL or not BUSINESS_PASSWORD:
    raise RuntimeError("Faltan variables de entorno en el archivo .env")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS ORM ---

class Persona(Base):
    __tablename__ = "persona"
    persona_id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    celular = Column(String(10), nullable=True)
    instagram = Column(String(100), nullable=True)
    firma_tratamiento_atos = Column(BIT(1), nullable=False)
    contactabilidad = Column(BIT(1), nullable=False)
    activo = Column(BIT(1), nullable=False, default="1")
    fecha_registro = Column(Date, nullable=False, default=date.today)

    puntos = relationship("Punto", back_populates="persona")
    premios = relationship("Premio", back_populates="persona")

class Punto(Base):
    __tablename__ = "punto"
    punto_id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("persona.persona_id"), nullable=False)
    punto_utilizado = Column(BIT(1), nullable=False, default="0")
    fecha_registro = Column(Date, nullable=False, default=date.today)

    persona = relationship("Persona", back_populates="puntos")

class PremioCatalogo(Base):
    __tablename__ = "premio_catalogo"
    premio_catalogo_id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    descripcion = Column(String(200))
    puntos_requeridos = Column(Integer, nullable=False)
    fecha_vigencia_inicio = Column(Date, nullable=False)
    fecha_vigencia_fin = Column(Date, nullable=False)
    activo = Column(BIT(1), nullable=False, default="1")

class Premio(Base):
    __tablename__ = "premio"
    premio_id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("persona.persona_id"), nullable=False)
    premio_catalogo_id = Column(Integer, ForeignKey("premio_catalogo.premio_catalogo_id"), nullable=False)
    fecha_premio = Column(Date, nullable=True)
    fecha_registro = Column(Date, nullable=False, default=date.today)

    persona = relationship("Persona", back_populates="premios")
    catalogo = relationship("PremioCatalogo")

class PremioPuntos(Base):
    __tablename__ = "premio_puntos"
    premio_id = Column(Integer, ForeignKey("premio.premio_id"), primary_key=True)
    punto_id = Column(Integer, ForeignKey("punto.punto_id"), primary_key=True)
    fecha_registro = Column(Date, nullable=False, default=date.today)

# --- SCHEMAS PYDANTIC ---

class PersonaCreate(BaseModel):
    nombre_completo: str
    email: EmailStr
    celular: Optional[str] = None
    instagram: Optional[str] = None
    firma_tratamiento_atos: bool
    contactabilidad: bool

class PersonaUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    celular: Optional[str] = None
    instagram: Optional[str] = None
    contactabilidad: Optional[bool] = None
    activo: Optional[bool] = None

class AddPuntos(BaseModel):
    cantidad: int

class RedeemPremio(BaseModel):
    premio_catalogo_id: int

class PremioCatalogoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    puntos_requeridos: int
    fecha_vigencia_inicio: date
    fecha_vigencia_fin: date

class LoginRequest(BaseModel):
    password: str

# --- INICIALIZACIÓN DE APP ---

app = FastAPI(title="Sistema de Fidelización Cumbre")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verificar_password_negocio(x_business_key: Optional[str] = Header(None)):
    if x_business_key != BUSINESS_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña de negocio no válida")

# --- ENDPOINTS CLIENTE ---

@app.get("/api/cliente/consultar/{email}")
def consultar_cliente(email: str, db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.email == email).first()
    if not persona:
        return {"registrado": False}

    puntos_disponibles = db.query(Punto).filter(
        Punto.persona_id == persona.persona_id, Punto.punto_utilizado == "0"
    ).count()

    puntos_usados = db.query(Punto).filter(
        Punto.persona_id == persona.persona_id, Punto.punto_utilizado == "1"
    ).count()

    premios = db.query(Premio).filter(Premio.persona_id == persona.persona_id).all()
    historial_premios = [
        {
            "premio_id": p.premio_id,
            "nombre": p.catalogo.nombre if p.catalogo else "Desconocido",
            "fecha_reclamo": str(p.fecha_premio or p.fecha_registro)
        }
        for p in premios
    ]

    return {
        "registrado": True,
        "persona": {
            "persona_id": persona.persona_id,
            "nombre_completo": persona.nombre_completo,
            "email": persona.email,
            "celular": persona.celular,
            "instagram": persona.instagram,
            "activo": str(persona.activo) == "1"
        },
        "puntos_disponibles": puntos_disponibles,
        "puntos_reclamados": puntos_usados,
        "premios_reclamados": historial_premios
    }

@app.post("/api/cliente/registrar")
def registrar_cliente(data: PersonaCreate, db: Session = Depends(get_db)):
    existe = db.query(Persona).filter(Persona.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya se encuentra registrado.")
    
    nueva_persona = Persona(
        nombre_completo=data.nombre_completo,
        email=data.email,
        celular=data.celular or None,
        instagram=data.instagram or None,
        firma_tratamiento_atos="1" if data.firma_tratamiento_atos else "0",
        contactabilidad="1" if data.contactabilidad else "0",
        activo="1",
        fecha_registro=date.today()
    )
    db.add(nueva_persona)
    db.commit()
    db.refresh(nueva_persona)
    return {"status": "ok", "persona_id": nueva_persona.persona_id}

# --- ENDPOINTS NEGOCIO ---

@app.post("/api/negocio/login")
def login_negocio(req: LoginRequest):
    if req.password == BUSINESS_PASSWORD:
        return {"status": "ok", "auth": True}
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")

@app.put("/api/negocio/cliente/{persona_id}", dependencies=[Depends(verificar_password_negocio)])
def actualizar_cliente(persona_id: int, data: PersonaUpdate, db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.persona_id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    if data.nombre_completo is not None:
        persona.nombre_completo = data.nombre_completo
    if data.celular is not None:
        persona.celular = data.celular
    if data.instagram is not None:
        persona.instagram = data.instagram
    if data.contactabilidad is not None:
        persona.contactabilidad = "1" if data.contactabilidad else "0"
    if data.activo is not None:
        persona.activo = "1" if data.activo else "0"
    
    db.commit()
    return {"status": "ok", "message": "Datos actualizados correctamente"}

@app.post("/api/negocio/cliente/{persona_id}/puntos", dependencies=[Depends(verificar_password_negocio)])
def sumar_puntos(persona_id: int, data: AddPuntos, db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.persona_id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    for _ in range(data.cantidad):
        nuevo_punto = Punto(
            persona_id=persona_id,
            punto_utilizado="0",
            fecha_registro=date.today()
        )
        db.add(nuevo_punto)
    
    db.commit()
    return {"status": "ok", "message": f"{data.cantidad} puntos asignados correctamente"}

@app.post("/api/negocio/cliente/{persona_id}/redimir", dependencies=[Depends(verificar_password_negocio)])
def redimir_premio(persona_id: int, data: RedeemPremio, db: Session = Depends(get_db)):
    catalogo = db.query(PremioCatalogo).filter(PremioCatalogo.premio_catalogo_id == data.premio_catalogo_id).first()
    if not catalogo or str(catalogo.activo) != "1":
        raise HTTPException(status_code=400, detail="Premio no válido o inactivo")

    puntos_disponibles = db.query(Punto).filter(
        Punto.persona_id == persona_id, Punto.punto_utilizado == "0"
    ).order_by(Punto.fecha_registro.asc()).all()

    if len(puntos_disponibles) < catalogo.puntos_requeridos:
        raise HTTPException(status_code=400, detail="Puntos insuficientes para este premio")

    nuevo_premio = Premio(
        persona_id=persona_id,
        premio_catalogo_id=catalogo.premio_catalogo_id,
        fecha_premio=date.today(),
        fecha_registro=date.today()
    )
    db.add(nuevo_premio)
    db.flush()

    puntos_a_usar = puntos_disponibles[:catalogo.puntos_requeridos]
    for p in puntos_a_usar:
        p.punto_utilizado = "1"
        asociacion = PremioPuntos(
            premio_id=nuevo_premio.premio_id,
            punto_id=p.punto_id,
            fecha_registro=date.today()
        )
        db.add(asociacion)

    db.commit()
    return {"status": "ok", "message": f"Premio '{catalogo.nombre}' redimido exitosamente"}

@app.get("/api/negocio/catalogo", dependencies=[Depends(verificar_password_negocio)])
def obtener_catalogo(db: Session = Depends(get_db)):
    return db.query(PremioCatalogo).filter(PremioCatalogo.activo == "1").all()

@app.post("/api/negocio/catalogo", dependencies=[Depends(verificar_password_negocio)])
def crear_premio_catalogo(data: PremioCatalogoCreate, db: Session = Depends(get_db)):
    nuevo_item = PremioCatalogo(
        nombre=data.nombre,
        descripcion=data.descripcion or "",
        puntos_requeridos=data.puntos_requeridos,
        fecha_vigencia_inicio=data.fecha_vigencia_inicio,
        fecha_vigencia_fin=data.fecha_vigencia_fin,
        activo="1"
    )
    db.add(nuevo_item)
    db.commit()
    db.refresh(nuevo_item)
    return {"status": "ok", "premio_catalogo_id": nuevo_item.premio_catalogo_id}

@app.get("/")
async def root():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo index.html no encontrado")
    return FileResponse(file_path, media_type="text/html")
