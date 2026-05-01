import requests, os, json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("/home/ubuntu/24-7-Bot/.env")
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def get_restart_info():
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
    try:
        # Get server details
        url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers"
        response = requests.get(url, headers=headers)
        data = response.json()

        if data["status"] == "success":
            server = data["data"]["gameserver"]
            status = server["status"]

            # Nitrado stores schedules in a separate endpoint usually,
            # but we can see the current uptime and basic status here.
            print(f"Server Status: {status}")

            # Check for scheduled tasks
            task_url = f"https://api.nitrado.net/services/{SERVICE_ID}/tasks"
            task_response = requests.get(task_url, headers=headers)
            tasks = task_response.json()

            if tasks["status"] == "success":
                print("\nScheduled Tasks (Restarts):")
                found_restart = False
                for task in tasks["data"]["tasks"]:
                    if "restart" in task["action"].lower():
                        print(f"- Task: {task['action']}")
                        print(
                            f"  Schedule: {task['hour']}:{task['minute']} (Day: {task['weekday']})"
                        )
                        found_restart = True
                if not found_restart:
                    print("- No scheduled restart tasks found in Nitrado API.")
            else:
                print("Could not fetch scheduled tasks.")
        else:
            print(f"Error fetching server data: {data.get('message')}")

    except Exception as e:
        print(f"Request error: {e}")


if __name__ == "__main__":
    get_restart_info()
