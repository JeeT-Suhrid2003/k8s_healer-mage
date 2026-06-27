import os
import subprocess
import json
import requests
from kubernetes import client, config, watch

# Configuration
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520424721253011518/p56jdJMwCpYDeN63zbOEQJDwlkhLt_BRLzc18QxFmywW21efncXppd00aY75zXA-Ylds"
DEPLOYMENT_NAME = "broken-nginx"
NAMESPACE = "default"

# Initialize K8s Client
try:
    config.load_kube_config() # Loads from ~/.kube/config
except:
    config.load_incluster_config()

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

def send_discord_alert(message):
    payload = {"content": f"🚨 **K8s Self-Healer Alert** 🚨\n{message}"}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def run_k8sgpt_analysis():
    """Runs k8sgpt analyze and safely handles the output."""
    try:
        result = subprocess.run(
            ["k8sgpt", "analyze", "--explain","-f","Pod","--namespace","default", "--output", "json","-b","google"],
            capture_output=True, text=True
        )
        
        # Debugging prints to catch the real error in your terminal
        if result.stderr:
            print(f"⚠️ K8sGPT Stderr Output:\n{result.stderr}")
            
        stdout_clean = result.stdout.strip()
        if not stdout_clean:
            print("❌ K8sGPT returned an empty stdout.")
            return None
            
        # Try to parse the JSON
        return json.loads(stdout_clean)
            
    except json.JSONDecodeError:
        print(f"❌ Failed to parse JSON. Raw stdout was:\n{result.stdout}")
        return None
    except Exception as e:
        print(f"Error executing K8sGPT command: {e}")
        return None

def trigger_rollback():
    """Automatically rolls back the broken deployment to the previous revision."""
    print(f"Attempting rollback for deployment {DEPLOYMENT_NAME}...")
    try:
        # Simple rollback strategy: Read history or just undo
        # In a real pipeline, you'd apply a known good manifest, 
        # but for this demo, we use kubectl rollout undo via subprocess
        subprocess.run(["kubectl", "rollout", "undo", f"deployment/{DEPLOYMENT_NAME}"], check=True)
        send_discord_alert(f"✅ Successfully triggered automated rollback for `deployment/{DEPLOYMENT_NAME}`.")
    except Exception as e:
        send_discord_alert(f"❌ Failed to execute automated rollback: {e}")

def watch_cluster():
    print("Monitoring cluster for pod failures...")
    w = watch.Watch()
    
    # Watch for Pod events
    for event in w.stream(v1.list_namespaced_pod, namespace=NAMESPACE):
        pod = event['object']
        status = pod.status
        
        # Check container statuses for waiting errors
        if status.container_statuses:
            for container_status in status.container_statuses:
                waiting = container_status.state.waiting
                if waiting and waiting.reason in ["ImagePullBackOff", "CrashLoopBackOff"]:
                    print(f"Detected failure in {pod.metadata.name}: {waiting.reason}")
                    
                    # 1. Run AI Diagnostics
                    analysis = run_k8sgpt_analysis()
                    explanation = "Could not parse K8sGPT explanation."
                    
                    if analysis and analysis.get("results"):
                        # Extract the failure message from K8sGPT results
                        explanation = analysis["results"][0].get("error", [{}])[0].get("Text", "No specific error text found.")
                    
                    # 2. Alert Discord
                    alert_msg = f"**Pod:** {pod.metadata.name}\n**Status:** {waiting.reason}\n**AI Analysis:** {explanation}"
                    send_discord_alert(alert_msg)
                    
                    # 3. Heal (Rollback)
                    trigger_rollback()
                    w.stop() # Stop watching for this demo run
                    return

if __name__ == "__main__":
    watch_cluster()