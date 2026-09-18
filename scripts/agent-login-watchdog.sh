#!/bin/bash
# Agent login watchdog.
#
# Why this exists: a Claude Code session can come up on a "Login successful.
# Press Enter to continue" screen and sit there forever. The scheduler keeps
# firing prompts into that pane and records them as "fired" -- because `fired`
# means the prompt was SENT, not that it ran. Heartbeat tasks are silent by
# design, so a stuck agent looks exactly like a quiet one. Measured 2026-08-22:
# Signal had been mute for four days (08-18 15:30 -> 08-22 08:12) with every
# scheduled round marked `fired`, and four more agents (bit, copy, lumen, reel)
# were sitting on the same screen at that moment. Nothing surfaced it.
#
# What it does: presses Enter ONLY when the login screen is the last thing on
# the pane. Never types anything else, never touches a working agent.
#
# KNOWN SIDE EFFECT, and it is intentional: the Enter also submits whatever text
# is parked on the input line. Measured 2026-08-22 -- when I cleared Signal's
# screen by hand at 08:05, a scheduled prompt that had been sitting there since
# an earlier day went through and ran a full email round. task_runs showed only
# ONE firing that day (08:18:46), which is how we know the 08:05 round was a
# replayed old prompt and not a duplicate schedule. That replay is the desired
# recovery -- but it means a stale prompt can execute, carrying a world-state
# assumption that has since expired. If an agent reports a round whose findings
# look oddly out of date, check this log for an UNBLOCKED entry near that time
# before believing the round was current.

TMUX_BIN="/opt/homebrew/bin/tmux"
TMUX_SOCKET="/tmp/tmux-501/default"
TMUX="$TMUX_BIN -S $TMUX_SOCKET"

LOG="/Users/macmini/marveen/store/logs/agent-login-watchdog.log"
STAMP=$(date '+%Y-%m-%d %H:%M:%S')
UNBLOCKED=0
CHECKED=0
STILL_STUCK=""
SEEN=""
RELOGGED=0
NEEDS_OWNER=""

# Scope: sub-agents AND the main agent's own sessions. Measured 2026-08-22: the
# first version only swept agent-*, and that is exactly the blind spot that let
# this incident run for three days -- Nova's own session was mute from 08-18
# evening to 08-22 dawn (zero daily-log entries on 08-19/20/21, and the newsletter
# billing patrol silently skipped the w34 send). A watchdog that cannot see the
# agent watching everyone else is the one gap nobody is left to notice.
for session in $($TMUX list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^(agent-|nova-)'); do
  CHECKED=$((CHECKED + 1))
  SEEN="$SEEN $session"
  # Only the tail matters: an agent QUOTING this text mid-answer must not trigger us.
  tail_lines=$($TMUX capture-pane -p -t "$session" 2>/dev/null | grep -v '^[[:space:]]*$' | tail -4)
  case "$tail_lines" in
    *"Not logged in"*)
      # SECOND failure shape, measured 2026-09-19 01:2x: Atlas sat in a healthy-looking
      # pane whose footer read "Not logged in - Run /login". No "Press Enter" line, so the
      # sweep above walked straight past it. The agent answered nothing for hours and the
      # scheduler kept marking its rounds `fired` -- the exact blind spot this file exists
      # for, in a shape the file could not see.
      #
      # The fix is NOT to type /login: that opens an interactive OAuth flow in the pane and
      # parks there waiting for a browser round trip nobody is at the keyboard for (measured
      # the same night -- it printed an authorize URL and a "Paste code here" prompt).
      # The credential itself lives in the login keychain and is SHARED by every agent, so a
      # restart is what re-reads it. Atlas restarted 01:30:11 and answered an inter-agent
      # ping inside a minute, with no human step.
      #
      # THE GUARD MATTERS MORE THAN THE FIX: restart only while the stored token is still
      # valid. If it has actually expired, a restart cannot help and a loop of restarts would
      # bury the one thing that does -- the owner logging in. That case escalates instead.
      agent_name="${session#agent-}"
      token_ok=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | python3 -c '
import json,sys,time
try:
    d=json.load(sys.stdin); o=d.get("claudeAiOauth",d)
    print("OK" if int(o.get("expiresAt",0))/1000 > time.time() else "EXPIRED")
except Exception:
    print("UNKNOWN")
' 2>/dev/null)
      case "$session" in
        nova-*)
          # The main session is the one the owner is talking to. A restart there drops the
          # live channel mid-turn, so this only escalates -- the recovery is a human call.
          NEEDS_OWNER="$NEEDS_OWNER $session(fo-agens,token=$token_ok)"
          echo "$STAMP  NOT-LOGGED-IN  $session  (fo agens, csak jelzes, token=$token_ok)" >> "$LOG"
          ;;
        *)
          if [ "$token_ok" = "OK" ]; then
            TOKEN=$(cat /Users/macmini/marveen/store/.dashboard-token 2>/dev/null)
            rc=$(curl -s -o /dev/null -w '%{http_code}' -m 20 -X POST \
                 "http://localhost:3420/api/agents/$agent_name/restart" \
                 -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{}')
            if [ "$rc" = "200" ]; then
              RELOGGED=$((RELOGGED + 1))
              echo "$STAMP  RELOGIN-RESTART  $session  (ervenyes token, /api/agents/$agent_name/restart -> $rc)" >> "$LOG"
            else
              NEEDS_OWNER="$NEEDS_OWNER $session(restart-HTTP-$rc)"
              echo "$STAMP  RESTART-FAILED  $session  (HTTP $rc)" >> "$LOG"
            fi
          else
            NEEDS_OWNER="$NEEDS_OWNER $session(token=$token_ok)"
            echo "$STAMP  NOT-LOGGED-IN  $session  (a tarolt token $token_ok -- restart nem segit, gazda kell)" >> "$LOG"
          fi
          ;;
      esac
      ;;
    *"Press Enter to continue"*)
      before=$($TMUX capture-pane -p -t "$session" 2>/dev/null)
      $TMUX send-keys -t "$session" Enter
      sleep 3
      after=$($TMUX capture-pane -p -t "$session" 2>/dev/null)
      # Verdict is CHANGE, not the absence of the phrase. Measured 2026-08-22 with a
      # synthetic control: the Enter landed (the pane's reader ran) while the login
      # text was still sitting in the scrollback, so a phrase-based recheck called a
      # successful unblock a failure. A watchdog that cries wolf after every fix is
      # what teaches you to stop reading its log.
      if [ "$before" = "$after" ]; then
        STILL_STUCK="$STILL_STUCK $session"
        echo "$STAMP  STUCK-AFTER-ENTER  $session  (pane unchanged after Enter)" >> "$LOG"
      else
        UNBLOCKED=$((UNBLOCKED + 1))
        echo "$STAMP  UNBLOCKED  $session" >> "$LOG"
      fi
      ;;
  esac
done

# Always leave proof the sweep ran, not only proof it found something --
# otherwise a watchdog that silently died looks identical to a clean fleet.
echo "$STAMP  SWEEP  checked=$CHECKED unblocked=$UNBLOCKED relogin=$RELOGGED stuck=${STILL_STUCK:-none} gazda=${NEEDS_OWNER:-none} seen=${SEEN:- none}" >> "$LOG"

if [ "$CHECKED" -eq 0 ]; then
  # Not "all clear" -- it means the sweep could not see anything. Distinct exit
  # code so a caller can tell blindness from health.
  echo "$STAMP  BLIND  no agent-/nova- sessions visible (tmux bin=$TMUX_BIN socket=$TMUX_SOCKET)" >> "$LOG"
  exit 3
fi

if [ -n "$STILL_STUCK" ] || [ -n "$NEEDS_OWNER" ]; then
  # Escalate, but not every five minutes: a repeating identical alert is how a
  # real one stops being read. One ping per hour per sweep-with-stuck-agents.
  STAMPFILE="/Users/macmini/marveen/store/.agent-login-watchdog-alerted"
  NOW=$(date +%s)
  LAST=0
  [ -f "$STAMPFILE" ] && LAST=$(cat "$STAMPFILE" 2>/dev/null || echo 0)
  if [ $((NOW - LAST)) -ge 3600 ]; then
    TOKEN=$(cat /Users/macmini/marveen/store/.dashboard-token 2>/dev/null)
    if [ -n "$TOKEN" ]; then
      BODY=$(SESSIONS="${STILL_STUCK}${NEEDS_OWNER}" python3 -c 'import json,os; print(json.dumps({"from":"nova","to":"nova","content":"[LOGIN-WATCHDOG] Ezek a sessionok NEM futokepesek (bejelentkezo kepernyo, amit az Enter nem oldott fel, VAGY \"Not logged in\" ervenytelen tokennel):" + os.environ["SESSIONS"] + ". Amig igy allnak, az utemezett korok promptja megerkezik hozzajuk es fired-nek szamit, de NEM fut le -- kivulrol ez csendes heartbeatnek latszik. Kezi beavatkozas kell. A sweep naploja: store/logs/agent-login-watchdog.log"}))')
      curl -s -o /dev/null -m 10 -X POST http://localhost:3420/api/messages \
        -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
        --data-binary "$BODY"
      echo "$NOW" > "$STAMPFILE"
      echo "$STAMP  ALERTED ${STILL_STUCK}${NEEDS_OWNER}" >> "$LOG"
    fi
  else
    echo "$STAMP  ALERT-THROTTLED  (utolso riasztas $(( (NOW - LAST) / 60 )) perce)" >> "$LOG"
  fi
  exit 2
fi
exit 0
