# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — MASTER ORCHESTRATOR
Runs the 24-agent pipeline: MASTER_SUPERVISOR → SCHEDULER → ... → WATCHDOG
Usage: python main.py --type daily --date 2026-10-04
       python main.py --type weekly --date 2026-10-05
       python main.py --type monthly --date 2026-10-31
"""

import argparse, json, os, sys, logging, traceback
from datetime import datetime
import pytz
from config.workflow import WORKFLOW_ORDER, MASTER_RULE
from config.sources import TIER_1_SOURCES

# Import all 24 agents dynamically
def load_agent(agent_id):
    module = __import__(f'agents.{agent_id}', fromlist=['Agent'])
    return module.Agent

def run_pipeline(job_type, job_date):
    tz = pytz.timezone("Asia/Kolkata")
    job_id = f"{job_type}_{job_date}"
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', handlers=[logging.FileHandler(f"logs/{job_id}.log"), logging.StreamHandler()])
    logging.info(f"=== START PIPELINE {job_id} ===")
    logging.info(f"MASTER RULE: {MASTER_RULE}")
    
    # Check duplicate
    if os.path.exists(f"data/jobs/{job_id}.json"):
        with open(f"data/jobs/{job_id}.json") as jf:
            j = json.load(jf)
            if j.get("status") == "COMPLETE":
                logging.info(f"Job {job_id} already COMPLETE — skipping duplicate")
                return
    
    # Initialize context
    context = {"job_id": job_id, "job_type": job_type, "job_date": job_date, "tz": "Asia/Kolkata", "window": f"{job_date} 06:00 IST"}
    os.makedirs("data/jobs", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    last_success = None
    # Try to resume from last success if exists
    if os.path.exists(f"data/jobs/{job_id}.json"):
        with open(f"data/jobs/{job_id}.json") as jf:
            j = json.load(jf)
            last_success = j.get("last_success_stage")
    
    start_idx = 0
    if last_success:
        try:
            start_idx = WORKFLOW_ORDER.index(last_success) + 1
            logging.info(f"Resuming from {last_success} -> next is {WORKFLOW_ORDER[start_idx]}")
        except:
            start_idx = 0
    
    # Execute each agent in order
    for agent_id in WORKFLOW_ORDER[start_idx:]:
        try:
            logging.info(f"--> Running {agent_id}")
            Agent = load_agent(agent_id)
            agent = Agent(job_id, job_type, context)
            context = agent.run()
            # Save checkpoint
            with open(f"data/jobs/{job_id}.json", 'w') as jf:
                json.dump({"job_id": job_id, "job_type": job_type, "job_date": job_date, "status": "RUNNING", "last_success_stage": agent_id, "updated": datetime.now(tz).isoformat()}, jf, indent=2)
        except Exception as e:
            logging.error(f"Agent {agent_id} failed: {e}")
            traceback.print_exc()
            # Retry via watchdog logic (3x)
            for retry in range(3):
                try:
                    logging.info(f"Retrying {agent_id} attempt {retry+1}")
                    Agent = load_agent(agent_id)
                    agent = Agent(job_id, job_type, context)
                    context = agent.run()
                    break
                except Exception as re:
                    if retry == 2:
                        logging.error(f"Persistent failure in {agent_id}, escalating to WATCHDOG")
                        # Send alert to admin via Telegram
                        try:
                            import requests
                            bot = os.getenv("TELEGRAM_BOT_TOKEN", "8263302068:AAG1tPtIUfq08dgfoijtsoOsrnhWPBeoE78")
                            chat = os.getenv("ADMIN_ID", "1138783169")
                            requests.post(f"https://api.telegram.org/bot{bot}/sendMessage", data={"chat_id": chat, "text": f"🚨 WATCHDOG ALERT: {job_id} failed at {agent_id} — {str(e)[:500]}"})
                        except: pass
                        raise
            else:
                continue
    
    # Mark complete
    with open(f"data/jobs/{job_id}.json", 'w') as jf:
        json.dump({"job_id": job_id, "job_type": job_type, "job_date": job_date, "status": "COMPLETE", "last_success_stage": WORKFLOW_ORDER[-1], "completed": datetime.now(tz).isoformat()}, jf, indent=2)
    logging.info(f"=== PIPELINE {job_id} COMPLETE ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["daily", "weekly", "monthly"], required=True)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD in Asia/Kolkata")
    args = parser.parse_args()
    run_pipeline(args.type, args.date)
