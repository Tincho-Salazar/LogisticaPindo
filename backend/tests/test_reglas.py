"""Pruebas de las reglas de negocio puras (criterios de aceptación 17.2)."""
import pytest

from app import reglas


def pilas():
    return [
        {"id": "a", "tipo": "grueso", "largo_pies": 12, "uso": "pindo", "volumen_m3": 10.0},
        {"id": "b", "tipo": "grueso", "largo_pies": 12, "uso": "ventas", "volumen_m3": 10.0},
    ]


def test_industria_no_consume_ventas():
    with pytest.raises(reglas.StockInsuficiente) as e:
        reglas.descontar_stock(pilas(), [{"tipo": "grueso", "largo_pies": 12, "volumen_m3": 12}], "industria")
    assert e.value.detalle["disponible"] == 10.0


def test_ventas_consume_primero_ventas():
    n = reglas.descontar_stock(pilas(), [{"tipo": "grueso", "largo_pies": 12, "volumen_m3": 12}], "ventas")
    assert n == {"b": 0.0, "a": 8.0}


def test_descuento_industria():
    n = reglas.descontar_stock(pilas(), [{"tipo": "grueso", "largo_pies": 12, "volumen_m3": 4.5}], "industria")
    assert n == {"a": 5.5}


def test_avance_pedido_exceso_no_compensa():
    ped = [{"tipo": "grueso", "largo_pies": 12, "volumen_m3": 60}, {"tipo": "fino", "largo_pies": 10, "volumen_m3": 30}]
    av = reglas.avance_pedido(ped, {"grueso|12": 70.0, "grueso|20": 5.0})
    assert av["cumplimiento_pct"] == 67  # 60 de 90
    assert av["faltante"] == 30.0
    assert av["fuera_de_pedido"] == 5.0
    assert av["lineas"][0]["avance_pct"] == 100


def test_importe_por_traccion():
    t = {"tarifa_4x2": 5500, "tarifa_6x4": 5800}
    assert reglas.importe_remito(t, "4x2", 10.0) == 55000
    assert reglas.importe_remito(t, "6x4", 27.4) == round(5800 * 27.4)
    assert reglas.importe_remito(None, "6x4", 27.4) is None
    assert reglas.importe_remito({"tarifa_4x2": 0, "tarifa_6x4": 5800}, "4x2", 25.0) is None


def test_eta_bascula():
    mins, eta = reglas.eta_bascula("2026-10-30T08:00:00", 30.0, 12.5)
    # 30/60 = 0.5h (30m) + 12.5/25 = 0.5h (30m) = 60 min
    assert mins == 60
    assert eta == "2026-10-30T09:00:00"


def test_demora_inicio():
    assert reglas.demora_inicio("07:30", "07:50") == (20, 20, False)
    assert reglas.demora_inicio("07:30", "07:34") == (4, 4, True)
    assert reglas.demora_inicio("07:30", "07:20") == (-10, 0, True)


def test_ciclo():
    assert reglas.ciclo_min("2026-10-30T08:00:00", "2026-10-30T10:30:00") == 150
    assert reglas.ciclo_min("2026-10-30T08:00:00", None) is None
    assert reglas.ciclo_min("2026-10-30T08:00:00", "2026-10-31T08:00:00") is None


def test_patente_norm():
    assert reglas.patente_norm(" ab 123 cd ") == "AB123CD"
    assert reglas.normalizar_rodal("mma-07 xc_073") == "MMA07XC073"
