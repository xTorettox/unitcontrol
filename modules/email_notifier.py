import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Dict, Any
import streamlit as st


def send_inspection_email(
    inspection_data: Dict[str, Any],
    pdf_bytes: bytes,
    pdf_filename: str,
    recipient_emails: List[str]
) -> bool:
    """
    Envía un correo electrónico automático a los roles CASS y Administrador
    con el resumen de la inspección y el reporte PDF oficial FSSA 106 adjunto.
    """
    # 1. Obtener credenciales de SMTP desde st.secrets o variables de entorno
    smtp_server = None
    smtp_port = 587
    smtp_user = None
    smtp_password = None
    smtp_from = None

    # Intentar leer desde st.secrets
    try:
        if hasattr(st, "secrets") and "email" in st.secrets:
            sec = st.secrets["email"]
            smtp_server = sec.get("smtp_server")
            smtp_port = int(sec.get("smtp_port", 587))
            smtp_user = sec.get("smtp_user")
            smtp_password = sec.get("smtp_password")
            smtp_from = sec.get("smtp_from", smtp_user)
    except Exception:
        pass

    # Si no están en secrets, intentar variables de entorno
    if not smtp_server:
        smtp_server = os.environ.get("SMTP_SERVER")
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        smtp_from = os.environ.get("SMTP_FROM", smtp_user)

    # Si no hay servidor SMTP configurado, registrar y retornar False sin interrumpir
    if not smtp_server or not smtp_user or not smtp_password:
        print("[Notificación por Email] Servidor SMTP no configurado. Para activar el envío automático, complete [email] en .streamlit/secrets.toml.")
        return False

    if not recipient_emails:
        print("[Notificación por Email] No se especificaron destinatarios.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = f"Sullair Flota <{smtp_from}>"
        msg["To"] = ", ".join(recipient_emails)
        
        nc_count = int(inspection_data.get("nc_count", 0))
        status_tag = f"⚠️ CON {nc_count} NO CONFORMIDADES" if nc_count > 0 else "✅ APROBADO SIN FALLAS"
        
        msg["Subject"] = f"[{status_tag}] Control FSSA 106: {inspection_data.get('interno')} ({inspection_data.get('patente')}) - {inspection_data.get('realizo_nombre', inspection_data.get('user_name'))}"

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

        # Enviar vía SMTP con TLS
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, recipient_emails, msg.as_string())
        server.quit()

        print(f"[Notificación por Email] Correo enviado exitosamente a {recipient_emails}")
        return True
    except Exception as e:
        print(f"[Notificación por Email] Error enviando correo: {e}")
        return False
