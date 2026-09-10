import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Dict, Any, Tuple
import streamlit as st
from database.connection import get_db


def get_effective_smtp_config() -> Dict[str, Any]:
    """
    Obtiene la configuración SMTP activa priorizando:
    1. Base de datos (configurada por Administrador en el panel).
    2. Streamlit Secrets (.streamlit/secrets.toml).
    3. Variables de entorno.
    """
    db = get_db()
    db_config = db.get_smtp_config()
    if db_config and db_config.get("smtp_server") and db_config.get("smtp_user"):
        return db_config

    # Fallback a st.secrets
    try:
        if hasattr(st, "secrets") and "email" in st.secrets:
            sec = st.secrets["email"]
            return {
                "smtp_server": sec.get("smtp_server", ""),
                "smtp_port": int(sec.get("smtp_port", 587)),
                "smtp_user": sec.get("smtp_user", ""),
                "smtp_password": sec.get("smtp_password", ""),
                "smtp_from": sec.get("smtp_from", sec.get("smtp_user", "")),
                "sender_name": sec.get("sender_name", "Sullair Flota"),
                "use_tls": sec.get("use_tls", True)
            }
    except Exception:
        pass

    # Fallback a variables de entorno
    return {
        "smtp_server": os.environ.get("SMTP_SERVER", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
        "smtp_user": os.environ.get("SMTP_USER", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "smtp_from": os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")),
        "sender_name": os.environ.get("SMTP_SENDER_NAME", "Sullair Flota"),
        "use_tls": True
    }


def send_test_email(to_email: str, config: Dict[str, Any] = None) -> Tuple[bool, str]:
    """Envía un correo de prueba para validar la configuración SMTP."""
    cfg = config or get_effective_smtp_config()
    server_addr = cfg.get("smtp_server", "").strip()
    port = int(cfg.get("smtp_port") or 587)
    user = cfg.get("smtp_user", "").strip()
    pwd = cfg.get("smtp_password", "")
    from_addr = (cfg.get("smtp_from") or user).strip()
    sender_name = cfg.get("sender_name") or "Sullair Argentina - Flota"
    use_tls = cfg.get("use_tls", True)

    if not server_addr or not user or not pwd:
        return False, "Complete los campos obligatorios de Servidor, Usuario y Contraseña."

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{from_addr}>"
        msg["To"] = to_email
        msg["Subject"] = "🧪 Prueba de Configuración de Correo - Sullair Flota FSSA 106"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #1e293b; padding: 20px;">
            <div style="max-width: 500px; border: 1px solid #86efac; background: #f0fdf4; border-radius: 8px; padding: 20px;">
                <h3 style="color: #166534; margin-top: 0;">✅ Configuración SMTP Exitosa</h3>
                <p>Este es un correo de prueba enviado desde el sistema de <strong>Control de Vehículos Sullair Argentina</strong>.</p>
                <p style="font-size: 0.9rem; color: #374151;">
                    <strong>Servidor:</strong> <code>{server_addr}:{port}</code><br/>
                    <strong>Casilla Emisora:</strong> <code>{from_addr}</code>
                </p>
                <p style="font-size: 0.85rem; color: #15803d; margin-bottom: 0;">
                    La casilla de correos está lista para emitir notificaciones automáticas y reportes FSSA 106.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, "html"))

        if port == 465:
            server = smtplib.SMTP_SSL(server_addr, port, timeout=12)
        else:
            server = smtplib.SMTP(server_addr, port, timeout=12)
            if use_tls:
                server.starttls()

        server.login(user, pwd)
        server.sendmail(from_addr, [to_email], msg.as_string())
        server.quit()
        return True, f"¡Correo de prueba enviado con éxito a {to_email}!"
    except Exception as e:
        return False, f"Error conectando al servidor SMTP: {str(e)}"


def send_inspection_email(
    inspection_data: Dict[str, Any],
    pdf_bytes: bytes,
    pdf_filename: str,
    recipient_emails: List[str]
) -> bool:
    """
    Envía un correo electrónico automático a los perfiles CASS, inspector y correos adicionales
    con el resumen de la inspección y el reporte PDF oficial FSSA 106 adjunto.
    El remitente visible y la dirección From corresponden al usuario que realizó la inspección.
    """
    cfg = get_effective_smtp_config()
    smtp_server = cfg.get("smtp_server")
    smtp_port = int(cfg.get("smtp_port", 587))
    smtp_user = cfg.get("smtp_user")
    smtp_password = cfg.get("smtp_password")
    smtp_from = cfg.get("smtp_from") or smtp_user
    use_tls = cfg.get("use_tls", True)

    if not smtp_server or not smtp_user or not smtp_password:
        print("[Notificación por Email] Servidor SMTP no configurado. Configure la casilla en el Panel de Administrador.")
        return False

    clean_recipients = [r.strip().lower() for r in recipient_emails if r and "@" in r]
    clean_recipients = list(dict.fromkeys(clean_recipients))

    if not clean_recipients:
        print("[Notificación por Email] No se especificaron destinatarios válidos.")
        return False

    # Datos del remitente: quien generó la inspección
    inspector_name = inspection_data.get("realizo_nombre") or inspection_data.get("user_name") or cfg.get("sender_name") or "Sullair Flota"
    inspector_email = inspection_data.get("user_email") or smtp_from or smtp_user

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{inspector_name} <{inspector_email}>"
        msg["Reply-To"] = f"{inspector_name} <{inspector_email}>"
        msg["To"] = ", ".join(clean_recipients)
        
        nc_count = int(inspection_data.get("nc_count", 0))
        status_tag = f"⚠️ CON {nc_count} NO CONFORMIDADES" if nc_count > 0 else "✅ APROBADO SIN FALLAS"
        
        msg["Subject"] = f"[{status_tag}] Control FSSA 106: {inspection_data.get('interno')} ({inspection_data.get('patente')}) - {inspector_name}"

        # Cuerpo del correo en HTML institucional
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #1e293b; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #00853E; padding: 20px; text-align: center; color: #ffffff;">
                    <h2 style="margin: 0;">Sullair Argentina S.A.</h2>
                    <p style="margin: 5px 0 0 0; font-size: 0.95rem;">Control de Vehículos - FSSA 106 Rev. 06</p>
                </div>
                <div style="padding: 24px;">
                    <h3 style="color: #005A2A; margin-top: 0;">Nueva Inspección Mensual Registrada</h3>
                    <p>Se ha cargado un nuevo reporte oficial en el sistema con el siguiente detalle:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr style="background-color: #f8fafc;">
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: bold;">Unidad / Interno:</td>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{inspection_data.get('interno')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: bold;">Patente:</td>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{inspection_data.get('patente')}</td>
                        </tr>
                        <tr style="background-color: #f8fafc;">
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: bold;">Vehículo:</td>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{inspection_data.get('marca')} {inspection_data.get('modelo')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: bold;">Kilometraje Actual:</td>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{int(inspection_data.get('km', 0)):,} km</td>
                        </tr>
                        <tr style="background-color: #f8fafc;">
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: bold;">Inspector:</td>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{inspection_data.get('realizo_nombre', inspection_data.get('user_name'))}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: bold;">Fecha del Control:</td>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{inspection_data.get('fecha')}</td>
                        </tr>
                        <tr style="background-color: #f8fafc;">
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: bold;">Resultado:</td>
                            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; color: {'#dc2626' if nc_count > 0 else '#16a34a'}; font-weight: bold;">
                                {'⚠️ Contiene ' + str(nc_count) + ' No Conformidades' if nc_count > 0 else '✅ Cumple Satisfactoriamente'}
                            </td>
                        </tr>
                    </table>

                    {f'<p><strong>Observaciones:</strong> {inspection_data.get("observaciones")}</p>' if inspection_data.get('observaciones') else ''}

                    <p style="margin-top: 20px; font-size: 0.9rem; color: #64748b;">
                        📄 Se adjunta el documento oficial en formato PDF firmado digitalmente.
                    </p>
                </div>
                <div style="background-color: #f1f5f9; padding: 12px; text-align: center; font-size: 0.8rem; color: #64748b;">
                    Sistema de Gestión de Flota - Sullair Argentina S.A.
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # Adjuntar PDF
        if pdf_bytes:
            part = MIMEApplication(pdf_bytes, Name=pdf_filename)
            part["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'
            msg.attach(part)

        # Enviar vía SMTP
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=12)
            if use_tls:
                server.starttls()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, clean_recipients, msg.as_string())
        server.quit()

        print(f"[Notificación por Email] Correo enviado exitosamente a {clean_recipients}")
        return True
    except Exception as e:
        print(f"[Notificación por Email] Error enviando correo: {e}")
        return False
