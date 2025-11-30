from fastapi import APIRouter, HTTPException , Query
from core.prometheus_client import PrometheusClient

from apscheduler.schedulers.background import BackgroundScheduler
from statistics import mean, stdev
import os
import time
import smtplib
from email.mime.text import MIMEText
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import requests
import re



router = APIRouter()
prometheus = PrometheusClient()


# ===== Email Setup =====
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "abdellaalimohamad4321@gmail.com"         # your Gmail address
EMAIL_PASS = "grhy xrpf npbq adkq"       # the 16-character App Password
ALERT_EMAIL_TO = "naitpublicstore2001@gmail.com"  # where to send test email


# ===== Anomaly Detection Config =====
CPU_HISTORY = {}   # {container_name: [cpu_values]}
MEM_HISTORY = {}   # {container_name: [mem_values]}
MAX_HISTORY = 20   # how many points to keep per container
CHECK_INTERVAL = 300  # 5 minutes in seconds

# ===== Alert Function =====
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

def send_email_alert(container_name: str, cpu_pred: float, mem_pred: float, error_count: int, total_risk: float, risk_level: str):
    """
    Envoie un email détaillé concernant l’état prédictif d’un conteneur.
    """
    if not (EMAIL_HOST and EMAIL_PORT and EMAIL_USER and EMAIL_PASS and ALERT_EMAIL_TO):
        print("⚠️ Configuration email manquante, alerte ignorée.")
        return

    try:
        #  Sujet de l’email
        subject = f"🚨 Alerte Prédictive - {container_name} [{risk_level}]"

        #  Corps du message en HTML
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color:#D32F2F;">🚨 Alerte Prédictive de Conteneur</h2>
            <p><b>Conteneur :</b> {container_name}</p>
            <p><b>Niveau de Risque :</b> {risk_level} ({round(total_risk, 2)}%)</p>

            <h3>📊 Prédictions :</h3>
            <ul>
                <li><b>CPU Prévu :</b> {round(cpu_pred, 2)}%</li>
                <li><b>Mémoire Prévue :</b> {round(mem_pred, 2)} Mo</li>
                <li><b>Erreurs Récentes :</b> {error_count}</li>
            </ul>

            <h3>🩺 Recommandations :</h3>
            <p>
        """

        if "CRITICAL" in risk_level:
            html_content += "⚠️ <b>Action immédiate requise :</b> surveillez ou redémarrez le conteneur pour éviter un crash potentiel."
        elif "WARNING" in risk_level:
            html_content += "🟠 <b>Surveillance recommandée :</b> les métriques augmentent, pensez à vérifier les logs et l’usage CPU."
        else:
            html_content += "🟢 <b>Tout semble stable :</b> aucun signe de surcharge détecté."

        html_content += """
            </p>
            <hr>
            <p style="font-size:12px; color:#666;">
                🔍 Rapport généré automatiquement par votre agent prédictif Docker.
            </p>
        </body>
        </html>
        """

        # ✉️ Création du message multipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = ALERT_EMAIL_TO
        msg.attach(MIMEText(html_content, "html"))

        # 🔐 Envoi
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"📧 Email d’alerte envoyé pour {container_name} ({risk_level})")

    except Exception as e:
        print(f"❌ Erreur lors de l’envoi de l’email : {e}")


# ===== Core Anomaly Detection =====
# ===== Core Anomaly Detection =====
def detect_anomalies():
    """
    Fetch metrics from Prometheus, analyze trends,
    and send alerts if CPU or Memory usage deviates abnormally.
    Handles non-numeric values safely.
    """
    print(f" Checking metrics for anomalies at {time.strftime('%H:%M:%S')}")
    containers = prometheus.list_containers()

    for container in containers:
        metrics = prometheus.get_container_metrics(container)
        
        # Safely convert metrics to float
        def to_float_safe(val, default=0.0):
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        cpu = to_float_safe(metrics.get("cpu_usage"))
        mem = to_float_safe(metrics.get("memory_usage"))

        # Maintain metric history
        CPU_HISTORY.setdefault(container, []).append(cpu)
        MEM_HISTORY.setdefault(container, []).append(mem)

        # Keep history bounded
        if len(CPU_HISTORY[container]) > MAX_HISTORY:
            CPU_HISTORY[container].pop(0)
        if len(MEM_HISTORY[container]) > MAX_HISTORY:
            MEM_HISTORY[container].pop(0)

        # Skip anomaly detection until we have enough data
        if len(CPU_HISTORY[container]) < 5:
            continue

        # Only use numeric values for mean/std
        cpu_values = [v for v in CPU_HISTORY[container] if isinstance(v, (int, float))]
        mem_values = [v for v in MEM_HISTORY[container] if isinstance(v, (int, float))]

        if not cpu_values or not mem_values:
            continue  # skip if history has no valid numeric entries

        # Compute moving average + std deviation
        cpu_mean = mean(cpu_values)
        cpu_std = stdev(cpu_values) or 1
        mem_mean = mean(mem_values)
        mem_std = stdev(mem_values) or 1

        # Detect significant deviation (Z-score > 3)
        cpu_z = abs((cpu - cpu_mean) / cpu_std)
        mem_z = abs((mem - mem_mean) / mem_std)

        if cpu_z > 3:
            msg = f"🚨 Anomaly detected: {container} CPU spike! Current={cpu:.2f}%, Mean={cpu_mean:.2f}%"
            send_email_alert(f"CPU Anomaly: {container}", msg)
        if mem_z > 3:
            msg = f"⚠️ Anomaly detected: {container} Memory spike! Current={mem:.2f}MB, Mean={mem_mean:.2f}MB"
            send_email_alert(f"CPU Anomaly: {container}", msg)


# ===== Background Scheduler =====
scheduler = BackgroundScheduler()
scheduler.add_job(detect_anomalies, "interval", seconds=CHECK_INTERVAL)
scheduler.start()
print("✅ Automatic anomaly detection job scheduled every 5 minutes.")





# ===== API Endpoints =====

@router.get("/container/{container_name}")
def get_container_metrics(container_name: str):
    """
    Get live metrics (CPU, Memory) for a specific container.
    """
    try:
        return prometheus.get_container_metrics(container_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/containers")
def list_all_containers():
    """
    List all containers Prometheus is monitoring.
    """
    try:
        return prometheus.list_containers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies/run-now")
def run_anomaly_detection_now():
    """
    Manual trigger for anomaly detection (useful for testing)
    """
    try:
        detect_anomalies()
        send_email_alert("CPU Anomaly: ", "testing")
        return {"message": "Anomaly detection executed manually."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.get("/predict/{container_name}")
def predict_container_health(container_name: str, hours: int = Query(1, ge=1, le=24)):
    """
    Predict CPU/Memory trends for the next X hours (user-defined)
    and adjust risk level based on recent error logs.
    """
    try:
        # 1️⃣ Fetch recent metrics (past 'hours')
        now = datetime.utcnow()
        past = now - timedelta(hours=hours)

        cpu_data = prometheus.query_range(
            f'rate(container_cpu_usage_seconds_total{{name="{container_name}"}}[1m])',
            start=past, end=now, step='1m'
        )
        mem_data = prometheus.query_range(
            f'container_memory_usage_bytes{{name="{container_name}"}}',
            start=past, end=now, step='1m'
        )


        if not cpu_data or not mem_data:
            raise HTTPException(status_code=404, detail="No metrics found for container.")

        # 2️⃣ Prepare data for regression
        # 2️⃣ Prepare data for regression (fixing inconsistent lengths)
        cpu_values = [float(v[1]) * 100 for v in cpu_data[0]['values']]
        mem_values = [float(v[1]) / (1024 * 1024) for v in mem_data[0]['values']]

        # ✅ Align both lists to the same length
        min_len = min(len(cpu_values), len(mem_values))
        cpu_values = cpu_values[:min_len]
        mem_values = mem_values[:min_len]

        time_points = np.arange(min_len).reshape(-1, 1)

        # Debug (optional)
        print(f"CPU samples: {len(cpu_values)}, MEM samples: {len(mem_values)}")

        # ✅ Train regression models safely
        cpu_model = LinearRegression().fit(time_points, cpu_values)
        mem_model = LinearRegression().fit(time_points, mem_values)


        # Predict for the next X hours (each hour = 60 minutes)
        future_points = np.arange(len(cpu_values), len(cpu_values) + (60 * hours)).reshape(-1, 1)
        #cpu_pred = cpu_model.predict(future_points)
        #mem_pred = mem_model.predict(future_points)
        cpu_pred = np.clip(cpu_model.predict(future_points), 0, 100)
        mem_pred = np.clip(mem_model.predict(future_points), 0, None)  # memory can't be negative, but can go up


        # 3️⃣ Fetch and analyze logs
        logs = get_recent_logs(container_name)
        error_count = analyze_logs_for_errors(logs)

        # 4️⃣ Determine trends
        cpu_trend = "increasing" if cpu_pred[-1] > cpu_values[-1] else "stable"
        mem_trend = "increasing" if mem_pred[-1] > mem_values[-1] else "stable"

        # 5️⃣ Compute risk
        cpu_risk = min(cpu_pred[-1] / 100 * 0.6, 1.0)
        mem_risk = min(mem_pred[-1] / 100 * 0.3, 1.0)
        log_risk = min(error_count / 20 * 0.1, 1.0)
        total_risk = (cpu_risk + mem_risk + log_risk) * 100

        if total_risk > 80 :
            risk_level = "🔴 CRITICAL"
        elif total_risk > 50:
            risk_level = "🟠 WARNING"
        else:
            risk_level = "🟢 NORMAL"

        # 6️⃣ Optional: send alert
        if total_risk > 50  :
            #send_email_alert("CPU Anomaly: ", "testing")
            #send_email_alert(container_name, total_risk, cpu_pred[-1], mem_pred[-1], error_count)
            #print("gooooooooooooooooood")
            send_email_alert(
                container_name,
                cpu_pred[-1],
                mem_pred[-1],
                error_count,
                total_risk,
                risk_level
            )

        return {
            "container": container_name,
            "prediction_window": f"next {hours} hour(s)",
            "cpu": {
                "current": round(cpu_values[-1], 2),
                "predicted": round(cpu_pred[-1], 2),
                "trend": cpu_trend,
            },
            "memory": {
                "current": round(mem_values[-1], 2),
                "predicted": round(mem_pred[-1], 2),
                "trend": mem_trend,
            },
            "logs": {
                "recent_errors": error_count,
            },
            "overall_risk": f"{risk_level} ({round(total_risk,2)}%)"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# 🔍 Helpers
def get_recent_logs(container_name: str, tail: int = 100):
    """
    Fetch recent logs for a given container from the Docker MCP server.
    Resolves container_name → container_id automatically.
    """
    try:
        # Get list of containers from Docker MCP
        containers_url = "localhost:9000/containers"
        res = requests.get(containers_url, timeout=5)

        if res.status_code != 200:
            print(f"⚠️ Failed to list containers from Docker MCP: {res.status_code}")
            return []

        containers = res.json()

        # Try to find container ID by name
        container_id = None
        for c in containers:
            if (c.get("name") == container_name) or (c.get("Names") and container_name in c.get("Names", [])):
                container_id = c.get("id") or c.get("Id")
                break

        if not container_id:
            print(f"⚠️ No matching container found for name: {container_name}")
            return []

        # Now fetch logs for that container ID
        logs_url = 'localhost:8000/{container_id}/logs'
        log_res = requests.get(logs_url, params={"tail": tail}, timeout=5)

        if log_res.status_code == 200:
            data = log_res.json()
            if "logs" in data:
                return data["logs"]

    except Exception as e:
        print(f"⚠️ Failed to fetch logs from Docker MCP: {e}")

    return []


def analyze_logs_for_errors(logs):
    if not logs:
        return 0
    log_text = str(logs).lower()
    return len(re.findall(r"error|failed|exception|crash|timeout", log_text))


