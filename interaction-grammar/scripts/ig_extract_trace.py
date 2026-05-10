import sqlite3
import json
import argparse
import struct
from pathlib import Path

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

    events = []

    # Extract robot events
    if robot_topic in topic_map:
        cursor.execute("SELECT timestamp, data FROM messages WHERE topic_id = ?", (topic_map[robot_topic],))
        for ts, blob in cursor.fetchall():
            val = extract_string(blob)
            events.append({
                "t": ts / 1e9,
                "prim": "α",
                "agent": "robot_1",
                "channel": "speech",
                "object": val
            })

    # Extract human events
    if human_topic in topic_map:
        cursor.execute("SELECT timestamp, data FROM messages WHERE topic_id = ?", (topic_map[human_topic],))
        for ts, blob in cursor.fetchall():
            val = extract_string(blob)
            if val == "human_speaking_start":
                events.append({
                    "t": ts / 1e9,
                    "prim": "σ",
                    "agent": "human_1",
                    "channel": "speech"
                })
            elif val == "human_speaking_end":
                events.append({
                    "t": ts / 1e9,
                    "prim": "ρ",
                    "agent": "human_1",
                    "channel": "speech"
                })
            else:
                events.append({
                    "t": ts / 1e9,
                    "prim": "α",
                    "agent": "human_1",
                    "channel": "speech",
                    "object": val
                })

    # Sort by timestamp
    events.sort(key=lambda x: x["t"])
    
    # Relative timestamps (optional, but requested in some IG contexts. 
    # However, the auditor handles absolute if needed. 
    # Let's keep them absolute but maybe offset by first event for readability).
    if events:
        t0 = events[0]["t"]
        # Wait, the spec doesn't say relative. I'll keep them absolute as stored.
        # But for IG traces, starting at 0 is often better.
        # Let's see what the examples use.
        pass

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    print(f"Extracted {len(events)} events to {args.out}")

if __name__ == "__main__":
    main()
