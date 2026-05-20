import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
import base64
from zoneinfo import ZoneInfo
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
import time
import schedule
import re

BARCA_SCHEDULE_URL = "https://www.fcbarcelona.com/en/football/first-team/schedule"

GMAIL_ADDRESS = "fadisupp20@gmail.com"
GMAIL_APP_PASSWORD = "vfnt xrdk owkz pmpv"
TEST_MODE = False
HERO_IMAGE_URL = "https://www.fcbarcelona.com/fcbarcelona/photo/2025/01/21/8a3b2560-3de6-4b9f-b281-9cdb0f5c540b/16-Bowl.jpg"

RECIPIENTS = [
    "yarafa1806@gmail.com",
    "juliete.mattar08@gmail.com",
    "shuhaiber.fadi@gmail.com",
    "tofiqkh@gmail.com",
    "tamertaktak123@hotmail.co.il",
    "a2boulus@gmail.com",
    "jacob.sheheber@gmail.com",
    "mikha.9595@gmail.com",
    "wissamkhshiboun@gmail.com",
    "toniee_842@hotmail.com",
    "fadi_sh11@hotmail.com"
]

def build_ics_content(result: dict) -> str:
    year = datetime.now().year
    kickoff_dt = datetime.strptime(
        f"{result['matched_date']} {year} {result['time_spain']}",
        "%a %d %b %Y %H:%M"
    )
    kickoff_dt = kickoff_dt.replace(tzinfo=ZoneInfo("Europe/Madrid"))
    kickoff_dt = kickoff_dt.astimezone(ZoneInfo("Asia/Jerusalem"))
    end_dt = kickoff_dt + timedelta(hours=2)
    dtstamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    dtstart = kickoff_dt.strftime("%Y%m%dT%H%M%S")
    dtend = end_dt.strftime("%Y%m%dT%H%M%S")
    uid = f"barcelona-match-{kickoff_dt.strftime('%Y%m%dT%H%M%S')}@sotiris-automation"
    summary = result["fixture"]
    location = result["stadium"] or "TBD"
    description = (
        f"Competition: {result['competition']}\\n"
        f"Stage: {result['stage'] or 'N/A'}\\n"
        f"Source: {result['source']}"
    )
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SOTIRIS Automation Company//FC Barcelona Alert//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART;TZID=Asia/Jerusalem:{dtstart}
DTEND;TZID=Asia/Jerusalem:{dtend}
SUMMARY:{summary}
LOCATION:{location}
DESCRIPTION:{description}
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:FC Barcelona match starts in 30 minutes
END:VALARM
END:VEVENT
END:VCALENDAR
"""
    return ics


def get_countdown(date_str, time_str):
    try:
        year = datetime.now().year
        kickoff = datetime.strptime(
            f"{date_str} {year} {time_str}",
            "%a %d %b %Y %H:%M"
        )
        kickoff = kickoff.replace(tzinfo=ZoneInfo("Europe/Madrid"))
        kickoff = kickoff.astimezone(ZoneInfo("Asia/Jerusalem"))
        now = datetime.now(ZoneInfo("Asia/Jerusalem"))
        delta = kickoff - now
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    except:
        return ""


def get_team_logo_urls(home_team: str, away_team: str) -> tuple[str, str]:

    def normalize_name(team_name: str) -> str:
        return (
            team_name.lower()
            .replace("fc ", "")
            .replace("cf ", "")
            .replace(".", "")
            .replace(",", "")
            .strip()
        )

    def get_aliases(team_name: str) -> list[str]:
        raw = team_name.strip()
        norm = normalize_name(raw)

        alias_map = {
            "fc barcelona": ["Barcelona", "FC Barcelona", "Barca", "Barça"],
            "barcelona": ["Barcelona", "FC Barcelona", "Barca", "Barça"],
            "sevilla": ["Sevilla", "Sevilla FC"],
            "sevilla fc": ["Sevilla", "Sevilla FC"],
            "real madrid": ["Real Madrid", "Real Madrid CF"],
            "atletico madrid": ["Atletico Madrid", "Atlético Madrid", "Atletico de Madrid"],
            "athletic club": ["Athletic Club", "Athletic Bilbao"],
            "psg": ["Paris Saint-Germain", "PSG"],
            "paris saint-germain": ["Paris Saint-Germain", "PSG"],
            "inter": ["Inter", "Internazionale", "Inter Milan"],
            "ac milan": ["AC Milan", "Milan"],
            "manchester united": ["Manchester United", "Man United"],
            "manchester city": ["Manchester City", "Man City"],
            "alavés": ["Alavés", "Alaves", "Deportivo Alavés", "Deportivo Alaves"],
            "alaves": ["Alavés", "Alaves", "Deportivo Alavés", "Deportivo Alaves"],
            "deportivo alavés": ["Alavés", "Alaves", "Deportivo Alavés", "Deportivo Alaves"],
        }

        aliases = [raw]

        if raw.lower() in alias_map:
            aliases.extend(alias_map[raw.lower()])
        elif norm in alias_map:
            aliases.extend(alias_map[norm])
        else:
            aliases.extend([
                raw.replace("FC ", "").replace("CF ", "").strip(),
                norm.title(),
            ])

        seen = set()
        clean_aliases = []
        for a in aliases:
            if a and a.lower() not in seen:
                seen.add(a.lower())
                clean_aliases.append(a)

        return clean_aliases

    def fetch_team_logo(team_name: str) -> str:
        aliases = get_aliases(team_name)

        for alias in aliases:
            try:
                url = "https://www.thesportsdb.com/api/v1/json/123/searchteams.php"
                response = requests.get(url, params={"t": alias}, timeout=20)
                response.raise_for_status()

                data = response.json()
                teams = data.get("teams") or []
                print(f"[LOGO DEBUG] team_name={team_name} | alias={alias} | found={len(teams)}")

                if not teams:
                    continue

                for team in teams:
                    # Only accept soccer teams
                    sport = (team.get("strSport") or "").lower()
                    if sport and sport != "soccer":
                        print(f"[LOGO DEBUG] Skipping non-soccer: {team.get('strTeam')} ({sport})")
                        continue

                    badge = (team.get("strBadge") or "").strip()
                    team_name_result = (team.get("strTeam") or "").lower()
                    alias_lower = alias.lower()

                    # Make sure returned team name actually matches what we searched
                    name_match = (
                        alias_lower in team_name_result or
                        team_name_result in alias_lower or
                        any(word in team_name_result for word in alias_lower.split() if len(word) > 3)
                    )

                    if name_match:
                        print(f"[LOGO DEBUG] alias={alias} | matched={team.get('strTeam')} | badge={badge}")
                        if badge.startswith("http"):
                            return badge

            except Exception as e:
                print(f"[LOGO DEBUG] alias={alias} | error={e}")
                continue

        return ""

    home_logo = fetch_team_logo(home_team)
    away_logo = fetch_team_logo(away_team)
    return home_logo, away_logo


def get_page_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def to_israel_time(date_str: str, time_str: str) -> str:
    try:
        year = datetime.now().year
        dt_spain = datetime.strptime(f"{date_str} {year} {time_str}", "%a %d %b %Y %H:%M")
        dt_spain = dt_spain.replace(tzinfo=ZoneInfo("Europe/Madrid"))
        dt_israel = dt_spain.astimezone(ZoneInfo("Asia/Jerusalem"))
        return dt_israel.strftime("%H:%M")
    except Exception:
        return time_str


def file_to_base64(path: str) -> str | None:
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def find_today_match_from_official_site():
    html = get_page_html(BARCA_SCHEDULE_URL)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    now = datetime.now()

    date_patterns = [
        now.strftime("%a %d %b"),
        now.strftime("%a %-d %b") if os.name != "nt" else None,
    ]
    date_patterns = [p for p in date_patterns if p]

    for date_str in date_patterns:
        pattern = rf"{re.escape(date_str)}\s+(\d{{1,2}}:\d{{2}}|KO:\s*\d{{1,2}}:\d{{2}}|Date and time to be announced|TBA)\s+(.+?)(?=Tickets|Groups|label\.aria\.groups|$)"
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            raw_time = match.group(1).replace("KO:", "").strip()
            details = match.group(2).strip()

            # ✅ FIX: stop the regex before stadium names bleed into team names
            fixture_match = re.search(
                r"([A-Za-zÀ-ÿ0-9&.'\- ]+?)\s+vs\.\s+([A-Za-zÀ-ÿ0-9&.'\- ]+?)(?=\s{2,}|\s+(?:Tickets|Buy|Spotify|Camp Nou|Estadi|Mendiz|Novo|Allianz|Signal|Bernab|Metropolit|Wanda|St\.\s*James|San Siro|Anfield|Old Trafford)|$)",
                details,
                re.IGNORECASE
            )

            competition_match = re.search(
                r"(UEFA Champions League|La Liga|Copa del Rey|Spanish Super Cup)",
                details,
                re.IGNORECASE
            )

            stage_match = re.search(
                r"(Round of 16|Matchday \d+|Quarter-final(?:s)?|Semi-final(?:s)?|Final)",
                details,
                re.IGNORECASE
            )

            home_team = fixture_match.group(1).strip() if fixture_match else "Unknown"
            away_team = fixture_match.group(2).strip() if fixture_match else "Unknown"
            competition = competition_match.group(1).strip() if competition_match else "Unknown competition"
            stage = stage_match.group(1).strip() if stage_match else ""

            # ✅ FIX: build venue by removing competition + stage + fixture from details
            venue = details
            for chunk in [competition, stage, fixture_match.group(0) if fixture_match else ""]:
                if chunk:
                    venue = re.sub(re.escape(chunk), "", venue, flags=re.IGNORECASE).strip()
            venue = re.sub(r"\s+", " ", venue).strip(" -")

            def clean_team_name(name: str) -> str:
                cleaned = name
                junk_patterns = [
                    r"\bUEFA Champions League\b",
                    r"\bLa Liga\b",
                    r"\bCopa del Rey\b",
                    r"\bSpanish Super Cup\b",
                    r"\bRound of 16\b",
                    r"\bQuarter-final(?:s)?\b",
                    r"\bSemi-final(?:s)?\b",
                    r"\bFinal\b",
                    r"\bMatchday\s+\d+\b",
                    r"\bSpotify Camp Nou\b",
                    r"\bCamp Nou\b",
                    r"\bEstadi Olímpic Lluís Companys\b",
                    r"\bSt\.?\s*James'? Park\b",
                    r"\bMendizorroza\b",
                    r"\bDate and time to be announced\b",
                    r"\bTBA\b",
                    r"\bAGG\b",
                    r"\bAgg\.\s*\d+\s*-\s*\d+\b",
                    r"\bAgg\b",
                    r"\bAggregate\b",
                ]
                for pattern in junk_patterns:
                    cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
                return cleaned

            home_team = clean_team_name(home_team)
            away_team = clean_team_name(away_team)

            israel_time = to_israel_time(date_str, raw_time) if ":" in raw_time else raw_time
            countdown = get_countdown(date_str, raw_time)

            print("[MATCH DEBUG] details:", details)
            print("[MATCH DEBUG] venue:", venue)
            print("[MATCH DEBUG] cleaned home_team:", home_team)
            print("[MATCH DEBUG] cleaned away_team:", away_team)

            return {
                "found": True,
                "matched_date": date_str,
                "time_spain": raw_time,
                "time_israel": israel_time,
                "competition": competition,
                "stage": stage,
                "stadium": venue,
                "home_team": home_team,
                "away_team": away_team,
                "fixture": f"{home_team} vs {away_team}",
                "source": BARCA_SCHEDULE_URL,
                "countdown": countdown,
            }

    return {
        "found": False,
        "matched_date": None,
        "time_spain": None,
        "time_israel": None,
        "competition": None,
        "stage": None,
        "stadium": None,
        "home_team": None,
        "away_team": None,
        "fixture": None,
        "source": BARCA_SCHEDULE_URL,
        "countdown": None,
    }


def build_email_content(result: dict):
    subject = f"⚽ FCB Match Alert | {result['fixture']}"

    hero_image_url = HERO_IMAGE_URL.strip()
    home_icon_url, away_icon_url = get_team_logo_urls(
        result["home_team"],
        result["away_team"]
    )

    poster_section = f"""
    <tr>
    <td style="padding:28px 28px 0 28px;">

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
    style="background:linear-gradient(135deg,#a50044 0%,#004d98 100%);
    border-radius:18px;padding:26px;color:white;text-align:center;">

    <tr>
    <td style="font-size:14px;font-weight:700;letter-spacing:1.2px;opacity:0.9;">
    {result['competition']}
    </td>
    </tr>

    <tr>
    <td style="padding-top:10px;font-size:28px;font-weight:900;color:#ffffff;">
    {result['fixture']}
    </td>
    </tr>

    <tr>
    <td style="padding-top:18px;">

    <table width="100%" role="presentation" cellspacing="0" cellpadding="0" border="0">
    <tr>

    <td align="center" width="40%">
    {"<img src='" + home_icon_url + "' alt='Home Team Logo' width='82' height='82' style='display:block;margin:0 auto 10px auto;object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,0.35));'>" if home_icon_url and home_icon_url.startswith('http') else ""}
    <div style="margin-top:8px;font-weight:700;color:#ffffff;">
    {result['home_team']}
    </div>
    </td>

    <td align="center" width="20%">
    <div style="
    display:inline-block;
    width:52px;
    height:52px;
    line-height:52px;
    border-radius:50%;
    background:rgba(255,255,255,0.18);
    color:#ffffff;
    font-size:18px;
    font-weight:900;
    text-align:center;
    ">
    VS
    </div>
    </td>

    <td align="center" width="40%">
    {"<img src='" + away_icon_url + "' alt='Away Team Logo' width='82' height='82' style='display:block;margin:0 auto 10px auto;object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,0.35));'>" if away_icon_url and away_icon_url.startswith('http') else ""}
    <div style="margin-top:8px;font-weight:700;color:#ffffff;">
    {result['away_team']}
    </div>
    </td>

    </tr>
    </table>

    </td>
    </tr>

    <tr>
    <td style="padding-top:20px;font-size:15px;font-weight:700;color:#ffffff;">
    📅 {result['matched_date']} | ⏰ {result['time_israel']} (Israel)
    </td>
    </tr>

    <tr>
    <td style="padding-top:6px;font-size:14px;opacity:0.9;color:#ffffff;">
    🏟️ {result['stadium']}
    </td>
    </tr>

    </table>

    </td>
    </tr>
    """

    plain_text = f"""FCB - Sotiris Automation

Match:
{result['fixture']}

Competition:
{result['competition']}

Stage:
{result['stage'] or 'N/A'}

Date:
{result['matched_date']}

Kickoff (Israel Time):
{result['time_israel']}

Stadium:
{result['stadium'] or 'N/A'}

Source:
{result['source']}

A calendar file (.ics) is attached to this email so you can add the match to your calendar.

"""

    hero_section = ""
    if hero_image_url:
        hero_section = f"""
        <tr>
          <td style="padding:0;">
            <img src="{hero_image_url}" alt="FC Barcelona Alert"
                 style="display:block;width:100%;max-width:660px;height:auto;">
          </td>
        </tr>
        """

    html = f"""
    <html>
      <body style="margin:0;padding:0;background:#f3f6fb;font-family:Arial,Helvetica,sans-serif;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f3f6fb;">
          <tr>
            <td align="center" style="padding:28px 14px;">

              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                   style="max-width:700px;background:#ffffff;border-radius:28px;border:1px solid #d8e1ec;
                      box-shadow:0 18px 50px rgba(15,23,42,0.14);overflow:hidden;">

                <tr>
                  <td style="height:8px;background:linear-gradient(90deg,#a50044 0%,#7a0036 20%,#004d98 55%,#003b73 80%,#edbb00 100%);"></td>
                </tr>

                <tr>
                  <td style="padding:0;background:#ffffff;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="height:10px;background:linear-gradient(90deg,#a50044 0%,#8b0038 22%,#004d98 58%,#003b73 85%,#edbb00 100%);"></td>
                      </tr>
                      <tr>
                        <td style="padding:34px 34px 30px 34px;background:#004d98;background-image:linear-gradient(135deg,#a50044 0%,#004d98 100%);text-align:center;">
                          <div style="font-size:13px;letter-spacing:1.8px;text-transform:uppercase;color:#f8d54a;font-weight:800;">
                            Sotiris Automation
                          </div>
                          <div style="margin-top:14px;font-size:34px;line-height:1.15;font-weight:900;color:#ffffff;letter-spacing:0.3px;">
                            ⚽ FC Barcelona Match Alert
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                {hero_section}
                {poster_section}
                <tr>
                    <td style="padding:36px 34px 34px 34px;">

                <div style="text-align:center;">
                  <div style="display:inline-block;background:#eef4ff;color:#004d98;font-size:12px;font-weight:800;
                              letter-spacing:1px;text-transform:uppercase;padding:8px 14px;border-radius:999px;">
                    Official SOTIRIS Match Notice
                  </div>
                </div>

                <div style="margin-top:18px;text-align:center;font-size:32px;font-weight:900;color:#101828;line-height:1.22;">
                  {result['fixture']}
                </div>

                <div style="margin-top:14px;text-align:center;font-size:16px;line-height:1.9;color:#526071;max-width:560px;margin-left:auto;margin-right:auto;">

                    <div style="font-weight:700;color:#0f172a;margin-bottom:10px;">
                        Hello Bro! This is the <strong>Sotiris Automation System</strong> Speaking... ⚙️
                    </div>

                    <div style="margin-bottom:10px;">
                        <strong>FC Barcelona is playing today</strong>.
                    </div>

                    <div style="margin-bottom:10px;">
                        It's time to prepare for kickoff — choose where you will watch the match,
                        get the beer ready 🍺, prepare the snacks, and make sure the TV is ready.
                    </div>

                    <div style="font-weight:700;color:#004d98;margin-top:6px;">
                        Kickoff is coming… Visca Barça! 🔵🔴
                    </div>

                </div>

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                    style="margin-top:30px;border-collapse:separate;border-spacing:0 14px;">

                    <tr>
                    <td style="background:#a50044;color:#ffffff;border-radius:18px;padding:22px 24px;">
                    <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;opacity:0.9;">Competition</div>
                    <div style="margin-top:8px;font-size:21px;font-weight:900;">🏆 {result['competition']}</div>
                    </td>
                    </tr>

                    <tr>
                    <td style="background:#004d98;color:#ffffff;border-radius:18px;padding:22px 24px;">
                    <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;opacity:0.9;">Stage</div>
                    <div style="margin-top:8px;font-size:19px;font-weight:900;">📌 {result['stage']}</div>
                    </td>
                    </tr>

                    <tr>
                    <td style="background:#a50044;color:#ffffff;border-radius:18px;padding:22px 24px;">
                    <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;opacity:0.9;">Date</div>
                    <div style="margin-top:8px;font-size:19px;font-weight:900;">📅 {result['matched_date']}</div>
                    </td>
                    </tr>

                    <tr>
                    <td style="background:#004d98;color:#ffffff;border-radius:18px;padding:22px 24px;">
                    <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;opacity:0.9;">Kickoff (Israel Time)</div>
                    <div style="margin-top:8px;font-size:22px;font-weight:900;">⏰ {result['time_israel']}</div>
                    </td>
                    </tr>

                    <tr>
                    <td style="background:#a50044;color:#ffffff;border-radius:18px;padding:22px 24px;">
                    <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;opacity:0.9;">Stadium</div>
                    <div style="margin-top:8px;font-size:19px;font-weight:900;">🏟️ {result['stadium']}</div>
                    </td>
                    </tr>

                    </table>
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin-top:28px;">
                      <tr>
                        <td align="center" bgcolor="#004d98" style="border-radius:12px;">
                          <a href="{result['source']}"
                             style="display:inline-block;padding:16px 30px;font-size:15px;font-weight:800;
                                    color:#ffffff;text-decoration:none;border-radius:12px;
                                    font-family:Arial,Helvetica,sans-serif;">
                            View Official Schedule
                          </a>
                        </td>
                      </tr>
                    </table>

                    <div style="margin-top:34px;padding-top:22px;border-top:1px solid #e8edf4;font-size:13px;line-height:1.9;color:#6b7280;text-align:center;">
                      This alert was generated and delivered by
                      <strong style="color:#0f172a;">SOTIRIS Automation Company🚀</strong>
                    </div>

                  </td>
                </tr>

              </table>

            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    return subject, plain_text, html


def send_email(subject: str, plain_text: str, html: str, ics_content: str | None = None):
    gmail = GMAIL_ADDRESS
    password = GMAIL_APP_PASSWORD
    receivers = RECIPIENTS
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"🔵🔴Barça - Sotiris Automation <{gmail}>"
    msg["To"] = "Undisclosed recipients"
    msg["Bcc"] = ", ".join(receivers)
    msg.set_content(plain_text)
    msg.add_alternative(html, subtype="html")
    if ics_content:
        msg.add_attachment(
            ics_content.encode("utf-8"),
            maintype="text",
            subtype="calendar",
            filename="barcelona_match.ics"
        )
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=60) as server:
        server.starttls()
        server.login(gmail, password)
        server.send_message(msg)


def run_daily():
    print("Starting Barcelona Daily Alert Scheduler...")
    schedule.every().day.at("10:00").do(main)
    schedule.every().day.at("17:00").do(main)
    while True:
        schedule.run_pending()


def main():
    test_mode = TEST_MODE

    if test_mode:
        result = {
            "found": True,
            "matched_date": "Tue 10 Mar",
            "time_spain": "21:00",
            "time_israel": "22:00",
            "competition": "UEFA Champions League",
            "stage": "Round of 16",
            "stadium": "St. James' Park",
            "home_team": "Newcastle United",
            "away_team": "FC Barcelona",
            "fixture": "Newcastle United vs FC Barcelona",
            "source": BARCA_SCHEDULE_URL,
            "countdown": "5h 20m",
        }
        subject, plain_text, html = build_email_content(result)
        ics_content = build_ics_content(result)
        send_email(subject, plain_text, html, ics_content)
        print("Test email sent successfully.")
        return

    result = find_today_match_from_official_site()

    if not result["found"]:
        print("No Barcelona match found for today.")
        return

    subject, plain_text, html = build_email_content(result)
    ics_content = build_ics_content(result)
    send_email(subject, plain_text, html, ics_content)
    print("Email sent successfully.")


if __name__ == "__main__":
    run_daily()