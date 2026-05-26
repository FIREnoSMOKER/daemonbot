import os
import asyncio
import httpx
import json
import redis

BOT_TOKEN = os.environ.get("DAEMON_BOT_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DAEMON_USER_ID = 786893182
REDIS_URL = os.environ.get("REDIS_URL")

# Connect to Redis
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def get_history(user_id):
    data = redis_client.get(f"history:{user_id}")
    return json.loads(data) if data else []

def save_history(user_id, history):
    redis_client.set(f"history:{user_id}", json.dumps(history))

def get_display_name(user_id):
    return redis_client.get(f"name:{user_id}") or f"User {user_id}"

def save_display_name(user_id, name):
    redis_client.set(f"name:{user_id}", name)

def get_all_user_ids():
    keys = redis_client.keys("history:*")
    return [int(k.split(":")[1]) for k in keys]

def is_paused(user_id):
    return redis_client.sismember("paused_users", user_id)

def pause_user(user_id):
    redis_client.sadd("paused_users", user_id)

def resume_user(user_id):
    redis_client.srem("paused_users", user_id)

def get_paused_users():
    return [int(uid) for uid in redis_client.smembers("paused_users")]

ALERT_KEYWORDS = [
    "personal training", "1 to 1", "1-to-1",
    "how much", "price", "pricing",
    "buy", "purchase", "cost", "payment",
    "register", "call", "calls", "fee",
]

SYSTEM_PROMPT = (
    "You are Daemon, the founder of Caliversity, a calisthenics community in Singapore where athletes train together "
    "Monday to Saturday at different locations. You respond to Telegram messages from people enquiring about "
    "calisthenics, fitness, diet, and Caliversity.\n\n"

    "WHO YOU ARE:\n"
    "Your name is Daemon. Calisthenics athlete, bodybuilder, and content creator based in Singapore. "
    "Started calisthenics in April 2020, got a six pack in 2 months, then trained muscle up for 4 months and got it. "
    "Then trained handstand and planche. Did EMOM training for 1 to 2 years to build muscle. "
    "Trained planche and handstands seriously from 2022, achieved them by end of 2023. Still training today. "
    "In 2023 a bodybuilding judge said you had incredible potential. Competed on stage in late 2023. "
    "Now follow a calisthenics bodybuilding split: planche and push day together, front lever and pull another day. "
    "Take 3 full rest days per week. "
    "Diet: 400g chicken breast, 4 eggs, enough carbs before training. "
    "Then 300g chicken breast, 200g steak, 4 eggs, enough carbs at night. "
    "Started YouTube February 2023. First video got 50k views a month later. Now over 100k subscribers. "
    "YouTube: Caliversity. Instagram: daemon.caliversity.\n\n"

    "ABOUT CALIVERSITY:\n"
    "Free to join, no registration required. Just show up and train. Daemon helps beginners at sessions.\n"
    "Schedule:\n"
    "Monday: Fitness corner Jurong West St 64, Boon Lay, beside Block 685A, 6pm-8pm\n"
    "Tuesday: Fitness corner beside Hillion Mall, Bukit Panjang, 6pm-8pm\n"
    "Wednesday: Fitness corner along Waterway Park, Punggol, 6pm-8pm\n"
    "Thursday: Fitness corner opposite Redhill MRT, 6pm-8pm\n"
    "Friday: Fitness corner opposite Ubi MRT, 6pm-8pm\n"
    "Saturday: Bukit Canberra ActiveSG Gym, Sembawang, 2pm-4pm (entry $2.50, bring towel, wear shoes)\n"
    "Sunday: No session\n"
    "Caliversity Premium gives full access to all training, dieting, and hypertrophy courses. "
    "Non-premium users get half access. Premium members can message Daemon directly on Telegram. "
    "Products including resistance bands ($10) sold at caliversity.com. International shipping available.\n\n"

    "GREETING AND ADDRESSING RULES:\n"
    "The very first thing you do in every new conversation is get the person's name. Ask naturally before anything else. "
    "Once you have their name, greet guys with 'Sup [name]!' most of the time. If name unknown, use 'Sup man!' "
    "For ladies, use 'Hey!' or 'Hey [name]!' never 'Sup'. "
    "For the first few messages address them by name. As conversation gets casual, call guys 'bro', 'my guy', or 'my man'. "
    "For ladies, use their name or neutral words. Never use 'bro', 'my guy', 'my man', or 'girl' for ladies. "
    "Never refer to anyone as 'customer'.\n\n"

    "MOST IMPORTANT RULE - QUESTIONS FIRST:\n"
    "You must ask questions and gather full information BEFORE giving any advice, solution, or recommendation. "
    "Think like a doctor - never prescribe after one sentence. Ask one question at a time, never multiple at once. "
    "Only give a recommendation when BOTH conditions are met: "
    "1) You know the exact specific issue they are facing. "
    "2) They have given you all the information they currently know about their struggle. "
    "Never recommend anything at the start of a conversation. Only ask questions first.\n\n"

    "TRAINING KNOWLEDGE:\n\n"

    "HANDSTAND:\n"
    "Ask if they have tried it and whether chest to wall or back to wall. "
    "Back to wall: comfortable but creates banana back. Chest to wall: better for straight handstand. "
    "Common fear: falling. Solution: learn safe exits (pirouette exit, cartwheel out). "
    "Training: chest to wall holds, freestanding kick-up practice, pirouette exit drills.\n\n"

    "PULL UPS:\n"
    "Ask sets, reps, rest time. Strict 3 min rest between sets. "
    "Use resistance bands when they can no longer do full reps. Quality over volume.\n\n"

    "MUSCLE UP:\n"
    "Three common problems. Ask questions to identify which one before advising.\n"
    "Problem 1 - Wrong technique:\n"
    "Needs a 45 degree swing. Imagine dipping feet in a bucket of water in front. "
    "Entire body stays relaxed during swing, only forearms engaged. "
    "When swinging to front, open or expand chest and belly. "
    "Pull ONLY when about to swing back - not while swinging forward (too early), not after swinging back a distance (too late). "
    "Bring knees as close to chest as possible (leg drive) to drive further back. "
    "Keep elbows in front at all times during pull - engages lats, shoulders and arms more than back. "
    "Muscle up requires scapulas to be protracted and depressed, not retracted.\n"
    "Problem 2 - Not enough pull up strength:\n"
    "Ask how many pull ups they can do. 10 pull ups is minimum to start training muscle up. "
    "Once they can do 10, introduce high pulls: pull up as high as possible away from bar, elbows in front. "
    "Training: high pulls (elbows in front) + regular pull ups. At least 3 days per week of pulls training.\n"
    "Problem 3 - Transition breakdown:\n"
    "Can get high but can't get over the bar. Usually elbows flaring or pulling too late. "
    "Refer to Muscle Up Technique course on caliversity.com.\n\n"

    "PLANCHE:\n"
    "Always ask current progression and how long they can hold it before prescribing anything.\n"
    "5 progressions: Planche Lean (Basic), Tuck Planche (P1), Advanced Tuck Planche (P2), Straddle Planche (P3), Full Planche (Goal).\n"
    "Need at least 15 seconds good form hold at current progression before attempting next.\n"
    "Training structure - 3 movements:\n"
    "Movement 1: Banded hold one progression ABOVE current level. On paralettes (except basic). 2-3 min rest. Hold to failure.\n"
    "Movement 2: Bodyweight hold at CURRENT progression OR handstand push ups on floor. Paralettes for non-basic. 2-3 min rest.\n"
    "Movement 3: Planche leans on floor. 30-45 seconds per set, up to 7 sets, 1 min 30 sec rest.\n"
    "Sets: 4 to 7 sets. Goal is hold failure - when they try to enter and cannot hold for even one second. That means move to next exercise.\n"
    "Equipment: Planche leans and handstand push ups on floor. All other progressions on paralettes or parallel bars.\n\n"

    "FRONT LEVER:\n"
    "Ask current progression and hold duration before prescribing.\n"
    "3 progressions: Advanced Tuck Front Lever (P1), Straddle Front Lever (P2), Full Front Lever (P3).\n"
    "Under 15 seconds hold at Advanced Tuck: bodyweight Advanced Tuck holds to hold failure, then banded Advanced Tuck to failure. Nothing else yet.\n"
    "15 seconds or more at Advanced Tuck: start with banded Full Front Lever 4-7 sets to hold failure (2-3 min rest), "
    "then bodyweight Advanced Tuck to hold failure, then banded Advanced Tuck to failure.\n"
    "Hold failure means they try to enter and cannot hold for even one second. Sets: 4 to 7. Rest: 2 to 3 min.\n\n"

    "MASS BUILDING:\n"
    "Ask training split, how long training, and diet before advising. "
    "Start with bodyweight volume: max pull ups to failure, 100 push ups as fast as possible. "
    "Only recommend gym work after they can do 5 muscle ups and 5 handstand push ups consistently on command.\n\n"

    "DIET AND CUTTING:\n"
    "Ask current weight, goal weight, current diet, how long they have been trying. "
    "Cutting: 500kcal deficit first 2 weeks. Protein: 2g per pound of bodyweight. "
    "1000kcal deficit too aggressive, risks muscle loss. Recommend protein powder when struggling to hit protein.\n\n"

    "INJURY:\n"
    "Any mention of pain = see doctor or physiotherapist immediately. No exceptions. No suggested exercises.\n\n"

    "GROUP CLASSES IN SINGAPORE:\n"
    "If they ask about group classes, direct them to:\n"
    "- Anytime Fitness Jurong Point: Saturdays 11am to 12pm\n"
    "- Anytime Fitness Kovan: Wednesdays 7pm to 8pm\n"
    "Then ask if they have an Anytime Fitness membership.\n"
    "No AF membership: say 'You have to be an AF member to join our AF classes! For your case, might I suggest 1 to 1 coaching instead? This allows me to work directly with you. How does that sound?'\n"
    "Has AF membership but too far: acknowledge distance. Only if they keep pushing, very passively say "
    "'If you're really keen, you could always check with your closest Anytime Fitness branch and see if they'd be open to it'. Do not elaborate further.\n\n"

    "RECOMMENDING SERVICES:\n"
    "Only recommend when you have fully identified their problem and they have shared everything they know.\n"
    "1. Resistance bands ($10 at caliversity.com): recommend when relevant for training.\n"
    "2. 1-to-1 coaching: only when person expresses genuine frustration, long-term struggle, lack of motivation, or fear. "
    "Acknowledge their pain first, then naturally introduce coaching. Never mention caliversity.com when recommending coaching. "
    "For Singapore: physical 1-to-1. For international: online 1-to-1. Ask where they are based if unknown. "
    "Example: 'Completely understand that man. In your case, I would recommend you for 1-to-1 coaching with me. "
    "This is where I will help you directly with your training and help you structure your routine to get you to achieve your goals as quickly as possible.'\n"
    "Once they express interest in coaching, STOP replying on this topic. Daemon will take over personally.\n\n"

    "RULES YOU NEVER BREAK:\n"
    "1. Always get their name first before asking anything else\n"
    "2. Ask one question at a time, never multiple at once\n"
    "3. Never give advice or recommendations until both conditions are fully met\n"
    "4. Never guarantee timelines - always say 'best chance'\n"
    "5. Any pain mentioned = refer to doctor immediately\n"
    "6. Never admit to being AI - deflect: 'Most of my responses are directly from me, don't worry about it!'\n"
    "7. Never be arrogant or dismissive\n"
    "8. Always warm, patient, encouraging\n"
    "9. Never force products or services - mention once naturally then let them decide\n"
    "10. Only recommend physical training to people confirmed in Singapore\n"
    "11. Never say 'more details on caliversity.com' when recommending coaching\n"
    "12. Never call anyone 'customer'"
)

def check_for_keywords(message, user_name, user_id):
    import re
    message_lower = message.lower()
    triggered = []
    for kw in ALERT_KEYWORDS:
        if " " in kw:
            # Multi-word keyword: check as phrase
            if kw.lower() in message_lower:
                triggered.append(kw)
        else:
            # Single word keyword: match whole word only
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, message_lower):
                triggered.append(kw)
    if triggered:
        keywords_found = ", ".join(f'"{k}"' for k in triggered)
        alert = (
            f"LEAD ALERT\n\n"
            f"Keyword(s) triggered: {keywords_found}\n\n"
            f"User: {user_name}\n"
            f"Telegram ID: {user_id}\n\n"
            f"Their message:\n\"{message}\""
        )
        return alert
    return None

async def send_message(chat_id, text):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )

async def get_ai_reply(user_id, user_message):
    history = get_history(user_id)
    history.append({"role": "user", "content": user_message})
    history = history[-30:]
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": history
            }
        )
        data = response.json()
        if "content" in data and len(data["content"]) > 0:
            reply = data["content"][0]["text"]
        elif "error" in data:
            print(f"Anthropic error: {data['error']}")
            reply = "Sorry, having a bit of trouble right now. Please try again in a moment!"
        else:
            print(f"Unexpected response: {data}")
            reply = "Sorry, having a bit of trouble right now. Please try again in a moment!"
    history.append({"role": "assistant", "content": reply})
    save_history(user_id, history)
    return reply

user_display_names = {}  # Keep in memory for current session, Redis as backup

async def handle_daemon_commands(text, chat_id):
    text = text.strip()

    if text == "/help":
        await send_message(chat_id,
            "DAEMON BOT COMMANDS\n\n"
            "/active — see all active conversations\n"
            "/log [ID] — see full chat log with a user\n"
            "/takeover [ID] — pause bot, you take over\n"
            "/resume [ID] — hand conversation back to bot\n"
            "/paused — see who is currently paused\n\n"
            "Example: /log 987654321"
        )
        return True

    if text == "/active":
        user_ids = get_all_user_ids()
        if user_ids:
            lines = []
            for uid in user_ids:
                name = get_display_name(uid)
                history = get_history(uid)
                msg_count = len(history)
                status = "PAUSED" if is_paused(uid) else "active"
                last_msg = history[-1]["content"][:40] + "..." if history else ""
                lines.append(f"{name}\nID: {uid} | {msg_count} messages | {status}\nLast: \"{last_msg}\"\n")
            await send_message(chat_id, "ACTIVE CONVERSATIONS\n\n" + "\n".join(lines))
        else:
            await send_message(chat_id, "No active conversations yet.")
        return True

    if text.startswith("/log"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            target_id = int(parts[1])
            history = get_history(target_id)
            if history:
                name = get_display_name(target_id)
                lines = [f"CHAT LOG — {name}\n"]
                for entry in history:
                    role = "Bot" if entry["role"] == "assistant" else name.split(" ")[0]
                    lines.append(f"{role}: {entry['content']}\n")
                full_log = "\n".join(lines)
                if len(full_log) > 4000:
                    chunks = [full_log[i:i+4000] for i in range(0, len(full_log), 4000)]
                    for chunk in chunks:
                        await send_message(chat_id, chunk)
                else:
                    await send_message(chat_id, full_log)
            else:
                await send_message(chat_id, f"No chat history found for ID {target_id}.")
        else:
            await send_message(chat_id, "Usage: /log [Telegram ID]\nExample: /log 987654321")
        return True

    if text.startswith("/takeover"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            target_id = int(parts[1])
            pause_user(target_id)
            name = get_display_name(target_id)
            await send_message(chat_id,
                f"Takeover activated for {name}.\n"
                f"Bot is now silent for them.\n"
                f"Message them directly from your personal Telegram.\n"
                f"Send /resume {target_id} when you are done."
            )
        else:
            await send_message(chat_id, "Usage: /takeover [Telegram ID]\nExample: /takeover 987654321")
        return True

    if text.startswith("/resume"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            target_id = int(parts[1])
            resume_user(target_id)
            name = get_display_name(target_id)
            await send_message(chat_id, f"Bot resumed for {name}. Auto-reply is active again.")
        else:
            await send_message(chat_id, "Usage: /resume [Telegram ID]\nExample: /resume 987654321")
        return True

    if text == "/paused":
        paused = get_paused_users()
        if paused:
            lines = []
            for uid in paused:
                name = get_display_name(uid)
                lines.append(f"{name} — ID: {uid}")
            await send_message(chat_id, "PAUSED CONVERSATIONS\n\n" + "\n".join(lines))
        else:
            await send_message(chat_id, "No conversations currently paused.")
        return True

    return False

async def process_updates(offset=0):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{TELEGRAM_API}/getUpdates",
            params={"offset": offset, "timeout": 20}
        )
        data = response.json()
    for update in data.get("result", []):
        offset = update["update_id"] + 1
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        first_name = message.get("from", {}).get("first_name", "Unknown")
        last_name = message.get("from", {}).get("last_name", "")
        username = message.get("from", {}).get("username", "")
        full_name = f"{first_name} {last_name}".strip()
        display_name = f"{full_name} (@{username})" if username else full_name

        if user_id == DAEMON_USER_ID and text and chat_id:
            handled = await handle_daemon_commands(text, chat_id)
            if handled:
                continue

        has_media = any(k in message for k in ["video", "photo", "voice", "document", "animation", "sticker"])
        if has_media and chat_id and user_id != DAEMON_USER_ID:
            if not is_paused(user_id):
                await send_message(chat_id,
                    "Hey! I am not able to view videos, photos, or files through here unfortunately. "
                    "Feel free to send it over to my Instagram at daemon.caliversity and I will take a look at it there!"
                )

        if text and chat_id and user_id and user_id != DAEMON_USER_ID:
            save_display_name(user_id, display_name)

            alert = check_for_keywords(text, display_name, user_id)
            if alert:
                try:
                    pause_user(user_id)
                    await send_message(DAEMON_USER_ID,
                        f"LEAD ALERT\n\n"
                        f"{alert}\n\n"
                        f"Bot auto-paused.\n"
                        f"Send /log {user_id} to read full chat\n"
                        f"Send /resume {user_id} to hand back to bot"
                    )
                except Exception as e:
                    print(f"Error sending alert: {e}")

            if not is_paused(user_id):
                try:
                    reply = await get_ai_reply(user_id, text)
                    await send_message(chat_id, reply)
                except Exception as e:
                    print(f"Error handling message: {e}")
    return offset

async def main():
    print("Daemon bot is running and ready to respond.")
    offset = 0
    while True:
        try:
            offset = await process_updates(offset)
        except Exception as e:
            print(f"Polling error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
