from __future__ import annotations

import argparse
import time

import obd


PIDS = (
    ("RPM", obd.commands.RPM),
    ("Velocidade", obd.commands.SPEED),
    ("Acelerador", obd.commands.THROTTLE_POS),
    ("Temperatura", obd.commands.COOLANT_TEMP),
    ("Carga do motor", obd.commands.ENGINE_LOAD),
    ("Ar de admissão", obd.commands.INTAKE_TEMP),
    ("Tensão", obd.commands.ELM_VOLTAGE),
)
QUERY_DELAY = 0.3
CYCLE_DELAY = 1.0


def connect(port: str | None) -> int:
    while True:
        print(f"Conectando em {port or 'porta automática'}...", flush=True)
        connection = obd.OBD(
            portstr=port,
            fast=False,
            timeout=5,
            check_voltage=False,
        )
        reconnect = False
        try:
            status = connection.status()
            print(f"Status da conexão: {status}", flush=True)
            if status != obd.OBDStatus.CAR_CONNECTED:
                print(f"Falha na conexão: {status}")
                return 1

            print(f"Conectado ({connection.port_name()})")
            print("Lendo dados; pressione Ctrl+C para sair.\n")
            last_status = status
            failed_reads = 0
            supported_pids = tuple(
                (label, command)
                for label, command in PIDS
                if connection.supports(command)
            )
            try:
                while True:
                    status = connection.status()
                    if status != last_status:
                        print(f"Status da conexão: {status}", flush=True)
                        last_status = status
                    if status != obd.OBDStatus.CAR_CONNECTED:
                        reconnect = True
                        break

                    for label, command in supported_pids:
                        try:
                            response = connection.query(command)
                        except Exception as error:
                            print(f"Falha ao ler {label}: {error}", flush=True)
                            response = None

                        if response is None or response.is_null():
                            failed_reads += 1
                            print(f"{label}: indisponível", flush=True)
                            if failed_reads >= 3:
                                reconnect = True
                                break
                            time.sleep(QUERY_DELAY)
                            continue

                        failed_reads = 0
                        value = response.value
                        if hasattr(value, "magnitude"):
                            value = value.magnitude
                        print(f"{label}: {value}", flush=True)
                        time.sleep(QUERY_DELAY)

                    if reconnect:
                        break
                    print(flush=True)
                    time.sleep(CYCLE_DELAY)
            except KeyboardInterrupt:
                print("\nLeitura encerrada.")
                return 0
        finally:
            connection.close()

        if reconnect:
            print("Conexão perdida. Tentando reconectar em 2 segundos...", flush=True)
            time.sleep(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Teste de conexão OBD2 (ELM327)")
    parser.add_argument("--port", help="porta COM do adaptador, ex.: COM3")
    parser.add_argument(
        "--list-ports", action="store_true", help="lista portas seriais"
    )
    args = parser.parse_args()

    if args.list_ports:
        from serial.tools import list_ports

        for port in list_ports.comports():
            print(f"{port.device} - {port.description}")
        return 0

    return connect(args.port)


if __name__ == "__main__":
    raise SystemExit(main())
