"""Peças falsas compartilhadas pelos testes da Task 4 (FIWARE, relógio, frota)."""
from app.models.schemas_fleet import SensorValues, VinheriaStatus


def status_vinheria(device_id: str = "vinheria001", status: str = "ok") -> VinheriaStatus:
    """Um VinheriaStatus mínimo, para testes de frota e de comandos."""
    return VinheriaStatus(device_id=device_id, name="Vinheria", city="Cidade", status=status,
                          current=SensorValues(), active_alerts=[])
