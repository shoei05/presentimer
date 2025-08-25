import streamlit as st
import datetime
import time
import pytz
import json
import os
import re
import unicodedata

# ページ設定
st.set_page_config(
    page_title="プレゼンタイマー",
    page_icon="⏰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 設定ファイルのパス
SETTINGS_FILE = "timer_settings.json"

# --- ユーティリティ ---
def parse_time_input(time_str):
    """
    様々な時刻入力フォーマットを解析
    例: "07:00", "700", "0700", "7:00", "7", "19:30", "1930" など
    """
    if not time_str:
        return None

    # 全角などを正規化してから数字とコロンのみを抽出
    time_str = unicodedata.normalize('NFKC', str(time_str))
    clean_str = re.sub(r'[^\d:]', '', time_str)

    try:
        # コロンが含まれている場合
        if ':' in clean_str:
            parts = clean_str.split(':')
            if len(parts) == 2:
                hour = int(parts[0])
                minute = int(parts[1])
            else:
                return None

        # コロンが含まれていない場合
        else:
            if len(clean_str) == 1:  # "7" -> "07:00"
                hour = int(clean_str)
                minute = 0
            elif len(clean_str) == 2:  # "07" -> "07:00"
                hour = int(clean_str)
                minute = 0
            elif len(clean_str) == 3:  # "700" -> "07:00"
                hour = int(clean_str[0])
                minute = int(clean_str[1:3])
            elif len(clean_str) == 4:  # "0700" -> "07:00"
                hour = int(clean_str[0:2])
                minute = int(clean_str[2:4])
            else:
                return None

        # 時刻の妥当性チェック
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return datetime.time(hour, minute)
        else:
            return None

    except (ValueError, IndexError):
        return None


def parse_duration_input(duration_str):
    """
    プレゼン時間の入力フォーマットを解析
    例: "15", "15:00", "1:30", "90" など

    修正点:
    - コロン形式の「分:秒」で、分は 0 以上の任意の整数を許可（60分以上もOK）
    - "15" は 15分 (=900秒)、"90" は 90秒 として扱う
    """
    if not duration_str:
        return None

    # 全角などを正規化してから数字とコロンのみを抽出
    duration_str = unicodedata.normalize('NFKC', str(duration_str))
    clean_str = re.sub(r'[^\d:]', '', duration_str)

    try:
        # コロンが含まれている場合（分:秒）
        if ':' in clean_str:
            parts = clean_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])  # 上限撤廃
                seconds = int(parts[1])
                if minutes >= 0 and 0 <= seconds <= 59:
                    return minutes * 60 + seconds
            return None

        # コロンが含まれていない場合
        else:
            duration = int(clean_str)
            if duration <= 0:
                return None
            # 60未満の場合は分として扱う
            if duration < 60:
                return duration * 60
            # それ以外は秒として扱う
            return duration

    except (ValueError, IndexError):
        return None


def load_settings():
    """設定を読み込み（プレゼンタイマー機能も含む）"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                time_obj = datetime.datetime.strptime(data['time'], '%H:%M').time()
                return (
                    time_obj,
                    data['suffix'],
                    data.get('timestamp', ''),
                    data.get('color_state', False),
                    data.get('force_color', False),
                    data.get('timer_mode', 'clock'),  # 'clock' or 'presentation'
                    data.get('presentation_duration', 900),  # 秒
                    data.get('timer_started', False),
                    data.get('timer_start_time', ''),
                    data.get('timer_paused', False),
                    data.get('timer_pause_time', 0)
                )
    except Exception:
        pass
    return datetime.time(23, 59), "から開始", "", False, False, "clock", 900, False, "", False, 0


def save_settings(target_time, suffix, color_state=False, force_color=False, timer_mode="clock",
                 presentation_duration=900, timer_started=False, timer_start_time="",
                 timer_paused=False, timer_pause_time=0):
    """設定を保存（プレゼンタイマー機能も含む）"""
    try:
        data = {
            'time': target_time.strftime('%H:%M'),
            'suffix': suffix,
            'color_state': color_state,
            'force_color': force_color,
            'timestamp': datetime.datetime.now().isoformat(),
            'timer_mode': timer_mode,
            'presentation_duration': int(presentation_duration),
            'timer_started': bool(timer_started),
            'timer_start_time': timer_start_time,
            'timer_paused': bool(timer_paused),
            'timer_pause_time': int(timer_pause_time)
        }
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception:
        return False


# 設定を読み込み
shared_time, shared_suffix, last_timestamp, shared_color_state, shared_force_color, \
shared_timer_mode, shared_presentation_duration, shared_timer_started, shared_timer_start_time, \
shared_timer_paused, shared_timer_pause_time = load_settings()

# セッション状態の初期化
if 'target_time' not in st.session_state:
    st.session_state.target_time = shared_time
if 'suffix' not in st.session_state:
    st.session_state.suffix = shared_suffix
if 'last_timestamp' not in st.session_state:
    st.session_state.last_timestamp = last_timestamp
if 'time_reached' not in st.session_state:
    st.session_state.time_reached = False
if 'editing' not in st.session_state:
    st.session_state.editing = False
if 'force_color_change' not in st.session_state:
    st.session_state.force_color_change = False
if 'timer_mode' not in st.session_state:
    st.session_state.timer_mode = shared_timer_mode
if 'presentation_duration' not in st.session_state:
    st.session_state.presentation_duration = shared_presentation_duration
if 'timer_started' not in st.session_state:
    st.session_state.timer_started = shared_timer_started
if 'timer_start_time' not in st.session_state:
    st.session_state.timer_start_time = shared_timer_start_time
if 'timer_paused' not in st.session_state:
    st.session_state.timer_paused = shared_timer_paused
if 'timer_pause_time' not in st.session_state:
    st.session_state.timer_pause_time = shared_timer_pause_time

# 他のユーザーの変更をチェック
current_time, current_suffix, current_timestamp, current_color_state, current_force_color, \
current_timer_mode, current_presentation_duration, current_timer_started, current_timer_start_time, \
current_timer_paused, current_timer_pause_time = load_settings()

if current_timestamp != st.session_state.last_timestamp and current_timestamp != "":
    st.session_state.target_time = current_time
    st.session_state.suffix = current_suffix
    st.session_state.last_timestamp = current_timestamp
    st.session_state.time_reached = current_color_state
    st.session_state.force_color_change = current_force_color
    st.session_state.timer_mode = current_timer_mode
    st.session_state.presentation_duration = current_presentation_duration
    st.session_state.timer_started = current_timer_started
    st.session_state.timer_start_time = current_timer_start_time
    st.session_state.timer_paused = current_timer_paused
    st.session_state.timer_pause_time = current_timer_pause_time

# 日本時間の設定
jst = pytz.timezone('Asia/Tokyo')
now = datetime.datetime.now(jst)

# --- プレゼンタイマーのロジック（判定のみここで実施）---
if st.session_state.timer_mode == "presentation":
    # 残り秒数の計算（ここでは副作用なし）
    if st.session_state.timer_started and not st.session_state.timer_paused:
        if st.session_state.timer_start_time:
            start_time = datetime.datetime.fromisoformat(st.session_state.timer_start_time)
            elapsed_seconds = (now - start_time).total_seconds()
            remaining_seconds = st.session_state.presentation_duration - elapsed_seconds
            # 時間切れの判定
            if remaining_seconds <= 0 and not st.session_state.time_reached:
                st.session_state.time_reached = True
                st.session_state.force_color_change = True
                save_settings(
                    st.session_state.target_time,
                    st.session_state.suffix,
                    True, True,
                    st.session_state.timer_mode,
                    st.session_state.presentation_duration,
                    st.session_state.timer_started,
                    st.session_state.timer_start_time,
                    st.session_state.timer_paused,
                    st.session_state.timer_pause_time
                )
                st.balloons()
        else:
            remaining_seconds = st.session_state.presentation_duration
    elif st.session_state.timer_paused:
        remaining_seconds = st.session_state.timer_pause_time
    else:
        # 未開始
        remaining_seconds = st.session_state.presentation_duration
        if st.session_state.time_reached:
            st.session_state.time_reached = False
            st.session_state.force_color_change = False
            save_settings(
                st.session_state.target_time,
                st.session_state.suffix,
                False, False,
                st.session_state.timer_mode,
                st.session_state.presentation_duration,
                st.session_state.timer_started,
                st.session_state.timer_start_time,
                st.session_state.timer_paused,
                st.session_state.timer_pause_time
            )
else:
    # 通常の時計モード
    target_dt = datetime.datetime.combine(datetime.date.today(), st.session_state.target_time)
    target_dt = jst.localize(target_dt)
    current_time_reached = now.time() >= st.session_state.target_time

    # 時刻到達時の自動反転処理
    if current_time_reached and not st.session_state.time_reached:
        st.session_state.time_reached = True
        st.session_state.force_color_change = True
        save_settings(
            st.session_state.target_time,
            st.session_state.suffix,
            True, True,
            st.session_state.timer_mode,
            st.session_state.presentation_duration,
            st.session_state.timer_started,
            st.session_state.timer_start_time,
            st.session_state.timer_paused,
            st.session_state.timer_pause_time
        )
        st.balloons()
    elif not current_time_reached and not st.session_state.force_color_change:
        st.session_state.time_reached = False

# 背景色とテキスト色の設定
if st.session_state.time_reached:
    bg_color = "#c5487b"
    text_color = "white"
else:
    bg_color = "#f5f5f5"
    text_color = "#333333"

# カスタムCSS
st.markdown(f"""
<style>
    .stApp {{
        background-color: {bg_color} !important;
    }}

    .main {{
        padding: 0 !important;
    }}

    .block-container {{
        padding: 2rem 1rem !important;
        max-width: 100% !important;
    }}

    .target-time {{
        font-size: 3rem;
        font-weight: bold;
        color: {text_color};
        text-align: center;
        margin: 1rem 0;
        padding: 1rem;
        border-radius: 10px;
        line-height: 0.9;
    }}

    .current-time {{
        font-size: 6rem;
        font-weight: bold;
        color: {text_color};
        text-align: center;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
        line-height: 0.9;
    }}

    .date-display {{
        font-size: 1.8rem;
        color: {text_color};
        text-align: center;
        margin: 0.5rem 0 1rem 0;
        line-height: 1;
    }}

    .time-info {{
        font-size: 1.5rem;
        color: {text_color};
        text-align: center;
        margin: 1rem 0;
        line-height: 1;
    }}

    .timer-display {{
        /* カウントダウンを主役に：大きく＆レスポンシブ */
        font-size: clamp(6rem, 22vw, 20rem);
        font-weight: 800;
        color: {text_color};
        text-align: center;
        margin: 0.5rem 0;
        font-family: 'Courier New', monospace;
        line-height: 0.85;
        letter-spacing: 0.03em;
    }}

    .timer-display.overtime {{
        color: #ff4444 !important;
        animation: pulse 1s infinite;
    }}

    @keyframes pulse {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
        100% {{ opacity: 1; }}
    }}

    .settings-section {{
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid {text_color};
        opacity: 0.7;
    }}

    .stButton > button {{
        background-color: transparent !important;
        border: 2px solid {text_color} !important;
        color: {text_color} !important;
        font-size: 1.1rem !important;
        padding: 0.5rem 1.5rem !important;
        border-radius: 8px !important;
        width: 100% !important;
    }}

    .stButton > button:hover {{
        background-color: {text_color} !important;
        color: {bg_color} !important;
    }}

    .stTextInput > div > div > input {{
        background-color: white !important;
        border: 2px solid {text_color} !important;
        color: #333333 !important;
        text-align: center !important;
        font-size: 1.2rem !important;
    }}

    .stTextInput > div > div > input:focus {{
        outline: none !important;
        box-shadow: 0 0 0 2px {text_color} !important;
    }}

    .stTextInput > div > div > input::placeholder {{
        color: #666666 !important;
        opacity: 0.8 !important;
    }}

    .stSelectbox > div > div {{
        background-color: white !important;
        border: 2px solid {text_color} !important;
        color: #333333 !important;
    }}

    .stSelectbox > div > div > div {{
        color: #333333 !important;
    }}

    .color-toggle-btn {{
        margin-top: 1rem;
        opacity: 0.8;
    }}

    .timer-controls {{
        margin-top: 2rem;
        display: flex;
        gap: 1rem;
        justify-content: center;
    }}

    /* Streamlitのデフォルト要素を非表示 */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{visibility: hidden;}}

    /* 警告メッセージのスタイル */
    .stAlert {{
        background-color: rgba(255, 193, 7, 0.1) !important;
        border: 1px solid #ffc107 !important;
        color: {text_color} !important;
    }}

    .input-help {{
        font-size: 0.9rem;
        color: {text_color};
        opacity: 0.7;
        text-align: center;
        margin-top: 0.5rem;
    }}
</style>
""", unsafe_allow_html=True)

# --- メイン表示 ---
if st.session_state.timer_mode == "presentation":
    # 残り秒数の再計算（表示用）
    if st.session_state.timer_started and not st.session_state.timer_paused and st.session_state.timer_start_time:
        start_time = datetime.datetime.fromisoformat(st.session_state.timer_start_time)
        elapsed_seconds = (now - start_time).total_seconds()
        remaining_seconds = st.session_state.presentation_duration - elapsed_seconds
    elif st.session_state.timer_paused:
        remaining_seconds = st.session_state.timer_pause_time
    else:
        remaining_seconds = st.session_state.presentation_duration

    # カウントダウン / オーバー表示
    if remaining_seconds >= 0:
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)
        timer_display = f"{minutes:02d}:{seconds:02d}"
        timer_class = "timer-display"
    else:
        over_seconds = abs(remaining_seconds)
        over_minutes = int(over_seconds // 60)
        over_secs = int(over_seconds % 60)
        timer_display = f"+{over_minutes:02d}:{over_secs:02d}"
        timer_class = "timer-display overtime"

    st.markdown(f"""
    <div class="{timer_class}">
        {timer_display}
    </div>
    """, unsafe_allow_html=True)

    # 現在時刻
    st.markdown(f"""
    <div class="current-time">
        {now.strftime('%H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)

    # 日付
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[now.weekday()]
    st.markdown(f"""
    <div class="date-display">
        {now.strftime('%Y年%m月%d日')}（{weekday}）
    </div>
    """, unsafe_allow_html=True)

    # 状態表示
    if st.session_state.timer_started:
        if st.session_state.timer_paused:
            status_text = "⏸️ 一時停止中"
        elif st.session_state.timer_start_time:
            start_time = datetime.datetime.fromisoformat(st.session_state.timer_start_time)
            elapsed_seconds = (now - start_time).total_seconds()
            current_remaining = st.session_state.presentation_duration - elapsed_seconds
            if current_remaining <= 0:
                status_text = "⏰ 時間切れ"
            else:
                status_text = "▶️ プレゼン中"
        else:
            status_text = "▶️ プレゼン中"
    else:
        status_text = "⏹️ 停止中"

    st.markdown(f"""
    <div class="time-info">
        {status_text}
    </div>
    """, unsafe_allow_html=True)

    # デバッグ情報（任意）
    if st.session_state.timer_started and st.session_state.timer_start_time:
        start_time = datetime.datetime.fromisoformat(st.session_state.timer_start_time)
        elapsed_seconds = (now - start_time).total_seconds()
        st.markdown(f"""
        <div class="time-info" style="font-size: 1rem; opacity: 0.6;">
            経過時間: {int(elapsed_seconds)}秒 / 設定時間: {int(st.session_state.presentation_duration)}秒
        </div>
        """, unsafe_allow_html=True)

    # タイマーコントロール
    st.markdown('<div class="timer-controls">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ スタート", key="start_timer"):
            if not st.session_state.timer_started:
                # 新規スタート
                st.session_state.timer_started = True
                st.session_state.timer_start_time = now.isoformat()
                st.session_state.timer_paused = False
                st.session_state.timer_pause_time = 0
                st.session_state.time_reached = False
                st.session_state.force_color_change = False
                save_settings(
                    st.session_state.target_time,
                    st.session_state.suffix,
                    False,
                    False,
                    st.session_state.timer_mode,
                    st.session_state.presentation_duration,
                    True,
                    st.session_state.timer_start_time,
                    False,
                    0
                )
                st.rerun()
            elif st.session_state.timer_paused:
                # 一時停止からの再開：残り時間でリスタートする
                remaining = max(0, int(st.session_state.timer_pause_time))
                st.session_state.presentation_duration = remaining
                st.session_state.timer_paused = False
                st.session_state.timer_pause_time = 0
                st.session_state.timer_start_time = now.isoformat()
                save_settings(
                    st.session_state.target_time,
                    st.session_state.suffix,
                    st.session_state.time_reached,
                    st.session_state.force_color_change,
                    st.session_state.timer_mode,
                    remaining,
                    True,
                    st.session_state.timer_start_time,
                    False,
                    0
                )
                st.rerun()

    with col2:
        if st.button("⏸️ 一時停止", key="pause_timer"):
            if st.session_state.timer_started and not st.session_state.timer_paused:
                # 現在の残り時間を計算
                if st.session_state.timer_start_time:
                    start_time = datetime.datetime.fromisoformat(st.session_state.timer_start_time)
                    elapsed_seconds = (now - start_time).total_seconds()
                    current_remaining = max(0, st.session_state.presentation_duration - elapsed_seconds)
                else:
                    current_remaining = st.session_state.presentation_duration

                st.session_state.timer_paused = True
                st.session_state.timer_pause_time = int(current_remaining)
                save_settings(
                    st.session_state.target_time,
                    st.session_state.suffix,
                    st.session_state.time_reached,
                    st.session_state.force_color_change,
                    st.session_state.timer_mode,
                    st.session_state.presentation_duration,
                    True,
                    st.session_state.timer_start_time,
                    True,
                    st.session_state.timer_pause_time
                )
                st.rerun()

    with col3:
        if st.button("⏹️ リセット", key="reset_timer"):
            st.session_state.timer_started = False
            st.session_state.timer_start_time = ""
            st.session_state.timer_paused = False
            st.session_state.timer_pause_time = 0
            st.session_state.time_reached = False
            st.session_state.force_color_change = False
            # リセットしても設定したプレゼン時間自体は維持
            save_settings(
                st.session_state.target_time,
                st.session_state.suffix,
                False,
                False,
                st.session_state.timer_mode,
                st.session_state.presentation_duration,
                False,
                "",
                False,
                0
            )
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

else:
    # 通常の時計モード
    st.markdown(f"""
    <div class="target-time">
        {st.session_state.target_time.strftime('%H時%M分')}{st.session_state.suffix}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="current-time">
        {now.strftime('%H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)

    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[now.weekday()]

    st.markdown(f"""
    <div class="date-display">
        {now.strftime('%Y年%m月%d日')}（{weekday}）
    </div>
    """, unsafe_allow_html=True)

    # 残り時間 / 経過時間
    if st.session_state.suffix == "まで" and not st.session_state.time_reached:
        target_for_calc = datetime.datetime.combine(datetime.date.today(), st.session_state.target_time)
        target_for_calc = jst.localize(target_for_calc)
        if target_for_calc <= now:
            target_for_calc = target_for_calc + datetime.timedelta(days=1)
        time_diff = target_for_calc - now
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.markdown(f"""
        <div class="time-info">
            ⏳ 残り {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}
        </div>
        """, unsafe_allow_html=True)

    elif st.session_state.suffix == "から開始" and not st.session_state.time_reached:
        target_for_calc = datetime.datetime.combine(datetime.date.today(), st.session_state.target_time)
        target_for_calc = jst.localize(target_for_calc)
        if target_for_calc <= now:
            target_for_calc = target_for_calc + datetime.timedelta(days=1)
        time_diff = target_for_calc - now
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.markdown(f"""
        <div class="time-info">
            ⏳ 残り {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}
        </div>
        """, unsafe_allow_html=True)

    elif st.session_state.time_reached:
        target_today = datetime.datetime.combine(datetime.date.today(), st.session_state.target_time)
        target_today = jst.localize(target_today)
        time_diff = now - target_today
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.markdown(f"""
        <div class="time-info">
            ⏱️ 経過 {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}
        </div>
        """, unsafe_allow_html=True)

# --- 設定セクション（一番下）---
st.markdown('<div class="settings-section">', unsafe_allow_html=True)

# 編集モード
if st.session_state.editing:
    st.markdown("### ⚙️ 設定変更")

    # モード選択（ラベルを明確化）
    new_timer_mode = st.selectbox(
        "表示モード",
        ["時計", "プレゼンタイマー"],
        index=0 if st.session_state.timer_mode == "clock" else 1
    )

    if new_timer_mode == "時計":
        new_mode = "clock"
        # 時刻入力
        time_input = st.text_input(
            "時刻",
            value=st.session_state.target_time.strftime('%H:%M'),
            placeholder="例: 07:00, 700, 0700, 19:30, 1930",
            help="様々な形式で入力可能です",
            key=f"time_input_field_{st.session_state.editing}"
        )

        # より確実な全選択
        st.markdown(f"""
        <script>
        setTimeout(function() {{
            const inputs = document.querySelectorAll('input[type="text"]');
            inputs.forEach(function(input) {{
                if (input.value.includes(':')) {{
                    input.addEventListener('focus', function() {{
                        setTimeout(() => this.select(), 50);
                    }});
                    input.addEventListener('click', function() {{
                        setTimeout(() => this.select(), 50);
                    }});
                    if (document.activeElement !== input) {{
                        input.focus();
                        setTimeout(() => input.select(), 100);
                    }}
                }}
            }});
        }}, 500);
        </script>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="input-help">
            入力例: 07:00, 700, 0700, 7:00, 7, 19:30, 1930
        </div>
        """, unsafe_allow_html=True)

        # 表示方法（suffix）
        new_suffix = st.selectbox(
            "表示方法",
            ["から開始", "まで"],
            index=0 if st.session_state.suffix == "から開始" else 1
        )

        parsed_time = parse_time_input(time_input)
        if parsed_time:
            preview_dt = jst.localize(datetime.datetime.combine(datetime.date.today(), parsed_time))
            if new_suffix == "から開始" and preview_dt <= now:
                time_status = " (開始時刻を過ぎています - 色が反転します)"
            elif new_suffix == "まで" and preview_dt <= now:
                time_status = " (期限を過ぎています - 色が反転します)"
            else:
                time_status = " (未来の時刻です)"
            st.success(f"✅ 認識された時刻: {parsed_time.strftime('%H:%M')}{time_status}")
        elif time_input.strip():
            st.warning("⚠️ 時刻の形式が正しくありません")

    else:
        new_mode = "presentation"
        # プレゼン時間入力（分:秒 または 分 / 秒）
        duration_input = st.text_input(
            "プレゼン時間",
            value=f"{st.session_state.presentation_duration // 60}:{st.session_state.presentation_duration % 60:02d}",
            placeholder="例: 15:00, 15, 1:30, 90",
            help="分:秒形式または分のみで入力可能です"
        )

        st.markdown(f"""
        <div class="input-help">
            入力例: 15:00 (15分), 15 (15分), 1:30 (1分30秒), 90 (90秒)
        </div>
        """, unsafe_allow_html=True)

        parsed_duration = parse_duration_input(duration_input)
        if parsed_duration:
            minutes = parsed_duration // 60
            seconds = parsed_duration % 60
            st.success(f"✅ 設定時間: {minutes}分{seconds}秒")
        elif duration_input.strip():
            st.warning("⚠️ 時間の形式が正しくありません")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("確定"):
            if new_timer_mode == "時計":
                if parsed_time:
                    input_dt = jst.localize(datetime.datetime.combine(datetime.date.today(), parsed_time))
                    if input_dt <= now:
                        auto_color_change = True
                        auto_force_change = True
                    else:
                        auto_color_change = False
                        auto_force_change = False

                    if save_settings(parsed_time, new_suffix, auto_color_change, auto_force_change,
                                     new_mode, st.session_state.presentation_duration,
                                     st.session_state.timer_started, st.session_state.timer_start_time,
                                     st.session_state.timer_paused, st.session_state.timer_pause_time):
                        st.session_state.target_time = parsed_time
                        st.session_state.suffix = new_suffix
                        st.session_state.timer_mode = new_mode
                        st.session_state.editing = False
                        st.session_state.time_reached = auto_color_change
                        st.session_state.force_color_change = auto_force_change
                        time.sleep(0.2)
                        st.rerun()
                    else:
                        st.error("設定の保存に失敗しました")
                else:
                    st.error("正しい時刻を入力してください")
            else:
                if parsed_duration:
                    if save_settings(st.session_state.target_time, st.session_state.suffix,
                                     st.session_state.time_reached, st.session_state.force_color_change,
                                     new_mode, parsed_duration,
                                     st.session_state.timer_started, st.session_state.timer_start_time,
                                     st.session_state.timer_paused, st.session_state.timer_pause_time):
                        st.session_state.timer_mode = new_mode
                        st.session_state.presentation_duration = parsed_duration
                        st.session_state.editing = False
                        st.success("設定を更新しました！")
                        time.sleep(0.2)
                        st.rerun()
                    else:
                        st.error("設定の保存に失敗しました")
                else:
                    st.error("正しい時間を入力してください")

    with col2:
        if st.button("キャンセル"):
            st.session_state.editing = False
            st.rerun()

else:
    # 設定ボタン
    if st.button("⚙️ 設定を変更", key="edit_button"):
        st.session_state.editing = True
        st.rerun()

# 色切り替えボタン（プレゼンタイマーモードでは非表示）
if st.session_state.timer_mode == "clock":
    st.markdown('<div class="color-toggle-btn">', unsafe_allow_html=True)
    current_color_status = "ピンク" if st.session_state.time_reached else "グレー"
    toggle_color_status = "グレー" if st.session_state.time_reached else "ピンク"

    if st.button(f"🎨 色を{toggle_color_status}に切り替え", key="color_toggle"):
        new_color_state = not st.session_state.time_reached
        new_force_state = new_color_state

        if save_settings(st.session_state.target_time, st.session_state.suffix, new_color_state, new_force_state,
                         st.session_state.timer_mode, st.session_state.presentation_duration,
                         st.session_state.timer_started, st.session_state.timer_start_time,
                         st.session_state.timer_paused, st.session_state.timer_pause_time):
            st.session_state.time_reached = new_color_state
            st.session_state.force_color_change = new_force_state
            st.session_state.last_timestamp = datetime.datetime.now().isoformat()
            st.rerun()
        else:
            st.error("色の変更を保存できませんでした")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- 自動リフレッシュ制御（編集中は止める）---
if not st.session_state.editing:
    time.sleep(1)
    st.rerun()
