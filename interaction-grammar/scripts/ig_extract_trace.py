import sqlite3
import json
import argparse
import struct
from pathlib import Path

# Map of raw bag labels to canonical IG labels
EVENT_MAP = {
    "recipient_acknowledges_delivery": "user_acknowledges_delivery",
    "user_acknowledges_delivery": "user_acknowledges_delivery",
    "robot_announces_delivery": "robot_announces_delivery",
    "robot_confirms_delivery": "robot_confirms_delivery",
    "robot_final_confirmation": "robot_confirms_delivery",
    "start": "start",
    "robot_prompts_user": "robot_prompts_user",
    "user_responds_to_prompt": "user_responds_to_prompt",
    "user_acknowledges_intent": "user_acknowledges_intent",
    "robot_acknowledges_interruption": "robot_acknowledges_interruption",
    "robot_stops_speaking": "robot_stops_speaking",
    "robot_provides_guidelines": "robot_provides_guidelines",
    "user_interrupts_by_speaking": "user_interrupts_by_speaking",
    "user_finishes_speaking": "user_finishes_speaking",
}

def extract_string(blob):
    if len(blob) < 12:
        return ""
    # CDR header is 4 bytes
    # Length is the next 4 bytes (little-endian)
    length = struct.unpack('<I', blob[4:8])[0]
    # String follows (without null terminator)
    return blob[8:8+length].decode('utf-8').strip('\x00')

def main():
    parser = argparse.ArgumentParser(description="Extract IG trace from ROS 2 bag")
    parser.add_argument("--bag", required=True, help="Path to the .db3 file")
    parser.add_argument("--out", required=True, help="Output .trace.jsonl path")
    args = parser.parse_args()

    conn = sqlite3.connect(args.bag)
    cursor = conn.cursor()

    # Map topics
    cursor.execute("SELECT id, name FROM topics")
    topic_map = {row[1]: row[0] for row in cursor.fetchall()}

    robot_topic = "/interaction/robot_event"
    human_topic = "/interaction/human_event"
    system_topic = "/interaction/system_event"

    events = []

    # Extract robot events
    if robot_topic in topic_map:
        cursor.execute("SELECT timestamp, data FROM messages WHERE topic_id = ?", (topic_map[robot_topic],))
        for ts, blob in cursor.fetchall():
            val = extract_string(blob)
            normalized_val = EVENT_MAP.get(val, val)
            events.append({
                "t": ts / 1e9,
                "prim": "α",
                "agent": "robot_1",
                "channel": "speech",
                "object": normalized_val
            })

    # Extract human events
    if human_topic in topic_map:
        cursor.execute("SELECT timestamp, data FROM messages WHERE topic_id = ?", (topic_map[human_topic],))
        for ts, blob in cursor.fetchall():
            val = extract_string(blob)

            # If the label is in our canonical map, it's a semantic act (alpha)
            if val in EVENT_MAP:
                normalized_val = EVENT_MAP[val]
                events.append({
                    "t": ts / 1e9,
                    "prim": "α",
                    "agent": "human_1",
                    "channel": "speech",
                    "object": normalized_val
                })
            # Otherwise, check if it's a raw speaking marker (sigma/rho)
            elif val in ["human_speaking_start", "user_starts_speaking"]:
                events.append({
                    "t": ts / 1e9,
                    "prim": "σ",
                    "agent": "human_1",
                    "channel": "speech"
                })
            elif val in ["human_speaking_end", "user_finishes_speaking"]:
                events.append({
                    "t": ts / 1e9,
                    "prim": "ρ",
                    "agent": "human_1",
                    "channel": "speech"
                })
            else:
                # Fallback for any other labels
                events.append({
                    "t": ts / 1e9,
                    "prim": "α",
                    "agent": "human_1",
                    "channel": "speech",
                    "object": val
                })

    # Extract system events
    if system_topic in topic_map:
        cursor.execute("SELECT timestamp, data FROM messages WHERE topic_id = ?", (topic_map[system_topic],))
        for ts, blob in cursor.fetchall():
            val = extract_string(blob)
            normalized_val = EVENT_MAP.get(val, val)
            events.append({
                "t": ts / 1e9,
                "prim": "α",
                "agent": "system",
                "channel": "system",
                "object": normalized_val
            })

    # Sort by timestamp
    events.sort(key=lambda x: x["t"])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    print(f"Extracted {len(events)} events to {args.out}")

if __name__ == "__main__":
    main()
