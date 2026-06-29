import os, openai

OPENROUTER_CLIENT = openai.OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1"
)

ASI_CLIENT = openai.OpenAI(
    api_key=os.environ["ASI_API_KEY"],
    base_url="https://inference.asicloud.cudos.org/v1"
)

ANTHROPIC_CLIENT = openai.OpenAI(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url="https://api.anthropic.com/v1/"
)

def _clean(text):
    return text.replace("_quote_", '"').replace("_apostrophe_", "'")

def _chat(client, model, content, max_tokens=6000, max_retries=5, retry_delay=1):
    content = content.replace("<tool_call>","").replace("<arg_value>"," ").replace("</tool_call>","").replace("</arg_value>","")
    sysmsg, usermsg = content.split(":-:-:-:", 1)

    if not usermsg.strip():
        usermsg = "EMPTY / NO NEW USER INPUT."

    for attempt in range(max_retries):
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sysmsg},
                      {"role": "user", "content": usermsg}],
            max_tokens=max_tokens,
            extra_body={
                "enable_thinking": True,
                "thinking_budget": 6000
            }
        )

        text = resp.choices[0].message.content

        if text is not None:
            return _clean(text)

        time.sleep(retry_delay)

    raise RuntimeError("LLM returned None after all retry attempts")

def useOpenRouter(content):
    return _chat(
        client=OPENROUTER_CLIENT,
        model="z-ai/glm-5.1",  # replace with your OpenRouter model id
        content=content
    )

def useMiniMax(content):
    return _chat(
        client=ASI_CLIENT,
        model="minimax/minimax-m2.7", #"minimax/minimax-m2.7", #"asi1-mini",
        content=content
    )

def useClaude(content):
    return _chat(
        client=ANTHROPIC_CLIENT,
        model="claude-opus-4-6",
        content=content
    )

_embedding_model = None

def initLocalEmbedding():
    model_name="intfloat/e5-large-v2"
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model

def useLocalEmbedding(atom):
    global _embedding_model
    if _embedding_model is None:
        raise RuntimeError("Call initLocalEmbedding() first.")
    return _embedding_model.encode(
        atom,
        normalize_embeddings=True
    ).tolist()

import os
import time
import cv2
import base64
import atexit
import threading
import subprocess
import numpy as np
import yt_dlp
from datetime import datetime


EPISODES_DIR = "./repos/mettaclaw/memory/episodes"

_SAMPLERS = {}
_SAMPLERS_LOCK = threading.Lock()


def episode_image_path(ext="jpg"):
    os.makedirs(EPISODES_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(EPISODES_DIR, f"{ts}.{ext}")


def _image_file_to_data_url(img_path):
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(img_path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    return f"data:{mime};base64," + b64


def get_youtube_media_url(youtube_url):
    opts = {
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": False,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return info["url"]
    except Exception as e:
        raise RuntimeError(
            f"Could not resolve YouTube video URL. "
            f"The video may be unavailable, private, region-blocked, login-gated, "
            f"or blocked from this machine. Original error: {e}"
        )


class LiveYoutubeMotionSampler:
    def __init__(
        self,
        youtube_url,
        sample_every=0.25,
        flow_size=(320, 180),
        motion_threshold=2.4,
        motion_half_life=0.5,
        coherence_threshold=0.58,
    ):
        self.youtube_url = youtube_url
        self.sample_every = sample_every
        self.flow_size = flow_size
        self.motion_threshold = motion_threshold
        self.motion_half_life = motion_half_life
        self.coherence_threshold = coherence_threshold

        self.lock = threading.Lock()
        self.thread = None
        self.stop_event = threading.Event()

        self.latest_frame = None
        self.prev_gray = None

        self.heat_accum = None
        self.flow_x_accum = None
        self.flow_y_accum = None
        self.flow_count = None

        self.sample_count = 0
        self.last_motion_update = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def wait_until_ready(self, timeout=8.0):
        t0 = time.time()

        while time.time() - t0 < timeout:
            with self.lock:
                ready = self.latest_frame is not None

            if ready:
                return True

            time.sleep(0.1)

        return False

    def _reset_accumulators_locked(self):
        hh, ww = self.flow_size[1], self.flow_size[0]

        self.heat_accum = np.zeros((hh, ww), dtype=np.float32)
        self.flow_x_accum = np.zeros((hh, ww), dtype=np.float32)
        self.flow_y_accum = np.zeros((hh, ww), dtype=np.float32)
        self.flow_count = np.zeros((hh, ww), dtype=np.float32)

        self.sample_count = 0
        self.last_motion_update = None

    def _run(self):
        cap = None
        last_sample_time = 0.0

        while not self.stop_event.is_set():
            try:
                if cap is None or not cap.isOpened():
                    media_url = get_youtube_media_url(self.youtube_url)
                    cap = cv2.VideoCapture(media_url)

                    self.prev_gray = None

                    with self.lock:
                        self.latest_frame = None
                        self._reset_accumulators_locked()

                ret, frame = cap.read()

                if not ret or frame is None:
                    if cap is not None:
                        cap.release()

                    cap = None
                    time.sleep(2.0)
                    continue

                now = time.time()

                if now - last_sample_time < self.sample_every:
                    continue

                last_sample_time = now

                small = cv2.resize(frame, self.flow_size, interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                with self.lock:
                    self.latest_frame = frame.copy()

                    if self.heat_accum is None:
                        self._reset_accumulators_locked()

                if self.prev_gray is not None:
                    flow = cv2.calcOpticalFlowFarneback(
                        self.prev_gray,
                        gray,
                        None,
                        pyr_scale=0.5,
                        levels=3,
                        winsize=15,
                        iterations=3,
                        poly_n=5,
                        poly_sigma=1.2,
                        flags=0,
                    )

                    fx = flow[:, :, 0]
                    fy = flow[:, :, 1]

                    mag = np.sqrt(fx * fx + fy * fy)
                    mag = cv2.GaussianBlur(mag, (5, 5), 0)

                    mean_fx = cv2.blur(fx, (15, 15))
                    mean_fy = cv2.blur(fy, (15, 15))
                    mean_mag = np.sqrt(mean_fx * mean_fx + mean_fy * mean_fy)

                    local_mag = cv2.blur(mag, (15, 15)) + 1e-6
                    coherence = mean_mag / local_mag
                    coherence = np.clip(coherence, 0.0, 1.0)

                    stable = (
                        (mag > self.motion_threshold)
                        & (coherence > self.coherence_threshold)
                    )

                    stable_mag = mag * coherence * stable

                    now2 = time.time()

                    with self.lock:
                        if self.last_motion_update is None:
                            dt = self.sample_every
                        else:
                            dt = now2 - self.last_motion_update

                        self.last_motion_update = now2

                        decay = 0.5 ** (dt / self.motion_half_life)

                        self.heat_accum *= decay
                        self.flow_x_accum *= decay
                        self.flow_y_accum *= decay
                        self.flow_count *= decay

                        # Important: decayed max, not additive accumulation.
                        # This prevents canal/water flicker from becoming huge blobs.
                        self.heat_accum = np.maximum(self.heat_accum, stable_mag)

                        # Use latest stable direction only.
                        self.flow_x_accum[stable] = fx[stable]
                        self.flow_y_accum[stable] = fy[stable]
                        self.flow_count[stable] = 1.0

                        self.sample_count += 1

                self.prev_gray = gray

            except Exception as e:
                print("[motion sampler error]", e)

                if cap is not None:
                    cap.release()

                cap = None
                time.sleep(2.0)

        if cap is not None:
            cap.release()

    def snapshot_overlay_image(self, reset=True):
        with self.lock:
            if self.latest_frame is None:
                raise RuntimeError("No frame available yet from sampler.")

            frame = self.latest_frame.copy()

            if self.heat_accum is None:
                self._reset_accumulators_locked()

            heat_accum = self.heat_accum.copy()
            flow_x_accum = self.flow_x_accum.copy()
            flow_y_accum = self.flow_y_accum.copy()
            flow_count = self.flow_count.copy()

            if reset:
                self._reset_accumulators_locked()

        h, w = frame.shape[:2]

        heat = heat_accum.copy()

        if np.max(heat) > 0:
            clip_val = np.percentile(heat, 99)

            if clip_val > 0:
                heat = np.clip(heat, 0, clip_val)

            heat = (255.0 * heat / (np.max(heat) + 1e-6)).astype(np.uint8)
        else:
            heat = np.zeros_like(heat, dtype=np.uint8)

        # Strict cutoff. This is the main anti-water-noise filter.
        visible_heat = heat.copy()
        visible_heat[visible_heat < 65] = 0

        binary = (visible_heat > 0).astype(np.uint8)

        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        #visible_heat = visible_heat * binary
        visible_heat = visible_heat * binary

        dir_mag = np.sqrt(flow_x_accum * flow_x_accum + flow_y_accum * flow_y_accum)
        visible_heat[dir_mag < 0.25] = 0
        binary = (visible_heat > 0).astype(np.uint8)

        # Render heat.
        heat_big = cv2.resize(visible_heat, (w, h), interpolation=cv2.INTER_LINEAR)
        mask_big = heat_big > 0
        heat_color = cv2.applyColorMap(heat_big, cv2.COLORMAP_JET)

        overlay = frame.copy()
        blended = cv2.addWeighted(frame, 0.72, heat_color, 0.45, 0.0)
        overlay[mask_big] = blended[mask_big]

        # Arrows per visible connected component.
        scale_x = w / float(self.flow_size[0])
        scale_y = h / float(self.flow_size[1])

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            binary,
            connectivity=8,
        )

        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]

            # Remove tiny junk.
            if area < 20:
                continue

            comp = labels == label
            valid = comp & (flow_count > 0) & (visible_heat > 65)

            if np.count_nonzero(valid) < 6:
                continue

            weights = visible_heat[valid].astype(np.float32)
            weight_sum = weights.sum()

            if weight_sum <= 0:
                continue

            avg_fx = float((flow_x_accum[valid] * weights).sum() / (weight_sum + 1e-6))
            avg_fy = float((flow_y_accum[valid] * weights).sum() / (weight_sum + 1e-6))
            avg_mag = float((avg_fx * avg_fx + avg_fy * avg_fy) ** 0.5)

            # Direction must be strong enough to show arrow.
            if avg_mag < 0.25:
                continue

            ys, xs = np.where(valid)

            cx_small = float((xs * weights).sum() / (weight_sum + 1e-6))
            cy_small = float((ys * weights).sum() / (weight_sum + 1e-6))

            # Short arrows. Less visual nonsense.
            max_len_small = max(4.0, 0.25 * np.sqrt(float(area)))
            desired_len_small = min(max_len_small, 3.0 + avg_mag * 6.0)

            norm = avg_mag + 1e-6
            dx_small = (avg_fx / norm) * desired_len_small
            dy_small = (avg_fy / norm) * desired_len_small

            cx = int(cx_small * scale_x)
            cy = int(cy_small * scale_y)
            ex = int((cx_small + dx_small) * scale_x)
            ey = int((cy_small + dy_small) * scale_y)

            cv2.arrowedLine(
                overlay,
                (cx, cy),
                (ex, ey),
                (255, 255, 255),
                2,
                tipLength=0.35,
            )

        cv2.putText(
            overlay,
            "recent stable motion",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        out_path = episode_image_path("jpg")
        cv2.imwrite(out_path, overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        return out_path


def get_motion_sampler(youtube_url, sample_every=0.25):
    with _SAMPLERS_LOCK:
        sampler = _SAMPLERS.get(youtube_url)

        if sampler is None:
            sampler = LiveYoutubeMotionSampler(
                youtube_url=youtube_url,
                sample_every=sample_every,
                flow_size=(320, 180),
                motion_threshold=2.4,
                motion_half_life=0.5,
                coherence_threshold=0.58,
            )
            sampler.start()
            _SAMPLERS[youtube_url] = sampler

        return sampler


def stop_all_motion_samplers():
    with _SAMPLERS_LOCK:
        samplers = list(_SAMPLERS.values())
        _SAMPLERS.clear()

    for s in samplers:
        try:
            s.stop()
        except Exception:
            pass


atexit.register(stop_all_motion_samplers)


def youtube_frame_to_data_url(youtube_url, seconds=0):
    img_path = episode_image_path("jpg")
    media_url = get_youtube_media_url(youtube_url)

    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(seconds),
            "-i",
            media_url,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            img_path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return _image_file_to_data_url(img_path)


def youtube_motion_overlay_to_data_url(youtube_url, warmup_timeout=8.0):
    sampler = get_motion_sampler(youtube_url, sample_every=0.25)

    ready = sampler.wait_until_ready(timeout=warmup_timeout)

    if not ready:
        return youtube_frame_to_data_url(youtube_url, seconds=0)

    img_path = sampler.snapshot_overlay_image(reset=True)
    return _image_file_to_data_url(img_path)


def useClaudeYoutubeImage(
    content,
    youtube_url,
    seconds=0,
    max_tokens=6000,
    use_motion=True,
):
    if use_motion and seconds == 0:
        image_data_url = youtube_motion_overlay_to_data_url(youtube_url)
    else:
        image_data_url = youtube_frame_to_data_url(youtube_url, seconds=seconds)

    resp = ANTHROPIC_CLIENT.chat.completions.create(
        model="claude-opus-4-6",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": content,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url,
                        },
                    },
                ],
            }
        ],
        max_tokens=max_tokens,
    )

    return _clean(resp.choices[0].message.content)


if __name__ == "__main__":
    youtube_url = "https://www.youtube.com/watch?v=CMn6xQXuSjI"

    while True:
        try:
            time.sleep(10)

            answer = useClaudeYoutubeImage(
                "Do you see a boat? Use the overlay: colored regions show recent stable motion; arrows show direction when reliable.",
                youtube_url
            )

            print(answer)

        except KeyboardInterrupt:
            print("stopping...")
            break

        except Exception as e:
            print("error:", e)
            time.sleep(2)
