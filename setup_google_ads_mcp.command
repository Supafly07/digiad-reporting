#!/bin/bash
# Double-click this file to connect Claude to your Google Ads account using
# Google's official (read-only) Google Ads MCP server:
#   https://github.com/googleads/google-ads-mcp
#
# Before running it, have these ready (see README, "Google Ads MCP"):
#   1. Your Google Ads developer token (Manager account -> Admin -> API Center)
#   2. Your Google Cloud project ID (with the Google Ads API enabled)
#   3. The OAuth "Desktop app" client JSON file you downloaded from Google Cloud

cd "$(dirname "$0")" || exit 1

SERVER_NAME="google-ads"
SERVER_SPEC="git+https://github.com/googleads/google-ads-mcp.git"
ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"

fail() {
  echo ""
  echo "$1"
  echo ""
  read -n 1 -s -r -p "Press any key to close this window."
  exit 1
}

echo "============================================"
echo "  Google Ads MCP - one-time setup"
echo "============================================"
echo ""

# 1. Homebrew installs the other tools. Load it if it's installed but not on PATH.
if ! command -v brew >/dev/null 2>&1; then
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$b" ] && eval "$("$b" shellenv)"
  done
fi
if ! command -v brew >/dev/null 2>&1; then
  fail "Homebrew isn't installed yet. Install it from https://brew.sh (copy the
command on that page into Terminal), then double-click this file again."
fi

# 2. Install pipx (runs the MCP server) and the Google Cloud CLI (signs you in).
if ! command -v pipx >/dev/null 2>&1; then
  echo "Installing pipx..."
  brew install pipx || fail "Installing pipx failed."
fi
if ! command -v gcloud >/dev/null 2>&1; then
  echo "Installing the Google Cloud CLI (this takes a few minutes)..."
  brew install --cask gcloud-cli 2>/dev/null || brew install --cask google-cloud-sdk \
    || fail "Installing the Google Cloud CLI failed."
  for p in /opt/homebrew/share/google-cloud-sdk/bin /usr/local/share/google-cloud-sdk/bin \
           /opt/homebrew/Caskroom/gcloud-cli/latest/google-cloud-sdk/bin \
           /opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin; do
    [ -d "$p" ] && PATH="$p:$PATH"
  done
  command -v gcloud >/dev/null 2>&1 \
    || fail "The Google Cloud CLI installed, but this window can't find it yet.
Close this window and double-click this file again."
fi
PIPX_PATH="$(command -v pipx)"

# 3. Ask for the details.
echo ""
echo "--------------------------------------------"
echo "  Your details"
echo "--------------------------------------------"
echo "Tip: for the JSON file, you can drag it from Finder into this window."
echo ""

read -r -p "Path to your OAuth client JSON file: " CLIENT_JSON
# Undo the quoting/escaping Terminal adds when a file is dragged in.
CLIENT_JSON="${CLIENT_JSON%"${CLIENT_JSON##*[![:space:]]}"}"
CLIENT_JSON="${CLIENT_JSON#\'}"; CLIENT_JSON="${CLIENT_JSON%\'}"
CLIENT_JSON="${CLIENT_JSON#\"}"; CLIENT_JSON="${CLIENT_JSON%\"}"
CLIENT_JSON="${CLIENT_JSON//\\ / }"
CLIENT_JSON="${CLIENT_JSON/#\~/$HOME}"
[ -f "$CLIENT_JSON" ] || fail "Couldn't find a file at: $CLIENT_JSON"

read -r -p "Google Cloud project ID: " PROJECT_ID
[ -n "$PROJECT_ID" ] || fail "A project ID is required."

read -r -s -p "Google Ads developer token (hidden as you type): " DEV_TOKEN
echo ""
[ -n "$DEV_TOKEN" ] || fail "A developer token is required."

read -r -p "Manager (MCC) account ID, e.g. 123-456-7890 (press Return to skip): " LOGIN_CID
LOGIN_CID="${LOGIN_CID//[^0-9]/}"

# 4. Sign in to Google. This opens a browser window.
echo ""
echo "A browser window is opening. Sign in with the Google account that has"
echo "access to your Google Ads accounts, and allow every permission it asks for."
echo ""
gcloud auth application-default login \
  --scopes https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file="$CLIENT_JSON" \
  || fail "Google sign-in didn't complete. Double-click this file to try again."
[ -f "$ADC_FILE" ] || fail "Sign-in finished but no credentials file was found at $ADC_FILE"

# 5. Pre-download the server so the first start inside Claude is fast.
echo ""
echo "Downloading the Google Ads MCP server..."
"$PIPX_PATH" run --spec "$SERVER_SPEC" google-ads-mcp --help >/dev/null 2>&1 || true

ADDED=0

# 6a. Claude Code (the 'claude' command).
if command -v claude >/dev/null 2>&1; then
  echo "Adding it to Claude Code..."
  claude mcp remove "$SERVER_NAME" -s user >/dev/null 2>&1
  ENV_ARGS=(-e "GOOGLE_APPLICATION_CREDENTIALS=$ADC_FILE"
            -e "GOOGLE_PROJECT_ID=$PROJECT_ID"
            -e "GOOGLE_ADS_DEVELOPER_TOKEN=$DEV_TOKEN")
  [ -n "$LOGIN_CID" ] && ENV_ARGS+=(-e "GOOGLE_ADS_LOGIN_CUSTOMER_ID=$LOGIN_CID")
  if claude mcp add "$SERVER_NAME" -s user "${ENV_ARGS[@]}" \
       -- "$PIPX_PATH" run --spec "$SERVER_SPEC" google-ads-mcp; then
    ADDED=1
  else
    echo "Couldn't add it to Claude Code automatically."
  fi
fi

# 6b. Claude Desktop app.
DESKTOP_DIR="$HOME/Library/Application Support/Claude"
if [ -d "$DESKTOP_DIR" ]; then
  read -r -p "Also add it to the Claude Desktop app? (Y/n): " ANS
  if [[ ! "$ANS" =~ ^[Nn] ]]; then
    CONFIG="$DESKTOP_DIR/claude_desktop_config.json"
    [ -f "$CONFIG" ] && cp "$CONFIG" "$CONFIG.bak"
    if CONFIG="$CONFIG" NAME="$SERVER_NAME" PIPX="$PIPX_PATH" SPEC="$SERVER_SPEC" \
       ADC="$ADC_FILE" PROJECT="$PROJECT_ID" TOKEN="$DEV_TOKEN" CID="$LOGIN_CID" \
       /usr/bin/python3 - <<'PY'
import json, os
path = os.environ["CONFIG"]
try:
    with open(path) as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}
env = {
    "GOOGLE_APPLICATION_CREDENTIALS": os.environ["ADC"],
    "GOOGLE_PROJECT_ID": os.environ["PROJECT"],
    "GOOGLE_ADS_DEVELOPER_TOKEN": os.environ["TOKEN"],
}
if os.environ["CID"]:
    env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"] = os.environ["CID"]
data.setdefault("mcpServers", {})[os.environ["NAME"]] = {
    "command": os.environ["PIPX"],
    "args": ["run", "--spec", os.environ["SPEC"], "google-ads-mcp"],
    "env": env,
}
with open(path, "w") as f:
    json.dump(data, f, indent=2)
PY
    then
      ADDED=1
      echo "Added to Claude Desktop (previous settings backed up to claude_desktop_config.json.bak)."
    else
      echo "Couldn't update the Claude Desktop settings file."
    fi
  fi
fi

echo ""
echo "============================================"
if [ "$ADDED" = 1 ]; then
  echo "  Done!"
  echo "============================================"
  echo "Fully quit Claude (Cmd+Q) and open it again, then ask:"
  echo "   \"List my accessible Google Ads customers\""
  echo ""
  echo "In Claude Code you can type /mcp to check that '$SERVER_NAME' is connected."
else
  echo "  Signed in, but Claude wasn't found"
  echo "============================================"
  echo "Install Claude Code (https://claude.com/claude-code) or the Claude Desktop"
  echo "app, then double-click this file again to finish."
fi
echo ""
echo "Note: this server is read-only - Claude can report on your ads but not change them."
echo ""
read -n 1 -s -r -p "Press any key to close this window."
