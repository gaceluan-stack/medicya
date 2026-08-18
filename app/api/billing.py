import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.db import models
from app.schemas import billing as billing_schemas
from app.api import deps

router = APIRouter(prefix="/billing", tags=["Facturación"])

class PagoCheckoutPayload(BaseModel):
    numero_tarjeta: Optional[str] = None
    nombre_titular: Optional[str] = None
    telefono_payphone: Optional[str] = None
    cvc: Optional[str] = None
    fecha_expiracion: Optional[str] = None
    metodo: str # 'PayPhone', 'Kushki', 'Transferencia'

@router.get("/mis-facturas", response_model=List[billing_schemas.FacturaResponse])
def get_mis_facturas(
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Retorna el historial de facturas del proveedor autenticado.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    
    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail="Perfil de proveedor no encontrado"
        )
        
    facturas = db.query(models.Factura).filter(
        models.Factura.proveedor_id == proveedor.id
    ).order_by(models.Factura.fecha_emision.desc()).all()
    
    return facturas

@router.get("/facturas", response_model=List[billing_schemas.FacturaResponse])
def list_todas_facturas(
    current_user: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Lista todas las facturas del sistema (para uso exclusivo del Administrador).
    """
    return db.query(models.Factura).order_by(models.Factura.fecha_emision.desc()).all()

@router.post("/facturas/{id}/pagar")
def pagar_factura(
    id: str,
    checkout_in: Optional[PagoCheckoutPayload] = None,
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Simulación de pago de factura con integración de pasarelas locales (PayPhone, Kushki, Transferencia).
    Valida las credenciales de pago simuladas, liquida la factura a 'PAGADA' y restaura
    el estado del proveedor a 'ACTIVO' si no tiene más deudas vencidas.
    """
    factura = db.query(models.Factura).filter(models.Factura.id == id).first()
    if not factura:
        raise HTTPException(
            status_code=404,
            detail="Factura no encontrada"
        )
        
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.id == factura.proveedor_id
    ).first()
    
    # Validar permisos (Solo el admin o el propio proveedor dueño de la factura pueden pagarla)
    if current_user.rol != models.RolUsuario.ADMIN and current_user.id != proveedor.usuario_id:
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para pagar esta factura"
        )
        
    if factura.estado == models.EstadoFactura.PAGADA:
        return {"message": "La factura ya se encuentra pagada", "transaction_id": "PREVIOUSLY_PAID"}
        
    # --- SIMULACIÓN DE PASARELAS DE PAGO LOCALES ---
    metodo_pago = "Manual/Admin"
    transaction_id = f"TX-SIM-{str(uuid.uuid4()).split('-')[0].upper()}"
    
    if checkout_in:
        metodo_pago = checkout_in.metodo
        if checkout_in.metodo == 'PayPhone':
            if not checkout_in.telefono_payphone:
                raise HTTPException(status_code=400, detail="El número de teléfono de PayPhone es obligatorio para este método")
            # Simular cobro por PayPhone (requiere confirmación en la app del usuario)
            print(f"[PayPhone] Enviando solicitud de cobro de ${factura.monto_total} al celular {checkout_in.telefono_payphone}")
            transaction_id = f"TX-PAYPHONE-{str(uuid.uuid4()).split('-')[0].upper()}"
            
        elif checkout_in.metodo == 'Kushki':
            if not checkout_in.numero_tarjeta or not checkout_in.cvc:
                raise HTTPException(status_code=400, detail="Los datos de tarjeta son obligatorios para pagar vía Kushki")
            if len(checkout_in.numero_tarjeta.replace(" ", "")) < 15:
                raise HTTPException(status_code=400, detail="Número de tarjeta inválido para la simulación")
            # Simular cobro con tarjeta vía Kushki
            print(f"[Kushki] Procesando tarjeta de {checkout_in.nombre_titular} por ${factura.monto_total}")
            transaction_id = f"TX-KUSHKI-{str(uuid.uuid4()).split('-')[0].upper()}"
            
        elif checkout_in.metodo == 'Transferencia':
            # Simulación de verificación automática de la transferencia del Banco Pichincha / Guayaquil
            print(f"[Banco] Verificando transferencia bancaria directa por ${factura.monto_total}")
            transaction_id = f"TX-BANK-{str(uuid.uuid4()).split('-')[0].upper()}"
            
    # Cambiar estado a pagada
    factura.estado = models.EstadoFactura.PAGADA
    
    # Verificar si el proveedor tiene más facturas pendientes
    facturas_pendientes = db.query(models.Factura).filter(
        models.Factura.proveedor_id == proveedor.id,
        models.Factura.estado != models.EstadoFactura.PAGADA,
        models.Factura.id != factura.id
    ).count()
    
    # Restablecer estado de cuenta a ACTIVO si ya no tiene deudas pendientes
    prov_usuario = proveedor.usuario
    if facturas_pendientes == 0 and prov_usuario.estado != models.EstadoUsuario.ACTIVO:
        prov_usuario.estado = models.EstadoUsuario.ACTIVO
        db.add(prov_usuario)
        
    db.commit()
    
    return {
        "message": f"Factura liquidada con éxito vía {metodo_pago}",
        "transaction_id": transaction_id,
        "estado_cuenta_proveedor": prov_usuario.estado.value
    }
