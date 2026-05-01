#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT_DIR/content_sets/demo-case-files}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to create PNG and MP4 case files." >&2
  exit 1
fi

FONT="$(fc-match -f '%{file}\n' DejaVuSans 2>/dev/null | head -1 || true)"
if [ ! -f "$FONT" ]; then
  FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
fi
if [ ! -f "$FONT" ]; then
  echo "A TrueType font is required for ffmpeg drawtext." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

write_doc() {
  local path="$1"
  local title="$2"
  local body="$3"
  {
    printf "%s\n" "$title"
    printf "%s\n\n" "$(printf "%s" "$title" | sed 's/./=/g')"
    printf "%s\n" "$body"
  } > "$path"
}

make_autonomous_vehicle() {
  local dir="$OUT_DIR/autonomous-vehicle-shuttle"
  mkdir -p "$dir"

  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x101418:s=1280x720:d=0.1" \
    -vf "drawbox=x=70:y=86:w=1140:h=548:color=0x182026:t=fill,drawbox=x=300:y=130:w=260:h=460:color=0x2f3434:t=fill,drawbox=x=720:y=130:w=260:h=460:color=0x2f3434:t=fill,drawbox=x=628:y=130:w=24:h=90:color=0xf0f4e8:t=fill,drawbox=x=628:y=260:w=24:h=90:color=0xf0f4e8:t=fill,drawbox=x=628:y=390:w=24:h=90:color=0xf0f4e8:t=fill,drawbox=x=505:y=430:w=270:h=92:color=0x76b900:t=fill,drawbox=x=535:y=455:w=210:h=36:color=0x111814:t=fill,drawbox=x=885:y=308:w=48:h=92:color=0xf0b84d:t=fill,drawbox=x=880:y=292:w=58:h=18:color=0xf3f6ef:t=fill,drawbox=x=880:y=408:w=58:h=18:color=0xf3f6ef:t=fill,drawbox=x=214:y=520:w=92:h=46:color=0xf05d5e:t=fill,drawbox=x=198:y=554:w=124:h=16:color=0xf05d5e:t=fill,drawtext=fontfile=${FONT}:text='AUTONOMOUS SHUTTLE REVIEW':x=96:y=110:fontsize=42:fontcolor=0xf3f6ef,drawtext=fontfile=${FONT}:text='Curb lane object detected near crosswalk':x=96:y=166:fontsize=30:fontcolor=0xf0b84d,drawtext=fontfile=${FONT}:text='Perception snapshot with ego path and pedestrian zone':x=96:y=586:fontsize=27:fontcolor=0xc8d2bf" \
    -frames:v 1 "$dir/autonomous-vehicle-shuttle.png"

  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x101418:s=1280x720:d=24:r=24" \
    -vf "drawbox=x=70:y=86:w=1140:h=548:color=0x182026:t=fill,drawbox=x=300:y=130:w=260:h=460:color=0x2f3434:t=fill,drawbox=x=720:y=130:w=260:h=460:color=0x2f3434:t=fill,drawbox=x=628:y=130:w=24:h=90:color=0xf0f4e8:t=fill,drawbox=x=628:y=260:w=24:h=90:color=0xf0f4e8:t=fill,drawbox=x=628:y=390:w=24:h=90:color=0xf0f4e8:t=fill,drawbox=x='500+5*t':y='455-3*t':w=270:h=92:color=0x76b900:t=fill,drawbox=x='530+5*t':y='480-3*t':w=210:h=36:color=0x111814:t=fill,drawbox=x=885:y=308:w=48:h=92:color=0xf0b84d:t=fill,drawbox=x=880:y=292:w=58:h=18:color=0xf3f6ef:t=fill,drawbox=x=880:y=408:w=58:h=18:color=0xf3f6ef:t=fill,drawbox=x='210+3*t':y=520:w=92:h=46:color=0xf05d5e:t=fill,drawbox=x='194+3*t':y=554:w=124:h=16:color=0xf05d5e:t=fill,drawbox=x=490:y=400:w=300:h=150:color=0x76b900@0.22:t=6,drawtext=fontfile=${FONT}:text='AV SHUTTLE EVENT CLIP':x=96:y=110:fontsize=42:fontcolor=0xf3f6ef,drawtext=fontfile=${FONT}:text='Vehicle slows as object remains in curb lane':x=96:y=166:fontsize=30:fontcolor=0xf0b84d,drawtext=fontfile=${FONT}:text='Local agents summarize scene and safety note':x=96:y=586:fontsize=27:fontcolor=0xc8d2bf" \
    -t 24 -pix_fmt yuv420p "$dir/autonomous-vehicle-shuttle.mp4"

  write_doc "$dir/autonomous-vehicle-safety-notes.txt" "Autonomous Vehicle Safety Notes" \
"Scenario: autonomous shuttle route 12 near the east campus crosswalk.
Observation: perception snapshot shows a curb lane object and a pedestrian zone near the planned path.
Related visual evidence: ego vehicle is centered in lane, the crosswalk marker is visible, and the video shows the vehicle slowing before the object.
Recommended action: flag the clip for safety review, confirm object classification, compare braking distance against route policy, and verify that the shuttle remains outside the pedestrian zone.
Success criteria: object is tracked for at least three frames, speed reduction is smooth, and the post event review includes scene summary plus next action owner."
}

make_manufacturing() {
  local dir="$OUT_DIR/manufacturing-quality-inspection"
  mkdir -p "$dir"

  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x101510:s=1280x720:d=0.1" \
    -vf "drawbox=x=70:y=86:w=1140:h=548:color=0x1b211b:t=fill,drawbox=x=128:y=438:w=920:h=56:color=0x3d4636:t=fill,drawbox=x=220:y=386:w=120:h=78:color=0x76b900:t=fill,drawbox=x=392:y=386:w=120:h=78:color=0x76b900:t=fill,drawbox=x=564:y=386:w=120:h=78:color=0xf0b84d:t=fill,drawbox=x=736:y=386:w=120:h=78:color=0x76b900:t=fill,drawbox=x=900:y=190:w=48:h=248:color=0x5ed7c7:t=fill,drawbox=x=795:y=198:w=165:h=42:color=0x5ed7c7:t=fill,drawbox=x=760:y=230:w=58:h=142:color=0x5ed7c7:t=fill,drawbox=x=735:y=352:w=112:h=34:color=0xf3f6ef:t=fill,drawbox=x=560:y=340:w=130:h=32:color=0xf05d5e:t=fill,drawtext=fontfile=${FONT}:text='MANUFACTURING QUALITY CELL':x=96:y=110:fontsize=42:fontcolor=0xf3f6ef,drawtext=fontfile=${FONT}:text='Vision station flags one amber part':x=96:y=166:fontsize=30:fontcolor=0xf0b84d,drawtext=fontfile=${FONT}:text='Robot cell evidence for local inspection briefing':x=96:y=586:fontsize=27:fontcolor=0xc8d2bf" \
    -frames:v 1 "$dir/manufacturing-quality-inspection.png"

  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x101510:s=1280x720:d=24:r=24" \
    -vf "drawbox=x=70:y=86:w=1140:h=548:color=0x1b211b:t=fill,drawbox=x=128:y=438:w=920:h=56:color=0x3d4636:t=fill,drawbox=x='160+18*t':y=386:w=120:h=78:color=0x76b900:t=fill,drawbox=x='332+18*t':y=386:w=120:h=78:color=0x76b900:t=fill,drawbox=x='504+18*t':y=386:w=120:h=78:color=0xf0b84d:t=fill,drawbox=x='676+18*t':y=386:w=120:h=78:color=0x76b900:t=fill,drawbox=x=900:y=190:w=48:h=248:color=0x5ed7c7:t=fill,drawbox=x='795+sin(t*2)*35':y=198:w=165:h=42:color=0x5ed7c7:t=fill,drawbox=x='760+sin(t*2)*45':y=230:w=58:h=142:color=0x5ed7c7:t=fill,drawbox=x='735+sin(t*2)*55':y=352:w=112:h=34:color=0xf3f6ef:t=fill,drawbox=x='500+18*t':y=340:w=130:h=32:color=0xf05d5e:t=fill,drawtext=fontfile=${FONT}:text='QUALITY INSPECTION WALKTHROUGH':x=96:y=110:fontsize=42:fontcolor=0xf3f6ef,drawtext=fontfile=${FONT}:text='Conveyor passes one out of tolerance part':x=96:y=166:fontsize=30:fontcolor=0xf0b84d,drawtext=fontfile=${FONT}:text='Agent summarizes defect evidence and next action':x=96:y=586:fontsize=27:fontcolor=0xc8d2bf" \
    -t 24 -pix_fmt yuv420p "$dir/manufacturing-quality-inspection.mp4"

  write_doc "$dir/manufacturing-quality-checklist.txt" "Manufacturing Quality Checklist" \
"Cell: robotic inspection station QI-7 on Line 3.
Observation: one amber part was flagged after the camera station measured a surface mark outside tolerance.
Related visual evidence: conveyor shows mixed part status, the robot arm is active, and the defect marker appears near the inspection zone.
Recommended action: quarantine the flagged part, inspect camera calibration, check the last twenty parts from the same fixture, and update the quality ticket with the image and clip.
Success criteria: flagged part is removed, camera confidence returns above 95 percent, and the next ten inspected parts pass without amber status."
}

make_media_entertainment() {
  local dir="$OUT_DIR/media-entertainment-virtual-production"
  mkdir -p "$dir"

  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x111216:s=1280x720:d=0.1" \
    -vf "drawbox=x=70:y=86:w=1140:h=548:color=0x1a1c24:t=fill,drawbox=x=160:y=160:w=720:h=330:color=0x26313f:t=fill,drawbox=x=190:y=190:w=660:h=270:color=0x5ed7c7:t=fill,drawbox=x=190:y=330:w=660:h=130:color=0x22382f:t=fill,drawbox=x=950:y=240:w=110:h=72:color=0x242831:t=fill,drawbox=x=1010:y=312:w=24:h=160:color=0x242831:t=fill,drawbox=x=930:y=470:w=190:h=28:color=0x76b900:t=fill,drawbox=x=238:y=392:w=72:h=44:color=0xf0b84d:t=fill,drawbox=x=350:y=368:w=86:h=68:color=0xf0b84d:t=fill,drawbox=x=478:y=344:w=96:h=92:color=0xf0b84d:t=fill,drawtext=fontfile=${FONT}:text='VIRTUAL PRODUCTION REVIEW':x=96:y=110:fontsize=42:fontcolor=0xf3f6ef,drawtext=fontfile=${FONT}:text='LED wall frame and camera marker alignment':x=96:y=166:fontsize=30:fontcolor=0xf0b84d,drawtext=fontfile=${FONT}:text='Media workflow evidence packaged into local briefing':x=96:y=586:fontsize=27:fontcolor=0xc8d2bf" \
    -frames:v 1 "$dir/media-entertainment-virtual-production.png"

  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x111216:s=1280x720:d=24:r=24" \
    -vf "drawbox=x=70:y=86:w=1140:h=548:color=0x1a1c24:t=fill,drawbox=x=160:y=160:w=720:h=330:color=0x26313f:t=fill,drawbox=x=190:y=190:w=660:h=270:color=0x5ed7c7:t=fill,drawbox=x=190:y=330:w=660:h=130:color=0x22382f:t=fill,drawbox=x='950-5*t':y=240:w=110:h=72:color=0x242831:t=fill,drawbox=x='1010-5*t':y=312:w=24:h=160:color=0x242831:t=fill,drawbox=x='930-5*t':y=470:w=190:h=28:color=0x76b900:t=fill,drawbox=x='238+12*t':y=392:w=72:h=44:color=0xf0b84d:t=fill,drawbox=x='350+8*t':y=368:w=86:h=68:color=0xf0b84d:t=fill,drawbox=x='478+4*t':y=344:w=96:h=92:color=0xf0b84d:t=fill,drawbox=x=188:y=188:w=664:h=274:color=0xf3f6ef@0.18:t=4,drawtext=fontfile=${FONT}:text='VIRTUAL PRODUCTION CLIP':x=96:y=110:fontsize=42:fontcolor=0xf3f6ef,drawtext=fontfile=${FONT}:text='Camera pass checks LED wall and foreground props':x=96:y=166:fontsize=30:fontcolor=0xf0b84d,drawtext=fontfile=${FONT}:text='Agent summarizes shot status and handoff needs':x=96:y=586:fontsize=27:fontcolor=0xc8d2bf" \
    -t 24 -pix_fmt yuv420p "$dir/media-entertainment-virtual-production.mp4"

  write_doc "$dir/virtual-production-shot-notes.txt" "Virtual Production Shot Notes" \
"Production: Stage B virtual production review for sequence VP-024.
Observation: LED wall horizon line, camera position, and foreground prop placement need a quick continuity check before final takes.
Related visual evidence: still frame shows the LED volume, camera marker, and foreground props while the clip shows a short camera pass across the stage.
Recommended action: verify camera tracking alignment, confirm horizon placement against the shot plan, inspect prop continuity, and publish a briefing for the director and stage supervisor.
Success criteria: camera marker remains aligned, no visible wall seam is detected, and the shot notes include a clear go or hold recommendation."
}

make_autonomous_vehicle
make_manufacturing
make_media_entertainment

echo "Created matching demo case files under: $OUT_DIR"
find "$OUT_DIR" -maxdepth 2 -type f | sort
